import { useState } from "react";
import { Pencil, Trash2, Plus, ArrowLeft } from "lucide-react";
import { useStore } from "../store/useStore";
import { PageHeader, Card, CardContent, Button, Input, Label, Select, Table, TableHeader, TableBody, TableRow, TableHead, TableCell, Badge } from "../components/ui";

export function Rooms() {
  const rooms = useStore((s) => s.rooms);
  const addRoom = useStore((s) => s.addRoom);
  const updateRoom = useStore((s) => s.updateRoom);
  const deleteRoom = useStore((s) => s.deleteRoom);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState({ name: "", room_number: "", type: "Classroom", capacity: 60, status: "Available" });

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (editing === "new") addRoom(form);
    else if (typeof editing === "number") updateRoom(editing, form);
    setEditing(null);
  };

  if (editing !== null) {
    return (
      <div className="animate-[fadeIn_0.5s_ease]">
        <PageHeader title={editing === "new" ? "Add Room" : "Edit Room"} action={<Button variant="outline" onClick={() => setEditing(null)}><ArrowLeft size={16} /> Back</Button>} />
        <Card><CardContent>
          <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div><Label>Room Number</Label><Input value={form.room_number} onChange={(e) => setForm({ ...form, room_number: e.target.value })} required /></div>
            <div><Label>Type</Label><Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}><option>Classroom</option><option>Lab</option></Select></div>
            <div><Label>Capacity</Label><Input type="number" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} /></div>
            <div className="flex items-end"><Button type="submit">Save Room</Button></div>
          </form>
        </CardContent></Card>
      </div>
    );
  }
  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Rooms" description="Classrooms and labs with capacity." action={<Button onClick={() => { setForm({ name: "", room_number: "", type: "Classroom", capacity: 60, status: "Available" }); setEditing("new"); }}><Plus size={16} /> Add Room</Button>} />
      <Card><CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Number</TableHead><TableHead>Type</TableHead><TableHead>Capacity</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {rooms.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.name}</TableCell>
                <TableCell mono>{r.room_number}</TableCell>
                <TableCell><Badge>{r.type}</Badge></TableCell>
                <TableCell mono>{r.capacity}</TableCell>
                <TableCell><span className="flex gap-2">
                  <button onClick={() => { setForm({ name: r.name, room_number: r.room_number, type: r.type, capacity: r.capacity, status: r.status }); setEditing(r.id); }} aria-label="Edit" className="rounded p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Pencil size={16} /></button>
                  <button onClick={() => deleteRoom(r.id)} aria-label="Delete" className="rounded p-1.5 text-[#9A2C2C] hover:bg-red-50"><Trash2 size={16} /></button>
                </span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>
    </div>
  );
}

