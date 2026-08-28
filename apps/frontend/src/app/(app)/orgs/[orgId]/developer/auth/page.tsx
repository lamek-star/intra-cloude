import { DeveloperStub } from "@/components/DeveloperStub";

export default async function DeveloperAuthPage(props: PageProps<"/orgs/[orgId]/developer/auth">) {
  const { orgId } = await props.params;
  return (
    <DeveloperStub
      orgId={orgId}
      tabKey="auth"
      title="Auth"
      comingSoonTitle="Letting applications authenticate end users isn't built yet"
      comingSoonDescription="Applications authenticate to Intra-Cloud's own API today via a bearer-token credential — see the SDKs tab for how. Issuing sign-in for an application's own end users (OAuth/OIDC, SSO) is a larger, separate feature that hasn't been designed yet."
    />
  );
}
