"""Run the local timetable agent from a terminal.

Examples:
    python -m app.services.local_agent learn previous_timetable.csv
    python -m app.services.local_agent show
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
    summary = agent.analyze_reference_timetable(args.file)
    print(f"Learned {summary['lectures']} lectures, "
          f"{summary['subjects']} subjects, {summary['roles']} roles "
          f"({summary['skipped_rows']} row(s) skipped).")
    print(f"Saved to {summary['saved_to']}")
    status = summary.get("ollama_status", {})
    print(f"Ollama: {'running' if status.get('running') else 'not running'} "
          f"at {status.get('endpoint', '')} (optional in Phase 1).")
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
    learn_parser = sub.add_parser("learn", help="Learn a timetable file")
    learn_parser.add_argument("file", help="CSV, XLSX or JSON timetable")
    show_parser = sub.add_parser("show", help="Show the stored profile")
    show_parser.add_argument("--json", action="store_true",
                             help="Print the full profile JSON")
    check_parser = sub.add_parser("check-model", help="Check localhost Ollama")
    check_parser.add_argument("--model", default=None)
    sub.add_parser("clear", help="Delete the stored profile")
    args = parser.parse_args(argv)
    agent = _agent(args)
    try:
        if args.command == "learn":
            return _cmd_learn(agent, args)
        if args.command == "show":
            return _cmd_show(agent, args)
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
