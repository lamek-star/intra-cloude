import ConnectApplicationClient from "./_client";

export default async function ConnectApplicationPage(
  props: PageProps<"/orgs/[orgId]/developer/applications/connect">,
) {
  const { orgId } = await props.params;
  return <ConnectApplicationClient orgId={orgId} />;
}
