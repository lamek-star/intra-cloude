import { Catalogue } from "@/components/movies/Catalogue";

export default async function MovieShopPage(props: PageProps<"/movies/[shopId]">) {
  const { shopId } = await props.params;
  return <Catalogue shopId={shopId} />;
}
