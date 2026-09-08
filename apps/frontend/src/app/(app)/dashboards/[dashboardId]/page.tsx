import DashboardClient from "./_client";

export default async function DashboardPage(props: PageProps<"/dashboards/[dashboardId]">) {
  const { dashboardId } = await props.params;
  return <DashboardClient dashboardId={dashboardId} />;
}
