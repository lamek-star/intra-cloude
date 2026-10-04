import AppModelClient from "./_client";

export default async function AppModelDetailPage(props: PageProps<"/app-models/[modelId]">) {
  const { modelId } = await props.params;
  return <AppModelClient modelId={modelId} />;
}
