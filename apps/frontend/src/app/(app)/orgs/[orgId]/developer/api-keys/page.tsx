import ApiKeysClient from "./_client";

export default async function ApiKeysPage(props: PageProps<"/orgs/[orgId]/developer/api-keys">) {
  const { orgId } = await props.params;
  return <ApiKeysClient orgId={orgId} />;
}
