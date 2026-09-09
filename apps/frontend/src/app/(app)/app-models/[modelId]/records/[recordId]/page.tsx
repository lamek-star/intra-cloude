import AppRecordClient from "./_client";

export default async function AppRecordDetailPage(
  props: PageProps<"/app-models/[modelId]/records/[recordId]">,
) {
  const { modelId, recordId } = await props.params;
  return <AppRecordClient modelId={modelId} recordId={recordId} />;
}
