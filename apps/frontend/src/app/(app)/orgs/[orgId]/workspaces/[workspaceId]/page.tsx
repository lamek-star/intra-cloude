import WorkspaceDetailClient from "./_client";

export default async function WorkspaceDetailPage(
  props: PageProps<"/orgs/[orgId]/workspaces/[workspaceId]">,
) {
  const { orgId, workspaceId } = await props.params;
  return <WorkspaceDetailClient orgId={orgId} workspaceId={workspaceId} />;
}
