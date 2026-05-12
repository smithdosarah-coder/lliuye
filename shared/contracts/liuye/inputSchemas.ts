// shared/contracts/liuye/inputSchemas.ts
//
// Liuye Phase 1 · Composer-level input validation (Zod · R7 锁定 3 字段)
//
// v3 spec §2.7 line 311-345 verbatim. 3 字段 (CustomerNo / Product / TermMonths) +
// ValidationMessages 中文 map · 不发明新字段 · 不放宽校验.
//
// safeParse 失败 UX: 字段级 inline error 阻断发送 + 标 composer 参数 chip 上 + 不 toast
// 不 modal (低摩擦修正 · 高频错误不丢上下文). 无 ToolCall / SSE / ledger side effect.
//
// 与 JSON Schema 协议层 (5 schema in ./schemas/) 的分工:
// - JSON Schema = backend/contract codegen 源 · 跨语言 (Python Pydantic + TS interface)
// - inputSchemas.ts = frontend composer 输入校验 · 仅 TS · 在 ToolCall.input 进 SSE 前用
//
// SSOT:
// - v3 spec §2.7 (Zod 3 字段 + 中文 map verbatim)
// - error code 与 backend Pydantic ValueError code 1:1 (验前后一致)

import { z } from 'zod';

const isCustomerNoChecksumValid = (v: string) =>
  v.length === 14 &&
  Number(v.slice(0, 13).split('').reduce((s, n, i) => s + Number(n) * (i + 1), 0)) % 10
    === Number(v[13]);

export const CustomerNoSchema = z.string()
  .regex(/^\d{14}$/, 'CUSTOMER_NO_FORMAT')
  .refine(isCustomerNoChecksumValid, 'CUSTOMER_NO_CHECKSUM');

export const ProductEnumSchema = z.enum(
  ['CORP_CREDIT', 'INCLUSIVE_CREDIT', 'PERSONAL_CREDIT'],
  { message: 'PRODUCT_INVALID' }
);

export const TermMonthsSchema = z.coerce.number()
  .int('TERM_NOT_INTEGER')
  .min(1, 'TERM_OUT_OF_RANGE')
  .max(360, 'TERM_OUT_OF_RANGE');

export const ValidationMessages: Record<string, string> = {
  CUSTOMER_NO_FORMAT: '客户号必须是 14 位数字',
  CUSTOMER_NO_CHECKSUM: '客户号校验位错误',
  PRODUCT_INVALID: '产品类型不支持, 请从 对公授信 / 普惠授信 / 对私授信 中选',
  TERM_NOT_INTEGER: '期限必须是整数月',
  TERM_OUT_OF_RANGE: '期限须在 1-360 月之间',
};
