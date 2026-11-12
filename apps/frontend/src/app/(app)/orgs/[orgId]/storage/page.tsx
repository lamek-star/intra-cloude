import OrgStorageClient from "./_client";

export default async function OrgStoragePage(props: PageProps<"/orgs/[orgId]/storage">) {
  const { orgId } = await props.params;
  return <OrgStorageClient orgId={orgId} />;
}
