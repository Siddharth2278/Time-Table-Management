import { useState } from "react";
import { Pencil, Trash2, Plus, ArrowLeft } from "lucide-react";
import { useStore } from "../store/useStore";
import { PageHeader, Card, CardContent, Button, Input, Label, Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge } from "../components/ui";

export default function Teachers() {
  const teachers = useStore((s) => s.teachers);
  const addTeacher = useStore((s) => s.addTeacher);
  const updateTeacher = useStore((s) => s.updateTeacher);
  const deleteTeacher = useStore((s) => s.deleteTeacher);
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState({ name: "", email: "", department: "", designation: "", status: "Active" });

  const openNew = () => { setForm({ name: "", email: "", department: "", designation: "", status: "Active" }); setEditing("new"); };
  const openEdit = (id: number) => {
    const t = teachers.find((x) => x.id === id);
    if (!t) return;
    setForm({ name: t.name, email: t.email, department: t.department, designation: t.designation, status: t.status });
    setEditing(id);
  };
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (editing === "new") addTeacher(form);
    else if (typeof editing === "number") updateTeacher(editing, form);
    setEditing(null);
  };

  const rows = teachers.filter((t) => (t.name + t.email + t.department).toLowerCase().includes(q.toLowerCase()));

  if (editing !== null) {
    return (
      <div className="animate-[fadeIn_0.5s_ease]">
        <PageHeader
          title={editing === "new" ? "Add Teacher" : "Edit Teacher"}
          action={<Button variant="outline" onClick={() => setEditing(null)}><ArrowLeft size={16} /> Back to table</Button>}
        />
        <Card><CardContent>
          <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div><Label>Email</Label><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div><Label>Department</Label><Input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></div>
            <div><Label>Designation</Label><Input value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} /></div>
            <div><Label>Status</Label><Input value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} /></div>
            <div className="flex items-end gap-2"><Button type="submit">Save Teacher</Button></div>
          </form>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Teachers" description="Manage faculty and availability." action={<Button onClick={openNew}><Plus size={16} /> Add Teacher</Button>} />
      <Card><CardContent>
        <div className="mb-3"><Input placeholder="Search teachers..." value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Dept</TableHead><TableHead>Status</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {rows.map((t) => (
              <TableRow key={t.id}>
                <TableCell>{t.name}</TableCell>
                <TableCell mono>{t.email}</TableCell>
                <TableCell>{t.department}</TableCell>
                <TableCell><Badge variant={t.status === "Active" ? "success" : "default"}>{t.status}</Badge></TableCell>
                <TableCell>
                  <span className="flex gap-2">
                    <button onClick={() => openEdit(t.id)} aria-label="Edit" className="rounded p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Pencil size={16} /></button>
                    <button onClick={() => deleteTeacher(t.id)} aria-label="Delete" className="rounded p-1.5 text-[#9A2C2C] hover:bg-red-50"><Trash2 size={16} /></button>
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>
    </div>
  );
}
