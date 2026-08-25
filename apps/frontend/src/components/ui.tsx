"use client";

import Link from "next/link";
import { Check, Copy, X } from "lucide-react";
import { useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#F5F6FB]";
  const sizes = { sm: "px-2.5 py-1.5 text-xs", md: "px-3.5 py-2 text-sm" };
  const variants = {
    primary: "bg-indigo-600 text-white shadow-sm hover:bg-indigo-500 focus-visible:ring-indigo-500",
    secondary:
      "bg-white text-slate-700 border border-slate-200 shadow-sm hover:bg-slate-50 focus-visible:ring-slate-300",
    danger: "bg-red-600 text-white shadow-sm hover:bg-red-500 focus-visible:ring-red-500",
    ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-slate-300",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props} />
  );
}

export function LinkButton({
  href,
  variant = "secondary",
  size = "md",
  className = "",
  children,
}: {
  href: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
  className?: string;
  children: ReactNode;
}) {
  const base = "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors";
  const sizes = { sm: "px-2.5 py-1.5 text-xs", md: "px-3.5 py-2 text-sm" };
  const variants = {
    primary: "bg-indigo-600 text-white shadow-sm hover:bg-indigo-500",
    secondary: "bg-white text-slate-700 border border-slate-200 shadow-sm hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
  };
  return (
    <Link href={href} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  );
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 ${className}`}
      {...props}
    />
  );
}

export function Textarea({
  className = "",
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 ${className}`}
      {...props}
    />
  );
}

export function Select({
  className = "",
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 ${className}`}
      {...props}
    />
  );
}

export function Checkbox(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type="checkbox"
      className="h-4 w-4 rounded border-slate-300 bg-white text-indigo-600 focus:ring-indigo-500/30"
      {...props}
    />
  );
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium text-slate-500">
      {children}
    </label>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-slate-200/70 bg-white p-5 shadow-[0_1px_2px_rgba(16,24,40,0.04)] ${className}`}>
      {children}
    </div>
  );
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "info";
}) {
  const tones = {
    default: "bg-slate-100 text-slate-600",
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-red-50 text-red-700",
    info: "bg-indigo-50 text-indigo-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export function PageLoading() {
  return (
    <div className="flex h-64 items-center justify-center text-slate-400">
      <Spinner className="h-6 w-6" />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white/60 px-6 py-14 text-center">
      <p className="text-sm font-medium text-slate-800">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </div>
  );
}

/** Copies `value` to the clipboard, showing a brief confirmation instead
 * of the label. Falls back silently if the Clipboard API is unavailable
 * (e.g. non-HTTPS context) — the value is still visible to select/copy
 * manually. */
export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Clipboard API unavailable; the value remains visible to copy by hand.
        }
      }}
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : label}
    </button>
  );
}

/** A secret shown exactly once at creation/rotation time. Never re-fetch
 * or persist this value across a reload — the backend genuinely cannot
 * return it again (only its hash is stored). */
export function SecretReveal({
  label = "This secret is shown only once",
  secret,
}: {
  label?: string;
  secret: string;
}) {
  return (
    <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <p className="text-xs font-medium text-amber-800">{label} — copy it now.</p>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded bg-slate-900 px-2 py-1.5 font-mono text-xs text-slate-100">
          {secret}
        </code>
        <CopyButton value={secret} />
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
}: {
  title: string;
  description?: string;
  breadcrumbs?: { label: string; href?: string }[];
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="mb-2 flex items-center gap-1.5 text-xs text-slate-400">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-slate-300">/</span>}
                {crumb.href ? (
                  <Link href={crumb.href} className="hover:text-slate-600">
                    {crumb.label}
                  </Link>
                ) : (
                  <span>{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200/70 bg-white">
      <table className="w-full min-w-full text-left text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
      <tr>{children}</tr>
    </thead>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return <th className="px-4 py-2.5 font-medium whitespace-nowrap">{children}</th>;
}

export function Td({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={`px-4 py-2.5 text-slate-700 ${className}`}>{children}</td>;
}

export function TRow({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={`border-b border-slate-100 last:border-0 ${onClick ? "cursor-pointer hover:bg-slate-50" : ""}`}
    >
      {children}
    </tr>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const STAT_ACCENTS = {
  amber: { icon: "bg-amber-50 text-amber-600", bar: "bg-gradient-to-r from-amber-300 to-amber-500" },
  emerald: {
    icon: "bg-emerald-50 text-emerald-600",
    bar: "bg-gradient-to-r from-emerald-300 to-emerald-500",
  },
  blue: { icon: "bg-blue-50 text-blue-600", bar: "bg-gradient-to-r from-blue-300 to-blue-500" },
  violet: {
    icon: "bg-violet-50 text-violet-600",
    bar: "bg-gradient-to-r from-violet-300 to-violet-500",
  },
} as const;

/** A colored-accent stat tile (icon badge + label + big number), matching
 * the professionalization brief's dashboard reference. Deliberately has
 * no trend/sparkline — Intra-Cloud doesn't record historical snapshots
 * of these counts, and a fabricated trend line would misrepresent real
 * data (Section 72: never fake completion/data). The accent bar at the
 * bottom is decoration only, not a chart. */
export function StatCard({
  icon: Icon,
  label,
  value,
  accent,
  detail,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  accent: keyof typeof STAT_ACCENTS;
  detail?: string;
}) {
  const tone = STAT_ACCENTS[accent];
  return (
    <Card className="overflow-hidden !p-0">
      <div className="p-5">
        <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${tone.icon}`}>
          <Icon className="h-4 w-4" />
        </div>
        <p className="mt-3 text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-0.5 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
        {detail && <p className="mt-1 text-xs text-slate-400">{detail}</p>}
      </div>
      <div className={`h-1 w-full ${tone.bar}`} />
    </Card>
  );
}
