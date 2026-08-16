import OrgDetailClient from "./_client";

export default async function OrgDetailPage(props: PageProps<"/orgs/[orgId]">) {
  const { orgId } = await props.params;
  return <OrgDetailClient orgId={orgId} />;
}
