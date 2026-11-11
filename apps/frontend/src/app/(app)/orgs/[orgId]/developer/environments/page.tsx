import EnvironmentsClient from "./_client";

export default async function EnvironmentsPage(
  props: PageProps<"/orgs/[orgId]/developer/environments">,
) {
  const { orgId } = await props.params;
  return <EnvironmentsClient orgId={orgId} />;
}
