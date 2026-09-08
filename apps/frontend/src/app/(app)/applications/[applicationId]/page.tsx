import ApplicationDetailClient from "./_client";

export default async function ApplicationDetailPage(props: PageProps<"/applications/[applicationId]">) {
  const { applicationId } = await props.params;
  return <ApplicationDetailClient applicationId={applicationId} />;
}
