import ProductDetail from "@/components/business/ProductDetail";

export default async function ProductPage(props: PageProps<"/apps/[instanceId]/products/[partId]">) {
  const { partId } = await props.params;
  return <ProductDetail partId={partId} />;
}
