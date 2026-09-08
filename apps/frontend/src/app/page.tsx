"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { KeyRound, Link2, Server, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button, LinkButton, PageLoading } from "@/components/ui";

const FEATURES = [
  {
    icon: Server,
    title: "Self-Hosted by Design",
    description: "Keep your files, databases and applications on infrastructure you control.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise-Grade Security",
    description: "Protect information using encryption, role-based permissions and audit trails.",
  },
  {
    icon: Link2,
    title: "Built to Connect",
    description:
      "Provide authorized storage and data access to websites, business systems and AI applications.",
  },
];

const CAPABILITIES = [
  "Secure file storage and sharing",
  "A visual relational database builder",
  "Backend storage for websites, mobile apps and AI applications",
  "Desktop, LAN Server and Private Cloud deployment",
  "User roles and permissions",
  "Backup, export, migration and complete restoration",
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  if (loading || user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-canvas">
        <PageLoading />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface-canvas">
      <header className="border-b border-border-subtle bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-64.png" alt="" width={32} height={32} className="h-8 w-8" />
            <span className="text-base font-semibold text-text-primary">IntraForge</span>
          </Link>
          <nav className="flex items-center gap-3">
            <Link
              href="/login"
              className="hidden text-sm font-medium text-slate-600 hover:text-text-primary sm:inline"
            >
              Sign in
            </Link>
            <LinkButton href="/register" variant="primary">
              Get Started
            </LinkButton>
          </nav>
        </div>
      </header>

      <main id="main-content" className="flex-1">
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-navy sm:text-5xl">
              Forge Your Private Cloud
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600">
              Self-hosted infrastructure for organizations that demand security, control and
              flexibility. Manage files, databases and connected applications from one trusted
              platform.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <LinkButton href="/register" variant="primary" className="!px-6 !py-3 !text-base">
                Get Started
              </LinkButton>
              <a href="#product-preview" className="inline-block">
                <Button variant="secondary" className="!px-6 !py-3 !text-base">
                  View Demo
                </Button>
              </a>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Build. Store. Connect. Privately.
            </p>
          </div>
          <div className="hidden justify-center lg:flex" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-512.png" alt="" width={320} height={320} className="h-72 w-72 opacity-90" />
          </div>
        </section>

        <section className="border-y border-border-subtle bg-white py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-8">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              {FEATURES.map((f) => (
                <div key={f.title} className="rounded-2xl border border-border-subtle bg-surface-canvas p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <f.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-text-primary">{f.title}</h3>
                  <p className="mt-1.5 text-sm text-slate-600">{f.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="product-preview" className="mx-auto max-w-6xl px-4 py-16 sm:px-8 sm:py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-semibold tracking-tight text-navy sm:text-3xl">
              One platform for your organization&apos;s infrastructure
            </h2>
            <p className="mt-3 text-base text-slate-600">
              Everything below runs on hardware you own and control — no third-party cloud
              required.
            </p>
          </div>
          <ul className="mx-auto mt-10 grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
            {CAPABILITIES.map((c) => (
              <li
                key={c}
                className="flex items-start gap-2.5 rounded-xl border border-border-subtle bg-white p-4 text-sm text-slate-700"
              >
                <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" aria-hidden="true" />
                {c}
              </li>
            ))}
          </ul>
          <div className="mt-10 flex justify-center">
            <LinkButton href="/register" variant="primary" className="!px-6 !py-3 !text-base">
              Get Started
            </LinkButton>
          </div>
        </section>
      </main>

      <footer className="border-t border-border-subtle bg-white py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 text-sm text-slate-500 sm:flex-row sm:px-8">
          <div className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
            <img src="/brand/icon-48.png" alt="" width={20} height={20} className="h-5 w-5" />
            <span>IntraForge</span>
          </div>
          <p>Self-hosted, local-first business infrastructure.</p>
        </div>
      </footer>
    </div>
  );
}
