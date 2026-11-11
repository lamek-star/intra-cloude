import SettingsClient from "./_client";

export default async function ServiceAppSettingsPage(props: PageProps<"/service-apps/[appId]/settings">) {
  const { appId } = await props.params;
  return <SettingsClient appId={appId} />;
}
