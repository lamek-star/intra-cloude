import TenantDatabaseClient from "./_client";

export default async function TenantDatabasePage(props: PageProps<"/tenant-databases/[dbId]">) {
  const { dbId } = await props.params;
  return <TenantDatabaseClient dbId={dbId} />;
}
