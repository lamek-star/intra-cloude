import { DeveloperStub } from "@/components/DeveloperStub";

export default async function DeveloperStoragePage(
  props: PageProps<"/orgs/[orgId]/developer/storage">,
) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="storage"
      title="Storage"
      comingSoonTitle="An organization-wide storage view isn't built yet"
      comingSoonDescription="Buckets already exist and are fully functional — upload, download, delete, and share files. They're scoped per project rather than per organization; open a project's page to manage its buckets. This tab will aggregate them across every project once that view exists."
    />
  );
}