export function Semesters() {
  const semesters = useStore((s) => s.semesters);
  const addSemester = useStore((s) => s.addSemester);
  const updateSemester = useStore((s) => s.updateSemester);
  const deleteSemester = useStore((s) => s.deleteSemester);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState({ name: "", code: "", status: "Active", academic_year: "2026-27" });

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (editing === "new") addSemester(form);
    else if (typeof editing === "number") updateSemester(editing, form);
    setEditing(null);
  };

  if (editing !== null) {
    return (
      <div className="animate-[fadeIn_0.5s_ease]">
        <PageHeader title={editing === "new" ? "Add Semester" : "Edit Semester"} action={<Button variant="outline" onClick={() => setEditing(null)}><ArrowLeft size={16} /> Back</Button>} />
        <Card><CardContent>
          <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><Label>Name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div><Label>Code</Label><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></div>
            <div className="flex items-end"><Button type="submit">Save Semester</Button></div>
          </form>
        </CardContent></Card>
      </div>
    );
  }
  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Semesters" action={<Button onClick={() => { setForm({ name: "", code: "", status: "Active", academic_year: "2026-27" }); setEditing("new"); }}><Plus size={16} /> Add Semester</Button>} />
      <Card><CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Code</TableHead><TableHead>Status</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {semesters.map((x) => (
              <TableRow key={x.id}>
                <TableCell>{x.name}</TableCell>
                <TableCell mono>{x.code}</TableCell>
                <TableCell><Badge variant="success">{x.status}</Badge></TableCell>
                <TableCell><span className="flex gap-2">
                  <button onClick={() => { setForm({ name: x.name, code: x.code, status: x.status, academic_year: x.academic_year }); setEditing(x.id); }} aria-label="Edit" className="rounded p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Pencil size={16} /></button>
                  <button onClick={() => deleteSemester(x.id)} aria-label="Delete" className="rounded p-1.5 text-[#9A2C2C] hover:bg-red-50"><Trash2 size={16} /></button>
                </span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>
    </div>
  );
}

export function TimeSlots() {
  const slots = useStore((s) => s.slots);
  const addSlot = useStore((s) => s.addSlot);
  const updateSlot = useStore((s) => s.updateSlot);
  const deleteSlot = useStore((s) => s.deleteSlot);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState({ start_time: "09:00", end_time: "10:00", label: "", is_break: false, break_name: "", is_enabled: true });

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    const label = form.label || (form.is_break ? form.break_name || "Break" : `${form.start_time}-${form.end_time}`);
    if (editing === "new") addSlot({ ...form, label });
    else if (typeof editing === "number") updateSlot(editing, { ...form, label });
    setEditing(null);
  };

  if (editing !== null) {
    return (
      <div className="animate-[fadeIn_0.5s_ease]">
        <PageHeader title={editing === "new" ? "Add Time Slot" : "Edit Time Slot"} action={<Button variant="outline" onClick={() => setEditing(null)}><ArrowLeft size={16} /> Back</Button>} />
        <Card><CardContent>
          <form onSubmit={save} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div><Label>Start</Label><Input value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} required /></div>
            <div><Label>End</Label><Input value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} required /></div>
            <div className="flex items-center gap-2">
              <input id="isbreak" type="checkbox" checked={form.is_break} onChange={(e) => setForm({ ...form, is_break: e.target.checked })} />
              <Label htmlFor="isbreak">Is Break?</Label>
            </div>
            {form.is_break ? <div><Label>Break Name</Label><Input value={form.break_name} onChange={(e) => setForm({ ...form, break_name: e.target.value })} /></div> : null}
            <div className="flex items-end"><Button type="submit">Save Slot</Button></div>
          </form>
        </CardContent></Card>
      </div>
    );
  }
  return (
    <div className="animate-[fadeIn_0.5s_ease]">
      <PageHeader title="Time Slots" action={<Button onClick={() => { setForm({ start_time: "09:00", end_time: "10:00", label: "", is_break: false, break_name: "", is_enabled: true }); setEditing("new"); }}><Plus size={16} /> Add Slot</Button>} />
      <Card><CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>Time</TableHead><TableHead>Label</TableHead><TableHead>Type</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {slots.map((t) => (
              <TableRow key={t.id}>
                <TableCell mono>{t.start_time}-{t.end_time}</TableCell>
                <TableCell>{t.label}</TableCell>
                <TableCell>{t.is_break ? <Badge variant="warning">{t.break_name || "Break"}</Badge> : <Badge variant="success">Class</Badge>}</TableCell>
                <TableCell><span className="flex gap-2">
                  <button onClick={() => { setForm({ start_time: t.start_time, end_time: t.end_time, label: t.label, is_break: t.is_break, break_name: t.break_name, is_enabled: t.is_enabled }); setEditing(t.id); }} aria-label="Edit" className="rounded p-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800"><Pencil size={16} /></button>
                  <button onClick={() => deleteSlot(t.id)} aria-label="Delete" className="rounded p-1.5 text-[#9A2C2C] hover:bg-red-50"><Trash2 size={16} /></button>
                </span></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>
    </div>
  );
}
