import SalesDocument from "@/components/business/SalesDocument";

export default async function SalesDocumentPage(props: PageProps<"/apps/[instanceId]/sales/[orderId]">) {
  const { orderId } = await props.params;
  // "Print invoice" right after a sale opens this page with ?print=1: the print dialog opens by itself.
  const { print } = await props.searchParams;
  return <SalesDocument orderId={orderId} autoPrint={print === "1"} />;
}
