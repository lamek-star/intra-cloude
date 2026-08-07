export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 px-6 text-center dark:bg-black">
      <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
        Private Data Cloud
      </h1>
      <p className="mt-3 max-w-md text-zinc-600 dark:text-zinc-400">
        Phase 1 scaffold — no product features yet. See{" "}
        <code className="rounded bg-black/[.06] px-1.5 py-0.5 font-mono text-sm dark:bg-white/[.08]">
          docs/architecture/ROADMAP.md
        </code>{" "}
        in the repository root for the implementation plan.
      </p>
    </div>
  );
}
