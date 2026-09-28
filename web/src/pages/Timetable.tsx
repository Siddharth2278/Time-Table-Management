import { useMemo, useState } from "react";
import { useStore, DAYS } from "../store/useStore";
import { PageHeader, Card, Select } from "../components/ui";
import { cn } from "../utils/cn";

function overlaps(aS: string, aE: string, bS: string, bE: string) {
  return aS < bE && aE > bS;
}

export default function Timetable() {
  const semesters = useStore((s) => s.semesters);
  const slots = useStore((s) => s.slots);
  const entries = useStore((s) => s.entries);
  const subjects = useStore((s) => s.subjects);
  const teachers = useStore((s) => s.teachers);
  const rooms = useStore((s) => s.rooms);
  const [semId, setSemId] = useState(semesters[0]?.id ?? 1);

  const activeSlots = useMemo(() => slots.filter((t) => t.is_enabled), [slots]);
  const semEntries = useMemo(() => entries.filter((e) => e.semester_id === Number(semId)), [entries, semId]);

  const cellFor = (dayId: number, s: string, e: string) =>
    semEntries.find((x) => x.day_id === dayId && x.start_time === s && x.end_time === e);

  const conflictFor = (dayId: number, s: string, e: string) => {
    const hit = semEntries.filter((x) => x.day_id === dayId && overlaps(x.start_time, x.end_time, s, e));
    const teachersSeen = new Set<number>();
    const roomsSeen = new Set<number>();
    for (const h of hit) {
      if (teachersSeen.has(h.teacher_id) || roomsSeen.has(h.room_id)) return true;
      teachersSeen.add(h.teacher_id);
      roomsSeen.add(h.room_id);
    }
    return hit.length > 1;
  };

  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader
        title="Timetable Matrix"
        description="Days across, time slots down. Breaks are hashed, conflicts outlined in burgundy."
        action={
          <label className="flex items-center gap-2 text-sm">
            Semester
            <Select value={semId} onChange={(e) => setSemId(Number(e.target.value))} className="w-44">
              {semesters.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </label>
        }
      />
      <Card>
        <div className="custom-scrollbar overflow-auto">
          <div className="min-w-[860px]">
            <div className="grid" style={{ gridTemplateColumns: `90px repeat(${DAYS.length}, minmax(120px, 1fr))` }}>
              <div className="sticky left-0 z-10 border-b border-[#DEDCD3] bg-[#F3F1EA] p-2 font-mono text-xs dark:bg-neutral-900">DAY ↓ TIME →</div>
              {DAYS.map((d) => (
                <div key={d.id} className="border-b border-l border-[#DEDCD3] bg-[#F3F1EA] p-2 text-center font-mono text-xs font-semibold dark:bg-neutral-900">
                  {d.name.toUpperCase()}
                </div>
              ))}
              {activeSlots.map((t) => (
                <div key={t.id} className="contents">
                  <div className="border-b border-[#DEDCD3] p-2 font-mono text-xs dark:border-neutral-800">
                    {t.start_time}<br />{t.end_time}
                  </div>
                  {DAYS.map((d) => {
                    if (t.is_break) {
                      return (
                        <div
                          key={d.id}
                          className="border-b border-l border-[#DEDCD3] p-2 text-center dark:border-neutral-800"
                          style={{ backgroundImage: "repeating-linear-gradient(45deg, rgba(0,0,0,.06) 0 6px, transparent 6px 12px)" }}
                        >
                          <span className="font-mono text-[11px] uppercase tracking-widest text-neutral-500">
                            {t.break_name || "Break"}
                          </span>
                        </div>
                      );
                    }
                    const hit = cellFor(d.id, t.start_time, t.end_time);
                    const conflict = conflictFor(d.id, t.start_time, t.end_time);
                    if (hit) {
                      const sub = subjects.find((x) => x.id === hit.subject_id);
                      const tea = teachers.find((x) => x.id === hit.teacher_id);
                      const roo = rooms.find((x) => x.id === hit.room_id);
                      return (
                        <div key={d.id} className="border-b border-l border-[#DEDCD3] p-1.5 dark:border-neutral-800">
                          <div
                            className={cn(
                              "rounded-sm border-l-4 bg-[#1C355E]/5 p-2",
                              conflict ? "border-[#9A2C2C]" : "border-[#1C355E]"
                            )}
                          >
                            <div className="font-mono text-xs font-semibold">{sub?.code ?? `Sub ${hit.subject_id}`}</div>
                            <div className="truncate text-xs text-neutral-600 dark:text-neutral-300">{tea?.name ?? ""}</div>
                            <div className="font-mono text-[11px] text-neutral-500">{roo?.room_number ?? ""}</div>
                          </div>
                        </div>
                      );
                    }
                    return (
                      <div key={d.id} className="group border-b border-l border-[#DEDCD3] p-1.5 dark:border-neutral-800">
                        <button className="w-full rounded-sm py-4 text-xs text-transparent hover:bg-[#1C355E]/5 hover:text-[#1C355E]">
                          Assign
                        </button>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
