import AppInstanceClient from "./_client";

export default async function AppInstanceDetailPage(props: PageProps<"/app-instances/[instanceId]">) {
  const { instanceId } = await props.params;
  return <AppInstanceClient instanceId={instanceId} />;
}
