import { DeveloperStub } from "@/components/DeveloperStub";

export default async function ApiKeysPage(props: PageProps<"/orgs/[orgId]/developer/api-keys">) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="api-keys"
      title="API Keys"
      comingSoonTitle="A cross-application key list isn't built yet"
      comingSoonDescription="Credentials already exist and are fully functional: issue, rotate, and revoke them from each application's own page. This tab will collect all of an organization's issued credentials into one list — open Applications to manage them per application for now."
    />
  );
}
