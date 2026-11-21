"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Blocks, Code2, FolderOpen, Wallet, type LucideIcon } from "lucide-react";
import {
  FEATURE_DESCRIPTIONS,
  featuresApi,
  featuresQueryKey,
  useFeatures,
  type FeatureGroup,
} from "@/lib/features";
import { Badge, Button, Card, ErrorBanner, PageHeader, PageLoading } from "@/components/ui";

const ICONS: Record<FeatureGroup, LucideIcon> = {
  business_apps: Blocks,
  pay_media: Wallet,
  websites_developer: Code2,
  files_data: FolderOpen,
};

/** Which parts of IntraForge this installation shows (chosen in Setup). Only the Super Administrator changes it. */
export default function FeaturesPage() {
  const qc = useQueryClient();
  const features = useFeatures();
  const [draft, setDraft] = useState<Set<FeatureGroup> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (!features.data) return <PageLoading />;
  const data = features.data;
  const current = new Set(data.groups.filter((g) => g.enabled).map((g) => g.key));
  const chosen = draft ?? current;
  const changed =
    draft !== null && (draft.size !== current.size || [...draft].some((g) => !current.has(g)));

  function toggle(group: FeatureGroup) {
    const next = new Set(chosen);
    if (next.has(group)) next.delete(group);
    else next.add(group);
    setDraft(next);
    setSaved(false);
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const order = data.groups.map((g) => g.key).filter((g) => chosen.has(g));
      qc.setQueryData(featuresQueryKey, await featuresApi.set(order));
      setDraft(null);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The features could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Features"
        description="Which parts of IntraForge this installation shows. Switching a part off hides it for everyone and the server refuses it; nothing is deleted, and switching it back on brings everything back."
      />
      <Card className="flex flex-col gap-3">
        <ul className="flex flex-col gap-2">
          {data.groups.map((g) => {
            const Icon = ICONS[g.key];
            const on = chosen.has(g.key);
            return (
              <li key={g.key}>
                <label
                  className={`flex items-start gap-3 rounded-xl border p-4 ${on ? "border-brand-300 bg-brand-50/40" : "border-slate-200"} ${data.can_change ? "cursor-pointer" : ""}`}
                >
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4"
                    checked={on}
                    disabled={!data.can_change || busy}
                    onChange={() => toggle(g.key)}
                  />
                  <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900">{g.label}</span>
                      <Badge tone={g.enabled ? "success" : "default"}>{g.enabled ? "On" : "Off"}</Badge>
                    </span>
                    <span className="mt-0.5 block text-sm text-slate-500">{FEATURE_DESCRIPTIONS[g.key]}</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        {error && <ErrorBanner message={error} />}
        {data.can_change ? (
          <div className="flex items-center justify-end gap-3">
            {saved && (
              <span className="text-sm text-green-700">Saved. Everyone sees the change on their next page.</span>
            )}
            <Button variant="secondary" onClick={() => setDraft(null)} disabled={!changed || busy}>
              Undo
            </Button>
            <Button onClick={() => void save()} disabled={!changed || busy}>
              {busy ? "Saving..." : "Save"}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Only the Super Administrator can change which parts are shown.</p>
        )}
      </Card>
    </div>
  );
}
