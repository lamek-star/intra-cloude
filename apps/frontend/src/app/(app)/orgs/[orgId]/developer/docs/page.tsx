import DocsClient from "./_client";

export default async function DocsPage(props: PageProps<"/orgs/[orgId]/developer/docs">) {
  const { orgId } = await props.params;
  return <DocsClient orgId={orgId} />;
}
