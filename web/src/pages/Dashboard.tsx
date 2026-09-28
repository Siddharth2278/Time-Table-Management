import { Link } from "react-router-dom";
import { Users, BookOpen, DoorOpen, Layers, ArrowRight } from "lucide-react";
import { useStore } from "../store/useStore";
import { PageHeader, Card, CardContent } from "../components/ui";

export default function Dashboard() {
  const teachers = useStore((s) => s.teachers);
  const subjects = useStore((s) => s.subjects);
  const rooms = useStore((s) => s.rooms);
  const semesters = useStore((s) => s.semesters);
  const entries = useStore((s) => s.entries);

  const metrics = [
    { label: "Total Teachers", value: teachers.length, icon: Users, bg: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300" },
    { label: "Total Subjects", value: subjects.length, icon: BookOpen, bg: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" },
    { label: "Rooms", value: rooms.length, icon: DoorOpen, bg: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" },
    { label: "Active Semesters", value: semesters.length, icon: Layers, bg: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300" },
  ];

  const recent = [...entries].slice(-6).reverse();

  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Dashboard" description="Timetable health, recent scheduling activity and shortcuts." />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((m) => {
          const Icon = m.icon;
          return (
            <Card key={m.label}>
              <CardContent className="flex items-center gap-4 py-5">
                <span className={`rounded-sm p-3 ${m.bg}`}>
                  <Icon size={22} />
                </span>
                <span>
                  <span className="block font-mono text-2xl font-semibold">{m.value}</span>
                  <span className="text-sm text-neutral-500">{m.label}</span>
                </span>
              </CardContent>
            </Card>
          );
        })}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent>
            <h2 className="mb-3 font-serif text-xl font-semibold">Recent Activity</h2>
            {recent.length === 0 ? (
              <p className="rounded-sm border border-dashed border-[#DEDCD3] p-6 text-center text-sm text-neutral-500">
                No lectures scheduled yet. Open Timetable and assign your first class.
              </p>
            ) : (
              <ul className="divide-y divide-[#DEDCD3] dark:divide-neutral-800">
                {recent.map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                    <span>
                      <span className="font-mono font-medium">Sem {e.semester_id} • Day {e.day_id}</span>{" "}
                      <span className="font-mono text-neutral-500">{e.start_time}-{e.end_time}</span>
                    </span>
                    <span className="truncate text-neutral-500">Sub {e.subject_id} • T{e.teacher_id} • R{e.room_id}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <h2 className="mb-3 font-serif text-xl font-semibold">Quick Links</h2>
            <div className="flex flex-col gap-2">
              {[
                { to: "/timetable", label: "Open Timetable" },
                { to: "/teachers", label: "Add Teacher" },
                { to: "/subjects", label: "Add Subject" },
                { to: "/settings", label: "Settings" },
              ].map((l) => (
                <Link
                  key={l.to + l.label}
                  to={l.to}
                  className="flex items-center justify-between rounded-sm border border-[#DEDCD3] px-3 py-2.5 text-sm font-medium hover:bg-[#FAF9F6] dark:border-neutral-700 dark:hover:bg-neutral-800"
                >
                  {l.label} <ArrowRight size={16} />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
