import OrgDatabasesClient from "./_client";

export default async function OrgDatabasesPage(props: PageProps<"/orgs/[orgId]/databases">) {
  const { orgId } = await props.params;
  return <OrgDatabasesClient orgId={orgId} />;
}
