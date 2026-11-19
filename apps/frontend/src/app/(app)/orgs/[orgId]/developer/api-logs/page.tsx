import ApiLogsClient from "./_client";

export default async function ApiLogsPage(props: PageProps<"/orgs/[orgId]/developer/api-logs">) {
  const { orgId } = await props.params;
  return <ApiLogsClient orgId={orgId} />;
}
