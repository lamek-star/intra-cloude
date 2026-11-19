import OrgDatabasesClient from "../../databases/_client";

/** The organization's databases (the same list as Organization > Databases), inside the Developer section. */
export default async function DeveloperDatabasePage(props: PageProps<"/orgs/[orgId]/developer/database">) {
  const { orgId } = await props.params;
  return <OrgDatabasesClient orgId={orgId} inDeveloper />;
}
