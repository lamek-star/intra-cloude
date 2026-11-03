import OpenClient from "./_client";

export default async function OpenServiceAppPage(props: PageProps<"/service-apps/[appId]/open">) {
  const { appId } = await props.params;
  return <OpenClient appId={appId} />;
}
