import BusinessApp from "@/components/business/BusinessApp";

export default async function BusinessAppLayout(props: LayoutProps<"/apps/[instanceId]">) {
  const { instanceId } = await props.params;
  return <BusinessApp instanceId={instanceId}>{props.children}</BusinessApp>;
}
