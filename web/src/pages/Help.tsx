import { PageHeader, Card, CardContent } from "../components/ui";

const STEPS = [
  { title: "1. Setup", body: "Set college name, department and academic year in Settings. Defaults are prefilled so the app works offline on first load." },
  { title: "2. Manage Resources", body: "Add Teachers, Subjects, Rooms, Semesters and Time Slots. Subjects link to a semester plus preferred teacher and room." },
  { title: "3. Generate", body: "Open Timetable, pick a semester, and assign Subject–Teacher–Room blocks into Day × Time cells. Breaks render hashed; double-bookings outline in burgundy." },
  { title: "4. Export", body: "Use Export PDF in the Timetable header to print or publish. State lives in memory via Zustand — no backend required." },
];

export default function Help() {
  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Help & Guide" description="Four steps from blank to published timetable." />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {STEPS.map((s) => (
          <Card key={s.title}><CardContent>
            <h2 className="mb-2 font-serif text-xl font-semibold">{s.title}</h2>
            <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">{s.body}</p>
          </CardContent></Card>
        ))}
      </div>
    </div>
  );
}
