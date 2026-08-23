import AnalyticsClient from "./_client";

export default async function AnalyticsPage(props: PageProps<"/tables/[tableId]/analytics">) {
  const { tableId } = await props.params;
  return <AnalyticsClient tableId={tableId} />;
}
