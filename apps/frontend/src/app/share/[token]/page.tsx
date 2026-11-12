"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText } from "lucide-react";

type Shared = { name: string; size: number; mime_type: string; expires_at: string };

function size(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

/** What a share link opens, for anyone who has it: one file's name, size and a Download button. */
export default function SharedFilePage() {
  const { token } = useParams<{ token: string }>();
  const shared = useQuery({
    queryKey: ["share", token],
    queryFn: async () => {
      const r = await fetch(`/api/v1/share/${encodeURIComponent(token)}/`, { credentials: "omit" });
      if (!r.ok) throw new Error(String(r.status));
      return (await r.json()) as Shared;
    },
    retry: false,
  });

  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-blue-600">
          <FileText className="h-6 w-6" aria-hidden="true" />
        </span>
        {shared.isLoading ? (
          <p className="mt-4 text-sm text-slate-500">Opening the link...</p>
        ) : shared.isError || !shared.data ? (
          <>
            <h1 className="mt-4 text-lg font-semibold text-slate-900">This link does not work</h1>
            <p className="mt-2 text-sm text-slate-500">It may have expired, been stopped, or been used up. Ask the person who sent it.</p>
          </>
        ) : (
          <>
            <h1 className="mt-4 text-lg font-semibold break-words text-slate-900">{shared.data.name}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {size(shared.data.size)} · works until {new Date(shared.data.expires_at).toLocaleDateString()}
            </p>
            <a
              href={`/api/v1/share/${encodeURIComponent(token)}/download/`}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Download className="h-4 w-4" aria-hidden="true" /> Download
            </a>
          </>
        )}
      </div>
    </main>
  );
}
