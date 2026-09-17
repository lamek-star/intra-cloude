import WebhooksClient from "./_client";

export default async function WebhooksPage(props: PageProps<"/orgs/[orgId]/developer/webhooks">) {
  const { orgId } = await props.params;
  return <WebhooksClient orgId={orgId} />;
}
