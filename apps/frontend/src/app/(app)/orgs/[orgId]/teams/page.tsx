import TeamsClient from "./_client";

export default async function TeamsPage(props: PageProps<"/orgs/[orgId]/teams">) {
  const { orgId } = await props.params;
  return <TeamsClient orgId={orgId} />;
}
