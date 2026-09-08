import SdksClient from "./_client";

export default async function SdksPage(props: PageProps<"/orgs/[orgId]/developer/sdks">) {
  const { orgId } = await props.params;
  return <SdksClient orgId={orgId} />;
}
