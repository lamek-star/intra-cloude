import ConnectedDatabaseDetailClient from "./_client";

export default async function ConnectedDatabaseDetailPage(
  props: PageProps<"/connected-databases/[connectedDatabaseId]">,
) {
  const { connectedDatabaseId } = await props.params;
  return <ConnectedDatabaseDetailClient connectedDatabaseId={connectedDatabaseId} />;
}
