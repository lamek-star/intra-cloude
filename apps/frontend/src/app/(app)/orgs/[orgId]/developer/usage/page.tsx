import { DeveloperStub } from "@/components/DeveloperStub";

export default async function UsagePage(props: PageProps<"/orgs/[orgId]/developer/usage">) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="usage"
      title="Usage"
      comingSoonTitle="Per-application usage metering isn't built yet"
      comingSoonDescription="Tracking request counts, storage consumption, and rate-limit status per application needs new metering, not just a new page. Not built yet."
    />
  );
}
