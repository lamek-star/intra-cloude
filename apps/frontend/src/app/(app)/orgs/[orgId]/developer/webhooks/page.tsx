import { DeveloperStub } from "@/components/DeveloperStub";

export default async function WebhooksPage(props: PageProps<"/orgs/[orgId]/developer/webhooks">) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="webhooks"
      title="Webhooks"
      comingSoonTitle="Event delivery isn't built yet"
      comingSoonDescription="Notifying an application's own endpoint when something happens in Intra-Cloud (a file uploads, a record changes, a credential rotates) needs a new signed-delivery system with retries and a delivery history. Not built yet."
    />
  );
}
