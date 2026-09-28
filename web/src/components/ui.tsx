import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { cn } from "../utils/cn";

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight text-[#111110] dark:text-[#FAF9F6]">{title}</h1>
        {description ? <p className="mt-1 max-w-2xl text-sm text-neutral-500 dark:text-neutral-400">{description}</p> : null}
      </div>
      {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
    </div>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-sm border border-[#DEDCD3] bg-white shadow-[0_1px_2px_rgba(17,17,16,0.06)] dark:border-neutral-800 dark:bg-[#1C1C1A]", className)}>
      {children}
    </div>
  );
}
export function CardHeader({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("border-b border-[#DEDCD3] px-5 py-4 dark:border-neutral-800", className)}>{children}</div>;
}
export function CardContent({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}

type BtnVariant = "primary" | "secondary" | "outline" | "danger";
export function Button({ variant = "primary", className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant }) {
  const styles: Record<BtnVariant, string> = {
    primary: "bg-[#1C355E] text-white hover:bg-[#16294a] focus-visible:ring-[#1C355E]",
    secondary: "bg-neutral-900 text-white hover:bg-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white",
    outline: "border border-[#DEDCD3] bg-transparent hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800",
    danger: "bg-[#9A2C2C] text-white hover:bg-[#7c2323] focus-visible:ring-[#9A2C2C]",
  };
  return (
    <button
      {...rest}
      className={cn(
        "inline-flex min-h-[40px] items-center justify-center gap-2 rounded-sm px-4 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className
      )}
    />
  );
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
      {children}
    </label>
  );
}
export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      className={cn(
        "h-10 w-full rounded-sm border border-[#DEDCD3] bg-white px-3 text-sm text-[#111110] outline-none transition",
        "focus:border-[#1C355E] focus:ring-2 focus:ring-[#1C355E]/20 disabled:opacity-50",
        "dark:border-neutral-700 dark:bg-neutral-900 dark:text-[#FAF9F6]",
        className
      )}
    />
  );
}
export function Select({ className, children, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...rest}
      className={cn(
        "h-10 w-full rounded-sm border border-[#DEDCD3] bg-white px-3 text-sm outline-none focus:border-[#1C355E] dark:border-neutral-700 dark:bg-neutral-900",
        className
      )}
    >
      {children}
    </select>
  );
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="custom-scrollbar overflow-auto rounded-sm border border-[#DEDCD3] dark:border-neutral-800">
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">{children}</table>
    </div>
  );
}
export function TableHeader({ children }: { children: ReactNode }) {
  return <thead className="bg-[#F3F1EA] dark:bg-neutral-900">{children}</thead>;
}
export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-[#DEDCD3] bg-white dark:divide-neutral-800 dark:bg-[#1C1C1A]">{children}</tbody>;
}
export function TableRow({ children, className }: { children: ReactNode; className?: string }) {
  return <tr className={cn("hover:bg-[#FAF9F6] dark:hover:bg-neutral-800/60", className)}>{children}</tr>;
}
export function TableHead({ children }: { children: ReactNode }) {
  return <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">{children}</th>;
}
export function TableCell({ children, mono }: { children: ReactNode; mono?: boolean }) {
  return <td className={cn("px-4 py-3 align-top", mono && "font-mono text-[13px]")}>{children}</td>;
}

type BadgeVariant = "default" | "success" | "warning" | "danger";
export function Badge({ variant = "default", children }: { variant?: BadgeVariant; children: ReactNode }) {
  const map: Record<BadgeVariant, string> = {
    default: "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200",
    success: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
    warning: "bg-yellow-100 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-300",
    danger: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  };
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium", map[variant])}>{children}</span>;
}
