import UsageClient from "./_client";

export default async function UsagePage(props: PageProps<"/orgs/[orgId]/developer/usage">) {
  const { orgId } = await props.params;
  return <UsageClient orgId={orgId} />;
}
