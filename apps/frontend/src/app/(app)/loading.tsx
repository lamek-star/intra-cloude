import { PageLoading } from "@/components/ui";

/** Shown inside the app shell the moment a link is clicked, while the next page's code loads, so a click never
 * looks ignored. */
export default function Loading() {
  return <PageLoading />;
}
