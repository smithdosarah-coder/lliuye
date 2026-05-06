import { CustomerListClient } from "./CustomerListClient";

export const metadata = {
  title: "客户列表 · 乾策 Studio",
};

/**
 * /customer/list · RM 看自己的客户
 * 接 GET /api/customer/list?rm={current_user.id}
 * Phase C Track A · A3 走访闭环第 1 步
 */
export default function CustomerListPage() {
  return <CustomerListClient />;
}
