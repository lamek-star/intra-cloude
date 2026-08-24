import ApplicationsClient from "./_client";

export default async function ApplicationsPage(props: PageProps<"/orgs/[orgId]/applications">) {
  const { orgId } = await props.params;
  return <ApplicationsClient orgId={orgId} />;
}
