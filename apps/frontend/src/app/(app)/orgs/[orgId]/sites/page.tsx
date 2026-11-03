import SitesClient from "./_client";

export default async function SitesPage(props: PageProps<"/orgs/[orgId]/sites">) {
  const { orgId } = await props.params;
  return <SitesClient orgId={orgId} />;
}
