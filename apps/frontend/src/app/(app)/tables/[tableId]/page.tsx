import TableDetailClient from "./_client";

export default async function TableDetailPage(props: PageProps<"/tables/[tableId]">) {
  const { tableId } = await props.params;
  return <TableDetailClient tableId={tableId} />;
}
