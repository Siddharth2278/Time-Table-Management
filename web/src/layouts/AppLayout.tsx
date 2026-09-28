import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard, CalendarDays, Users, BookOpen, DoorOpen, Layers,
  Clock, Settings as SettingsIcon, CircleHelp, Menu, FileDown,
} from "lucide-react";
import { useStore } from "../store/useStore";
import { cn } from "../utils/cn";

const NAV = [
  { section: "MAIN" as const, to: "/", label: "Dashboard", icon: LayoutDashboard },
  { section: "MAIN" as const, to: "/timetable", label: "Timetable", icon: CalendarDays },
  { section: "MANAGE" as const, to: "/teachers", label: "Teachers", icon: Users },
  { section: "MANAGE" as const, to: "/subjects", label: "Subjects", icon: BookOpen },
  { section: "MANAGE" as const, to: "/rooms", label: "Rooms", icon: DoorOpen },
  { section: "MANAGE" as const, to: "/semesters", label: "Semesters", icon: Layers },
  { section: "MANAGE" as const, to: "/timeslots", label: "Time Slots", icon: Clock },
  { section: "SYSTEM" as const, to: "/help", label: "Help", icon: CircleHelp },
  { section: "SYSTEM" as const, to: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function AppLayout() {
  const settings = useStore((s) => s.settings);
  const [open, setOpen] = useState(true);
  const [mobile, setMobile] = useState(false);
  const loc = useLocation();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", settings.theme === "dark");
  }, [settings.theme]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const apply = () => {
      setMobile(mq.matches);
      setOpen(!mq.matches);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  const width = open && !mobile ? 260 : 72;
  let lastSection = "";

  return (
    <div className="flex h-full bg-[#FAF9F6] text-[#111110] dark:bg-[#111110] dark:text-[#FAF9F6]">
      {/* Sidebar: isolated column, never overlays content */}
      <aside
        className="flex shrink-0 flex-col border-r border-[#DEDCD3] bg-[#1C355E] text-white dark:border-neutral-800"
        style={{ width }}
      >
        <div className="flex items-center gap-3 px-4 py-5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-white font-serif text-xl font-bold text-[#1C355E]">
            C
          </div>
          {width === 260 ? (
            <div className="min-w-0">
              <div className="truncate font-serif text-base font-semibold leading-tight">College Timetable</div>
              <div className="font-mono text-[11px] uppercase tracking-widest text-white/60">Manager • Offline</div>
            </div>
          ) : null}
        </div>
        <nav className="custom-scrollbar flex-1 overflow-y-auto px-2 pb-4">
          {NAV.map((n) => {
            const showHead = n.section !== lastSection;
            lastSection = n.section;
            const Icon = n.icon;
            return (
              <div key={n.to}>
                {showHead && width === 260 ? (
                  <div className="px-3 pb-1 pt-4 font-mono text-[11px] uppercase tracking-widest text-white/50">{n.section}</div>
                ) : null}
                <NavLink
                  to={n.to}
                  className={({ isActive }) =>
                    cn(
                      "mb-1 flex items-center gap-3 rounded-sm px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive ? "bg-white text-[#1C355E]" : "text-white/75 hover:bg-white/10 hover:text-white"
                    )
                  }
                >
                  <Icon size={18} className="shrink-0" />
                  {width === 260 ? <span className="truncate">{n.label}</span> : null}
                </NavLink>
              </div>
            );
          })}
        </nav>
        <div className="border-t border-white/15 px-4 py-3 font-mono text-[11px] text-white/60">
          {width === 260 ? "v1.0.0 • Offline" : "v1"}
        </div>
      </aside>

      {/* Main column: header + isolated scrollable outlet */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-[#DEDCD3] bg-white px-4 dark:border-neutral-800 dark:bg-[#1C1C1A]">
          <button
            onClick={() => setOpen((v) => !v)}
            className="rounded-sm p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            aria-label="Toggle sidebar"
          >
            <Menu size={20} />
          </button>
          <div className="min-w-0">
            <div className="truncate font-serif text-lg font-semibold leading-tight">{settings.college_name}</div>
            <div className="truncate text-xs text-neutral-500">
              {settings.department} • {settings.academic_year}
            </div>
          </div>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 font-mono text-xs font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
              <span className="h-1.5 w-1.5 rounded-full bg-current" /> Offline Ready
            </span>
            {loc.pathname === "/timetable" ? (
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-2 rounded-sm bg-[#1C355E] px-4 py-2 text-sm font-medium text-white hover:bg-[#16294a]"
              >
                <FileDown size={16} /> Export PDF
              </button>
            ) : null}
          </div>
        </header>
        {/* Each page renders ONLY here; no overlap possible */}
        <main className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <div key={loc.pathname} className="mx-auto w-full max-w-6xl animate-[fadeIn_0.5s_ease]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
