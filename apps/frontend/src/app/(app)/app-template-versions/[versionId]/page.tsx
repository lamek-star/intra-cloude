import AppTemplateVersionClient from "./_client";

export default async function AppTemplateVersionPage(
  props: PageProps<"/app-template-versions/[versionId]">,
) {
  const { versionId } = await props.params;
  return <AppTemplateVersionClient versionId={versionId} />;
}
