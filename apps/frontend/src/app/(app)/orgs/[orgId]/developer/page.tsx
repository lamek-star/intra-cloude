import DeveloperOverviewClient from "./_client";

export default async function DeveloperOverviewPage(props: PageProps<"/orgs/[orgId]/developer">) {
  const { orgId } = await props.params;
  return <DeveloperOverviewClient orgId={orgId} />;
}
