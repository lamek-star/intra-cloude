"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Film } from "lucide-react";
import { portalDirectory } from "@/lib/portal";

/** The short address on the shop network (https://movies.lan:8443 opens here): straight to the shop's portal
 * when one is open, a choice when several are. */
export default function PortalDirectoryPage() {
  const router = useRouter();
  const shops = useQuery({ queryKey: ["portal-directory"], queryFn: portalDirectory });
  const list = shops.data?.shops ?? [];
  const only = list.length === 1 ? list[0].id : null;

  useEffect(() => {
    if (only) router.replace(`/portal/${only}`);
  }, [only, router]);

  return (
    <main className="grid min-h-screen place-items-center bg-[#0a0d16] p-6 text-slate-100">
      <div className="w-full max-w-sm text-center">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-amber-400/15 text-amber-300">
          <Film className="h-6 w-6" />
        </span>
        {shops.isLoading || only ? (
          <p className="mt-4 text-sm text-slate-400">Opening the shop...</p>
        ) : shops.isError ? (
          <p className="mt-4 text-sm text-red-300">The shop cannot be reached right now. Try again in a moment.</p>
        ) : list.length === 0 ? (
          <>
            <h1 className="mt-4 text-lg font-bold">No shop is open here yet</h1>
            <p className="mt-2 text-sm text-slate-400">Ask at the counter.</p>
          </>
        ) : (
          <>
            <h1 className="mt-4 text-lg font-bold">Choose the shop</h1>
            <ul className="mt-4 flex flex-col gap-2">
              {list.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/portal/${s.id}`}
                    className="block rounded-xl border border-[#252e47] bg-[#141a2b] px-4 py-3 text-left font-semibold hover:border-amber-400"
                  >
                    {s.name}
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </main>
  );
}
