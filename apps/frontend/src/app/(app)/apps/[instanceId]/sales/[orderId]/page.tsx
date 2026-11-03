import SalesDocument from "@/components/business/SalesDocument";

export default async function SalesDocumentPage(props: PageProps<"/apps/[instanceId]/sales/[orderId]">) {
  const { orderId } = await props.params;
  return <SalesDocument orderId={orderId} />;
}
