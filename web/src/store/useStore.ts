import { create } from "zustand";

export interface Semester { id: number; name: string; code: string; status: string; academic_year: string }
export interface Teacher { id: number; name: string; email: string; department: string; designation: string; status: string }
export interface Room { id: number; name: string; room_number: string; type: string; capacity: number; status: string }
export interface Subject {
  id: number; code: string; name: string; semester_id: number;
  subject_type: string; required_lectures_per_week: number; lecture_duration: number;
  teacher_id: number | null; room_id: number | null; room_requirement: string;
}
export interface TimeSlot { id: number; start_time: string; end_time: string; label: string; is_break: boolean; break_name: string; is_enabled: boolean }
export interface TimetableEntry {
  id: number; semester_id: number; subject_id: number; teacher_id: number;
  room_id: number; day_id: number; start_time: string; end_time: string; lecture_type: string;
}
export interface Settings { college_name: string; department: string; academic_year: string; theme: "light" | "dark" }

export const DAYS = [
  { id: 1, name: "Monday" }, { id: 2, name: "Tuesday" }, { id: 3, name: "Wednesday" },
  { id: 4, name: "Thursday" }, { id: 5, name: "Friday" }, { id: 6, name: "Saturday" },
];

let seq = 100;
const nid = () => ++seq;

interface Store {
  semesters: Semester[];
  teachers: Teacher[];
  rooms: Room[];
  subjects: Subject[];
  slots: TimeSlot[];
  entries: TimetableEntry[];
  settings: Settings;
  addSemester: (v: Omit<Semester, "id">) => void;
  updateSemester: (id: number, v: Partial<Semester>) => void;
  deleteSemester: (id: number) => void;
  addTeacher: (v: Omit<Teacher, "id">) => void;
  updateTeacher: (id: number, v: Partial<Teacher>) => void;
  deleteTeacher: (id: number) => void;
  addRoom: (v: Omit<Room, "id">) => void;
  updateRoom: (id: number, v: Partial<Room>) => void;
  deleteRoom: (id: number) => void;
  addSubject: (v: Omit<Subject, "id">) => void;
  updateSubject: (id: number, v: Partial<Subject>) => void;
  deleteSubject: (id: number) => void;
  addSlot: (v: Omit<TimeSlot, "id">) => void;
  updateSlot: (id: number, v: Partial<TimeSlot>) => void;
  deleteSlot: (id: number) => void;
  addEntry: (v: Omit<TimetableEntry, "id">) => void;
  updateEntry: (id: number, v: Partial<TimetableEntry>) => void;
  deleteEntry: (id: number) => void;
  updateSettings: (v: Partial<Settings>) => void;
}

export const useStore = create<Store>((set) => ({
  semesters: [
    { id: 1, name: "Semester 1", code: "SEM1", status: "Active", academic_year: "2026-27" },
    { id: 2, name: "Semester 2", code: "SEM2", status: "Active", academic_year: "2026-27" },
  ],
  teachers: [
    { id: 1, name: "Dr. Alan Turing", email: "turing@college.edu", department: "Computer Science", designation: "Professor", status: "Active" },
    { id: 2, name: "Dr. Ada Lovelace", email: "ada@college.edu", department: "Mathematics", designation: "Associate Professor", status: "Active" },
  ],
  rooms: [
    { id: 1, name: "Room 101", room_number: "101", type: "Classroom", capacity: 60, status: "Available" },
    { id: 2, name: "Computer Lab 1", room_number: "L101", type: "Lab", capacity: 30, status: "Available" },
  ],
  subjects: [
    { id: 1, code: "CS101", name: "Programming Fundamentals", semester_id: 1, subject_type: "Theory", required_lectures_per_week: 4, lecture_duration: 60, teacher_id: 1, room_id: 1, room_requirement: "Classroom" },
  ],
  slots: [
    { id: 1, start_time: "08:00", end_time: "09:00", label: "08:00-09:00", is_break: false, break_name: "", is_enabled: true },
    { id: 2, start_time: "09:00", end_time: "10:00", label: "09:00-10:00", is_break: false, break_name: "", is_enabled: true },
    { id: 3, start_time: "10:00", end_time: "11:00", label: "10:00-11:00", is_break: false, break_name: "", is_enabled: true },
    { id: 4, start_time: "13:00", end_time: "14:00", label: "Lunch Break", is_break: true, break_name: "Lunch Break", is_enabled: true },
  ],
  entries: [
    { id: 1, semester_id: 1, subject_id: 1, teacher_id: 1, room_id: 1, day_id: 1, start_time: "09:00", end_time: "10:00", lecture_type: "Theory" },
  ],
  settings: { college_name: "My College", department: "Computer Science", academic_year: "2026-27", theme: "light" },

  addSemester: (v) => set((s) => ({ semesters: [...s.semesters, { ...v, id: nid() }] })),
  updateSemester: (id, v) => set((s) => ({ semesters: s.semesters.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteSemester: (id) => set((s) => ({ semesters: s.semesters.filter((x) => x.id !== id) })),
  addTeacher: (v) => set((s) => ({ teachers: [...s.teachers, { ...v, id: nid() }] })),
  updateTeacher: (id, v) => set((s) => ({ teachers: s.teachers.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteTeacher: (id) => set((s) => ({ teachers: s.teachers.filter((x) => x.id !== id) })),
  addRoom: (v) => set((s) => ({ rooms: [...s.rooms, { ...v, id: nid() }] })),
  updateRoom: (id, v) => set((s) => ({ rooms: s.rooms.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteRoom: (id) => set((s) => ({ rooms: s.rooms.filter((x) => x.id !== id) })),
  addSubject: (v) => set((s) => ({ subjects: [...s.subjects, { ...v, id: nid() }] })),
  updateSubject: (id, v) => set((s) => ({ subjects: s.subjects.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteSubject: (id) => set((s) => ({ subjects: s.subjects.filter((x) => x.id !== id) })),
  addSlot: (v) => set((s) => ({ slots: [...s.slots, { ...v, id: nid() }] })),
  updateSlot: (id, v) => set((s) => ({ slots: s.slots.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteSlot: (id) => set((s) => ({ slots: s.slots.filter((x) => x.id !== id) })),
  addEntry: (v) => set((s) => ({ entries: [...s.entries, { ...v, id: nid() }] })),
  updateEntry: (id, v) => set((s) => ({ entries: s.entries.map((x) => (x.id === id ? { ...x, ...v } : x)) })),
  deleteEntry: (id) => set((s) => ({ entries: s.entries.filter((x) => x.id !== id) })),
  updateSettings: (v) => set((s) => ({ settings: { ...s.settings, ...v } })),
}));
