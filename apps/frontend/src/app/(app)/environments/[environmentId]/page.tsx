import EnvironmentDetailClient from "./_client";

export default async function EnvironmentDetailPage(props: PageProps<"/environments/[environmentId]">) {
  const { environmentId } = await props.params;
  return <EnvironmentDetailClient environmentId={environmentId} />;
}
