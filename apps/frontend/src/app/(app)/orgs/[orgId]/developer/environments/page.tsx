import { DeveloperStub } from "@/components/DeveloperStub";

export default async function EnvironmentsPage(
  props: PageProps<"/orgs/[orgId]/developer/environments">,
) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="environments"
      title="Environments"
      comingSoonTitle="Per-environment credentials aren't built yet"
      comingSoonDescription="Separating development, staging, and production configuration and credentials per application needs a new Environment model scoped to Application. Every credential an application issues today works the same way in every context it's used."
    />
  );
}
