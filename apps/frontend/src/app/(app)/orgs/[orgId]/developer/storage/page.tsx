import OrgStorageClient from "../../storage/_client";

/** The organization's buckets (the same list as Organization > Storage), inside the Developer section. */
export default async function DeveloperStoragePage(props: PageProps<"/orgs/[orgId]/developer/storage">) {
  const { orgId } = await props.params;
  return <OrgStorageClient orgId={orgId} inDeveloper />;
}
