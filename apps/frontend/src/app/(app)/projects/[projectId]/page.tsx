import ProjectDetailClient from "./_client";

export default async function ProjectDetailPage(props: PageProps<"/projects/[projectId]">) {
  const { projectId } = await props.params;
  return <ProjectDetailClient projectId={projectId} />;
}
