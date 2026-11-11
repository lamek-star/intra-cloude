import { DeveloperStub } from "@/components/DeveloperStub";

export default async function DeveloperDatabasePage(
  props: PageProps<"/orgs/[orgId]/developer/database">,
) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="database"
      title="Database"
      comingSoonTitle="An organization-wide database view isn't built yet"
      comingSoonDescription="Tenant databases already exist and are fully functional — build tables, browse and edit rows, import CSVs, run analytics. They're scoped per project rather than per organization; open a project's page to manage its databases. This tab will aggregate them across every project once that view exists."
    />
  );
}
