"use client";

// Design-system check page: every shipped primitive from components/ui.tsx in every state, on one screen.
// Drop in as apps/frontend/src/app/design/page.tsx (outside the (app) group, so it needs no sign-in).
// It renders no real data and calls no API. Remove it, or gate it to development builds, before release.

import { Database, FolderOpen, HardDrive, Upload } from "lucide-react";
import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  ComingSoon,
  CopyButton,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  LinkButton,
  Modal,
  PageHeader,
  SecretReveal,
  Select,
  Spinner,
  StatCard,
  Table,
  Td,
  Th,
  THead,
  TRow,
  Textarea,
} from "@/components/ui";

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="space-y-3">
      <h2 id={id} className="text-lg font-semibold tracking-tight text-text">
        {title}
      </h2>
      {children}
    </section>
  );
}

const SWATCHES: [string, string][] = [
  ["bg", "bg-bg"],
  ["surface", "bg-surface"],
  ["surface-sunken", "bg-surface-sunken"],
  ["border", "bg-border"],
  ["border-input", "bg-border-input"],
  ["text", "bg-text"],
  ["text-body", "bg-text-body"],
  ["text-muted", "bg-text-muted"],
  ["accent", "bg-accent"],
  ["accent-hover", "bg-accent-hover"],
  ["focus", "bg-focus"],
  ["chrome", "bg-chrome"],
  ["nav-active", "bg-nav-active"],
  ["danger", "bg-danger"],
  ["danger-hover", "bg-danger-hover"],
  ["success", "bg-success"],
  ["warning", "bg-warning"],
];

