import AppTemplateClient from "./_client";

export default async function AppTemplateDetailPage(props: PageProps<"/app-templates/[templateId]">) {
  const { templateId } = await props.params;
  return <AppTemplateClient templateId={templateId} />;
}
