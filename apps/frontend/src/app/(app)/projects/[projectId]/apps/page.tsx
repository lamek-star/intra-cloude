import AppGalleryClient from "./_client";

export default async function AppGalleryPage(props: PageProps<"/projects/[projectId]/apps">) {
  const { projectId } = await props.params;
  return <AppGalleryClient projectId={projectId} />;
}
