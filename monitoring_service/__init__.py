"""Monitoring service package · Stage E.2 (onboarding W-E2-A3).

Production 24/7 ops · 4 pillars:
- metrics.py     · Prometheus exporter (FastAPI middleware) · graceful no-dep fallback
- sentry_init.py · Sentry SDK init · DSN env · graceful no-dep fallback
- alerts.py      · Alert rules engine (LLM down / 5xx burst / Tavily 401 burst)
- health.py      · Extended /health/extended (LLM + Tavily + sqlite + 6 Agent ping)

设计原则 (与 backend 各 module 一致):
- 第三方 dep 缺时 silent skip · 不阻断主进程 (例: prometheus_client / sentry_sdk
  未安装 → metrics 走 NoOp · sentry init 直 return)
- 所有 endpoint 失败优雅降级 · 返结构化 error 不抛 500
- env 配置 (SENTRY_DSN / METRICS_ENABLED) · 缺则 disable
"""
