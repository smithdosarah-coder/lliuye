"""Wrapper: 带环境变量运行 v16_classifier.py。

2026-04-22 安全修复: 原硬编 DEEPSEEK_API_KEY 已轮换并改为从项目根 .env 加载。
新机器首次部署: cp .env.example .env 后填 DEEPSEEK_API_KEY 实际值。
"""
import os, sys
from pathlib import Path

# 1. 加载项目根 .env(极简 parser,与 scripts/start_uvicorn.py 一致语义)
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        _v = _v.strip()
        if len(_v) >= 2 and _v[0] == _v[-1] and _v[0] in ("'", '"'):
            _v = _v[1:-1]
        os.environ.setdefault(_k.strip(), _v)

# 2. DeepSeek 是国内服务,不走海外代理
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "api.deepseek.com,dashscope.aliyuncs.com,open.bigmodel.cn"

# 3. 校验必需 key
if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
    sys.exit("[run_v16_classifier] DEEPSEEK_API_KEY 缺失: cp .env.example .env 并填值后重试")

os.environ.setdefault("CLASSIFIER_PROVIDER", "deepseek")
os.chdir(r"D:\claude code\credit_report_agent_work")
sys.path.insert(0, ".")
import runpy
runpy.run_path("v16_classifier.py", run_name="__main__")
