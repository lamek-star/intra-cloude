import ImportClient from "./_client";

export default async function ImportPage(props: PageProps<"/tables/[tableId]/import">) {
  const { tableId } = await props.params;
  return <ImportClient tableId={tableId} />;
}
