"use client";

import { useParams } from "next/navigation";
import { Portal } from "@/components/portal/Portal";

/** A Movie Shop's customer portal (ADR-0022 phase 3), opened on the shop Wi-Fi. Not part of IntraForge's signed-in
 * app: customers have their own portal accounts. */
export default function PortalPage() {
  const { shopId } = useParams<{ shopId: string }>();
  return <Portal shopId={shopId} />;
}
