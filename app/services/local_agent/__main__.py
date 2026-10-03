"""Run the local timetable agent from a terminal.

Examples:
    python -m app.services.local_agent learn previous_timetable.csv
    python -m app.services.local_agent learn sem1.csv sem3.csv
    python -m app.services.local_agent show
    python -m app.services.local_agent generate requirements.json
    python -m app.services.local_agent generate requirements.json --apply
    python -m app.services.local_agent check-model
    python -m app.services.local_agent clear
"""
import argparse
import json
import sys

from app.services.local_agent.schemas import LearningError


def _agent(args):
    from app.services.local_agent.agent import TimetableAgent
    from app.services.local_agent.model_client import OllamaClient
    client = OllamaClient(endpoint=args.ollama_url, model=args.model)
    return TimetableAgent(ollama=client)


def _cmd_learn(agent, args):
    summary = agent.learn_files(args.files)
    print(f"Learned {summary['lectures']} lectures, "
          f"{summary['subjects']} subjects, {summary['roles']} roles "
          f"from {len(summary['files'])} file(s) "
          f"({summary['skipped_rows']} row(s) skipped).")
    status = agent._ollama_status()
    print(f"Ollama: {'running' if status.get('running') else 'not running'} "
          f"at {status.get('endpoint', '')} (optional for learning).")
    return 0


def _cmd_show(agent, args):
    try:
        profile = agent.get_learning_profile()
    except LearningError as e:
        print(f"Error: {e}")
        return 1
    patterns = profile.get("patterns", {})
    print(f"Sources: {', '.join(profile.get('sources', [])) or '-'}")
    print(f"Lectures: {profile.get('total_lectures', 0)}, "
          f"subjects: {len(profile.get('subjects', []))}, "
          f"roles: {len(profile.get('roles', {}))}")
    print(f"Preferred days: {', '.join(patterns.get('preferred_days', []))}")
    print(f"Preferred times: {', '.join(patterns.get('preferred_times', []))}")
    print(f"Morning share: {patterns.get('morning_share')}")
    print(f"Daily load avg: {patterns.get('average_daily_load')}")
    if args.json:
        print(json.dumps(profile, indent=1))
    return 0


def _cmd_check_model(agent, args):
    try:
        status = agent.check_model(args.model)
    except LearningError as e:
        print(f"Error: {e}")
        return 1
    print(f"Ollama running at {status['endpoint']}, "
          f"model '{status['model']}' available.")
    return 0


def _cmd_generate(agent, args):
    import json as _json
    try:
        with open(args.requirements, "r", encoding="utf-8") as fh:
            req = _json.load(fh)
    except (OSError, ValueError) as e:
        print(f"Error: cannot read requirements file: {e}")
        return 1
    try:
        semester_id = int(req.get("semester_id", 0))
    except (TypeError, ValueError):
        print("Error: requirements JSON needs an integer 'semester_id'.")
        return 1
    mode = str(req.get("mode", "fill"))
    if mode not in ("fill", "fresh", "replace"):
        print("Error: 'mode' must be fill, fresh or replace.")
        return 1
    try:
        result = agent.generate(semester_id, mode, args.model,
                                use_model_plan=not args.template_only)
    except LearningError as e:
        print(f"Error: {e}")
        return 1
    summary = result.as_dict()
    print(f"Proposed: {summary['statistics'].get('proposed', 0)} model cells, "
          f"accepted {summary['accepted']}, unplaced {summary['unplaced']}, "
          f"hard conflicts {summary['hard_conflicts']}, "
          f"similarity {summary['structural_similarity']}.")
    print(f"Planner: {summary['profile'].get('planner', '')}")
    for item in result.unplaced[:10]:
        print(f"  unplaced: {item.get('code', '')} — {item.get('reason', '')}")
    if args.apply:
        if not result.accepted:
            print("Nothing to apply.")
            return 1
        try:
            applied = agent.apply_generation(semester_id, result, mode)
        except LearningError as e:
            print(f"Error: {e}")
            return 1
        print(f"Applied {applied.get('applied', 0)} lecture(s) atomically.")
    else:
        print("Dry run only: database unchanged. Re-run with --apply to commit.")
    return 0


def _cmd_clear(agent, args):
    removed = agent.clear_learning_profile()
    print("Profile cleared." if removed else "No profile stored.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m app.services.local_agent",
        description="Phase 1 local timetable learning agent (offline).")
    parser.add_argument("--ollama-url", default=None,
                        help="Ollama endpoint (default http://127.0.0.1:11434)")
    parser.add_argument("--model", default=None,
                        help="Ollama model name for availability checks")
    sub = parser.add_subparsers(dest="command", required=True)
    learn_parser = sub.add_parser("learn", help="Learn timetable file(s)")
    learn_parser.add_argument("files", nargs="+", help="CSV, XLSX or JSON timetables")
    show_parser = sub.add_parser("show", help="Show the stored profile")
    show_parser.add_argument("--json", action="store_true",
                             help="Print the full profile JSON")
    check_parser = sub.add_parser("check-model", help="Check localhost Ollama")
    check_parser.add_argument("--model", default=None)
    gen_parser = sub.add_parser("generate", help="Dry-run local-agent generation")
    gen_parser.add_argument("requirements",
                            help='JSON file, e.g. {"semester_id": 1, "mode": "fill"}')
    gen_parser.add_argument("--apply", action="store_true",
                            help="Apply the proposal atomically after preview")
    gen_parser.add_argument("--template-only", action="store_true",
                            help="Skip the local model and use template patterns only")
    sub.add_parser("clear", help="Delete the stored profile")
    args = parser.parse_args(argv)
    agent = _agent(args)
    try:
        if args.command == "learn":
            return _cmd_learn(agent, args)
        if args.command == "show":
            return _cmd_show(agent, args)
        if args.command == "generate":
            return _cmd_generate(agent, args)
        if args.command == "check-model":
            return _cmd_check_model(agent, args)
        if args.command == "clear":
            return _cmd_clear(agent, args)
    except LearningError as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
