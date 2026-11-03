import AppTemplatesClient from "./_client";

export default async function AppTemplatesPage(props: PageProps<"/orgs/[orgId]/app-templates">) {
  const { orgId } = await props.params;
  return <AppTemplatesClient orgId={orgId} />;
}
