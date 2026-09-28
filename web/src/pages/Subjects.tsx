import { useState } from "react";
import { Pencil, Trash2, Plus, ArrowLeft } from "lucide-react";
import { useStore } from "../store/useStore";
import { PageHeader, Card, CardContent, Button, Input, Label, Select, Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge } from "../components/ui";

export default function Subjects() {
  const subjects = useStore((s) => s.subjects);
  const semesters = useStore((s) => s.semesters);
  const teachers = useStore((s) => s.teachers);
  const rooms = useStore((s) => s.rooms);
  const addSubject = useStore((s) => s.addSubject);
  const updateSubject = useStore((s) => s.updateSubject);
  const deleteSubject = useStore((s) => s.deleteSubject);
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState({ code: "", name: "", semester_id: 1, subject_type: "Theory", required_lectures_per_week: 3, lecture_duration: 60, teacher_id: null as number | null, room_id: null as number | null, room_requirement: "Classroom" });

  const openNew = () => { setForm({ code: "", name: "", semester_id: semesters[0]?.id ?? 1, subject_type: "Theory", required_lectures_per_week: 3, lecture_duration: 60, teacher_id: null, room_id: null, room_requirement: "Classroom" }); setEditing("new"); };
  const openEdit = (id: number) => {
    const x = subjects.find((v) => v.id === id);
    if (!x) return;
    setForm({ code: x.code, name: x.name, semester_id: x.semester_id, subject_type: x.subject_type, required_lectures_per_week: x.required_lectures_per_week, lecture_duration: x.lecture_duration, teacher_id: x.teacher_id, room_id: x.room_id, room_requirement: x.room_requirement });
    setEditing(id);
  };
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.code.trim() || !form.name.trim()) return;
    if (editing === "new") addSubject(form);
    else if (typeof editing === "number") updateSubject(editing, form);
    setEditing(null);
  };
  const rows = subjects.filter((x) => (x.code + x.name).toLowerCase().includes(q.toLowerCase()));

  if (editing !== null) {
    return (
      <div className="animate-[fadeIn_0.5s_ease]">
        <PageHeader title={editing === "new" ? "Add Subject" : "Edit Subject"} action={<Button variant="outline" onClick={() => setEditing(null)}><ArrowLeft size={16} /> Back</Button>} />
        <Card><CardContent>
          <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><Label>Code</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></div>
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div><Label>Semester</Label><Select value={form.semester_id} onChange={(e) => setForm({ ...form, semester_id: Number(e.target.value) })}>{semesters.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></div>
            <div><Label>Preferred Teacher</Label><Select value={form.teacher_id ?? ""} onChange={(e) => setForm({ ...form, teacher_id: e.target.value ? Number(e.target.value) : null })}><option value="">— None —</option>{teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</Select></div>
            <div><Label>Preferred Room</Label><Select value={form.room_id ?? ""} onChange={(e) => setForm({ ...form, room_id: e.target.value ? Number(e.target.value) : null })}><option value="">— None —</option>{rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</Select></div>
            <div><Label>Type</Label><Select value={form.subject_type} onChange={(e) => setForm({ ...form, subject_type: e.target.value })}><option>Theory</option><option>Lab</option><option>Practical</option><option>Tutorial</option></Select></div>
            <div className="flex items-end"><Button type="submit">Save Subject</Button></div>
          </form>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Subjects" description="Courses linked to semesters, teachers and rooms." action={<Button onClick={openNew}><Plus size={16} /> Add Subject</Button>} />
      <Card><CardContent>
        <div className="mb-3"><Input placeholder="Search subjects..." value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Table>
          <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Name</TableHead><TableHead>Type</TableHead><TableHead>Req/Wk</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.map((x) => (
              <TableRow key={x.id}>
                <TableCell mono>{x.code}</TableCell>
                <TableCell>{x.name}</TableCell>
                <TableCell><Badge>{x.subject_type}</Badge></TableCell>
                <TableCell mono>{x.required_lectures_per_week}</TableCell>
                <TableCell><span className="flex gap-2">
                  <button onClick={() => openEdit(x.id)} aria-label="Edit" className="rounded p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Pencil size={16} /></button>
                  <button onClick={() => deleteSubject(x.id)} aria-label="Delete" className="rounded p-1.5 text-[#9A2C2C] hover:bg-red-50"><Trash2 size={16} /></button>
                </span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>
    </div>
  );
}
