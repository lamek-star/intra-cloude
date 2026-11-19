import AuthClient from "./_client";

export default async function DeveloperAuthPage(props: PageProps<"/orgs/[orgId]/developer/auth">) {
  const { orgId } = await props.params;
  return <AuthClient orgId={orgId} />;
}
