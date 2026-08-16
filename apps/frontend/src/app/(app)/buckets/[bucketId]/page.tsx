import BucketDetailClient from "./_client";

export default async function BucketDetailPage(props: PageProps<"/buckets/[bucketId]">) {
  const { bucketId } = await props.params;
  const searchParams = await props.searchParams;
  const name = typeof searchParams.name === "string" ? searchParams.name : null;
  const projectId = typeof searchParams.project === "string" ? searchParams.project : null;
  return <BucketDetailClient bucketId={bucketId} initialName={name} projectId={projectId} />;
}
