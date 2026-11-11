"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { licenceApi, licenceNotice } from "@/lib/license";

const TONE = {
  info: "border-brand-200 bg-brand-50 text-brand-900",
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  danger: "border-red-300 bg-red-50 text-red-900",
};

/** A thin line above every page while the licence needs attention (trial days left, or read-only). */
export function LicenceBanner() {
  const licence = useQuery({
    queryKey: ["licence"],
    queryFn: licenceApi.get,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const notice = licenceNotice(licence.data);
  if (!notice) return null;
  return (
    <div
      role={notice.tone === "danger" ? "alert" : "status"}
      className={`flex flex-wrap items-center gap-2 border-b px-4 py-2 text-sm sm:px-8 ${TONE[notice.tone]}`}
    >
      <KeyRound className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="flex-1">{notice.text}</span>
      <Link
        href="/license"
        className="font-semibold underline underline-offset-2"
      >
        Licence
      </Link>
    </div>
  );
}
