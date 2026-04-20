/**
 * <CustomerLink customerId="cust_zrgs">中锐工商</CustomerLink>
 *
 * 任何 view（dispatch / warroom / today / archive 工作区）点客户名
 * → 滑出右侧 CustomerDrawer（AppShell 内已全局挂载）。
 *
 * 语义：行内文本触发器（默认 <button> 外观如文本链接），不跳路由；
 * drawer 里有"打开详情 →"按钮跳 /customer/[id]，这里不抢路由控制。
 *
 * 也可通过 asChild=true 让调用方自己渲染，仅托管 onClick。
 */
"use client";

import {
  cloneElement,
  type HTMLAttributes,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
} from "react";
import { useCustomerDrawerStore } from "@/components/shell/_customer-drawer-store";

type BaseProps = {
  customerId: string;
  children: ReactNode;
  className?: string;
};

type AsChildProps = BaseProps & {
  asChild: true;
  /** asChild 模式下 children 必须是可接受 onClick 的单一元素 */
  children: ReactElement<{ onClick?: (e: MouseEvent) => void }>;
};

type AsButtonProps = BaseProps &
  Omit<HTMLAttributes<HTMLButtonElement>, "onClick" | "children" | "className">;

export function CustomerLink(props: AsChildProps | AsButtonProps) {
  const open = useCustomerDrawerStore((s) => s.open);

  const handle = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    open(props.customerId);
  };

  if ("asChild" in props && props.asChild) {
    const child = props.children as ReactElement<{
      onClick?: (e: MouseEvent) => void;
    }>;
    return cloneElement(child, { onClick: handle });
  }

  const { customerId: _cid, className, children, ...rest } =
    props as AsButtonProps;
  return (
    <button
      type="button"
      className={`customer-link${className ? ` ${className}` : ""}`}
      onClick={handle}
      {...rest}
    >
      {children}
    </button>
  );
}