export default function DesignPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  return (
    <main id="main-content" className="mx-auto w-full max-w-[1280px] space-y-10 px-4 py-8 sm:px-6">
      <PageHeader
        title="Design system"
        description="Every primitive in every state, with the WCAG AA token fixes applied."
        breadcrumbs={[{ label: "IntraForge", href: "/" }, { label: "Design system" }]}
        actions={<Button>Primary action</Button>}
      />

      <Section id="colours" title="Colour roles">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {SWATCHES.map(([name, cls]) => (
            <div key={name} className="overflow-hidden rounded-lg border border-border bg-surface">
              <div className={`h-12 ${cls}`} />
              <p className="px-2 py-1.5 font-mono text-xs text-text-body">{name}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section id="type" title="Type">
        <Card className="space-y-2">
          <p className="text-2xl font-semibold tracking-tight text-text">Page title 24/600</p>
          <p className="text-lg font-semibold tracking-tight text-text">Section title 18/600</p>
          <p className="text-sm font-semibold text-text">Card title 14/600</p>
          <p className="max-w-2xl text-sm text-text-body">
            Body 14/400. Fourteen pixels is the floor for anything someone must read to act.
          </p>
          <p className="text-xs font-medium text-text-muted">Label 12/500</p>
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Table header 12/500</p>
          <p className="font-mono text-xs tabular-nums text-text-body">mono 3f9a0c21 · 1,284,551 bytes</p>
        </Card>
      </Section>

      <Section id="buttons" title="Buttons">
        <Card className="space-y-4">
          {(["md", "sm"] as const).map((size) => (
            <div key={size} className="flex flex-wrap items-center gap-3">
              <Button size={size}>Primary</Button>
              <Button size={size} variant="secondary">
                Secondary
              </Button>
              <Button size={size} variant="danger">
                Delete
              </Button>
              <Button size={size} variant="ghost">
                Ghost
              </Button>
              <Button size={size} disabled>
                Disabled
              </Button>
              <Button
                size={size}
                aria-busy={loading}
                disabled={loading}
                onClick={() => {
                  setLoading(true);
                  setTimeout(() => setLoading(false), 1500);
                }}
              >
                {loading ? <Spinner className="h-4 w-4 motion-safe-spin" /> : <Upload className="h-4 w-4" aria-hidden="true" />}
                Upload
              </Button>
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-3">
            <LinkButton href="#buttons" variant="primary">
              Link primary
            </LinkButton>
            <LinkButton href="#buttons">Link secondary</LinkButton>
            <CopyButton value="https://localhost:8445/sample/" label="Copy address" />
          </div>
        </Card>
      </Section>

      <Section id="forms" title="Form controls">
        <Card className="grid gap-4 md:grid-cols-2">
          <div>
            <Label htmlFor="d-name">Bucket name</Label>
            <Input id="d-name" placeholder="shared-docs" />
          </div>
          <div>
            <Label htmlFor="d-invalid">Bucket name (invalid)</Label>
            <Input
              id="d-invalid"
              defaultValue="Shared Docs"
              aria-invalid="true"
              aria-describedby="d-invalid-err"
              className="!border-danger"
            />
            <p id="d-invalid-err" className="mt-1 text-xs text-danger-fg">
              Use lowercase letters, numbers and hyphens.
            </p>
          </div>
          <div>
            <Label htmlFor="d-select">Expires after</Label>
            <Select id="d-select" defaultValue="24h">
              <option value="1h">1 hour</option>
              <option value="24h">24 hours</option>
              <option value="7d">7 days</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="d-disabled">Disabled</Label>
            <Input id="d-disabled" disabled defaultValue="Read only value" />
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="d-notes">Notes</Label>
            <Textarea id="d-notes" rows={3} placeholder="Why is this link needed?" />
          </div>
          <label className="flex items-center gap-2 text-sm text-text-body">
            <Checkbox defaultChecked /> Keep previous versions
          </label>
        </Card>
      </Section>

      <Section id="badges" title="Badges">
        <div className="flex flex-wrap gap-2">
          <Badge>Default</Badge>
          <Badge tone="success">Online</Badge>
          <Badge tone="warning">Production</Badge>
          <Badge tone="danger">Denied</Badge>
          <Badge tone="info">Planned, not yet built</Badge>
        </div>
      </Section>

      <Section id="stats" title="Stat cards">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard icon={FolderOpen} label="Buckets" value={3} accent="blue" detail="across 2 projects" />
          <StatCard icon={Database} label="Databases" value={2} accent="teal" />
          <StatCard icon={HardDrive} label="Storage used" value="1.2 GB" accent="green" detail="of 50 GB" />
          <StatCard icon={Upload} label="Uploads today" value={0} accent="amber" />
        </div>
      </Section>

      <Section id="table" title="Table">
        <Table>
          <THead>
            <Th>Name</Th>
            <Th>Size</Th>
            <Th>Modified</Th>
            <Th>Status</Th>
          </THead>
          <tbody>
            <TRow onClick={() => setModalOpen(true)}>
              <Td>invoice-0042.pdf</Td>
              <Td className="font-mono tabular-nums">184,220</Td>
              <Td className="font-mono tabular-nums">2026-11-01 11:45</Td>
              <Td>
                <Badge tone="success">Active</Badge>
              </Td>
            </TRow>
            <TRow onClick={() => setModalOpen(true)}>
              <Td>price-list.xlsx</Td>
              <Td className="font-mono tabular-nums">22,016</Td>
              <Td className="font-mono tabular-nums">2026-10-31 15:01</Td>
              <Td>
                <Badge tone="danger">Quarantined</Badge>
              </Td>
            </TRow>
          </tbody>
        </Table>
      </Section>

      <Section id="states" title="States">
        <div className="grid gap-4 lg:grid-cols-2">
          <EmptyState
            title="No files yet"
            description="Upload a file to get started."
            action={<Button size="sm">Upload files</Button>}
          />
          <ComingSoon title="Usage" description="Request counts and storage per application." />
          <ErrorBanner
            message="The upload could not be saved. Your file is still selected; try again."
            error={{ status: 503, code: "object_storage_unavailable", requestId: "req_7f3a9c" }}
          />
          <SecretReveal secret="ifk_live_7d1c3e9a5b2f4c6d8e0a1b3c5d7e9f1a" />
          <Card className="flex items-center gap-3 text-sm text-text-body">
            <Spinner className="h-5 w-5 text-text-muted motion-safe-spin" /> Loading…
          </Card>
        </div>
      </Section>

      <Section id="overlays" title="Overlays">
        <Button variant="secondary" onClick={() => setModalOpen(true)}>
          Open modal
        </Button>
        <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Share invoice-0042.pdf">
          <div className="space-y-4">
            <div>
              <Label htmlFor="m-exp">Expires after</Label>
              <Select id="m-exp" defaultValue="24h">
                <option value="24h">24 hours</option>
                <option value="7d">7 days</option>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setModalOpen(false)}>Create link</Button>
            </div>
          </div>
        </Modal>
      </Section>
    </main>
  );
}
