import { DeveloperStub } from "@/components/DeveloperStub";

export default async function ApiLogsPage(props: PageProps<"/orgs/[orgId]/developer/api-logs">) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="api-logs"
      title="API Logs"
      comingSoonTitle="A request-by-request API log isn't built yet"
      comingSoonDescription="Every action an application's credential takes is already recorded in the organization's audit log (who/what/when/result) — see the Audit log page. A dedicated log of raw HTTP requests (method, endpoint, status, latency, request ID) hasn't been built yet."
    />
  );
}
