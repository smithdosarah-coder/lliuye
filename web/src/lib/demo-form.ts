export const DEMO_FORM_MODE = process.env.NEXT_PUBLIC_DEMO_FORM_MODE === "1";

export const DEMO_FORM_READONLY_MESSAGE =
  "演示环境为只读形态 · 已停用生成、上传与写入";

// 形态模式下人对人 IM 照常（不调模型），只停用 @智能体 → DeepSeek 的路径
export const DEMO_FORM_AGENT_BLOCKED_MESSAGE =
  "演示环境已停用 @智能体 · 消息仅本地演示，不落库";
export const DEMO_FORM_COMPOSER_HINT =
  "演示环境：消息仅本地演示，不落库 · @智能体 已停用";
