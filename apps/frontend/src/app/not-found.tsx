import Link from "next/link";
import { LinkButton } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-canvas px-4 text-center">
      {/* eslint-disable-next-line @next/next/no-img-element -- fixed-size static brand asset */}
      <img src="/brand/icon-96.png" alt="" width={44} height={44} className="mb-5 h-11 w-11" />
      <p className="text-sm font-medium text-brand-600">404</p>
      <h1 className="mt-2 text-xl font-semibold text-text-primary">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm text-slate-500">
        The page you&apos;re looking for doesn&apos;t exist, or you may not have access to it.
      </p>
      <div className="mt-6 flex gap-3">
        <LinkButton href="/" variant="primary">
          Go home
        </LinkButton>
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
