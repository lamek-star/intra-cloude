import AuditLogClient from "./_client";

export default async function AuditLogPage(props: PageProps<"/orgs/[orgId]/audit">) {
  const { orgId } = await props.params;
  return <AuditLogClient orgId={orgId} />;
}
