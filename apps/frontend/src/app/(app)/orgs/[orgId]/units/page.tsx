import UnitsClient from "./_client";

export default async function UnitsPage(props: PageProps<"/orgs/[orgId]/units">) {
  const { orgId } = await props.params;
  return <UnitsClient orgId={orgId} />;
}
