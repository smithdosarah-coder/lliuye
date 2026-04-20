import { CustomerPageClient } from "./CustomerPageClient";

export const metadata = {
  title: "客户 · 乾策 Studio",
};

export default async function CustomerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CustomerPageClient id={id} />;
}
