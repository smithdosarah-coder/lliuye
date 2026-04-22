# -*- coding: utf-8 -*-
"""信贷 AI 智能体矩阵 · uvicorn 启动 wrapper。

替代历史上的 /tmp/start_uvicorn.py(临时文件易丢失)。本文件入 git,跨机器/
跨重启稳定可用。

行为:
  1. 从项目根 .env 加载环境变量(无 python-dotenv 依赖,内置极简 parser)
  2. 校验必需的 LLM key,缺失时给出可执行的修复提示
  3. 调用 uvicorn 启动 api_server:app

用法:
  py scripts/start_uvicorn.py              # 默认 0.0.0.0:8000 + --reload
  py scripts/start_uvicorn.py --no-reload  # 生产模式
  PORT=8001 py scripts/start_uvicorn.py    # 覆盖端口

新机器首次部署:
  cp .env.example .env
  # 编辑 .env 填实际 DEEPSEEK_API_KEY / TAVILY_API_KEY
  py scripts/start_uvicorn.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> dict[str, str]:
    """极简 .env parser: KEY=VALUE 一行,忽略 # 注释 / 空行 / export 前缀。

    不覆盖已存在的 os.environ(命令行 PORT=xxx py ... 优先)。
    """
    if not path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # 去掉首尾成对引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded


def assert_required_keys() -> None:
    """LLM key 缺失就明确告诉用户怎么修,而不是让 api_server 启动后才 500。"""
    missing = []
    deepseek = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not deepseek or deepseek.startswith("sk-your-"):
        missing.append("DEEPSEEK_API_KEY")
    if missing:
        print("[start_uvicorn] 缺失必需 env: " + ", ".join(missing), file=sys.stderr)
        print("[start_uvicorn] 修复:", file=sys.stderr)
        print("  1. cp .env.example .env  (若 .env 不存在)", file=sys.stderr)
        print("  2. 编辑 .env 填实际 key", file=sys.stderr)
        print("  3. 重新 py scripts/start_uvicorn.py", file=sys.stderr)
        sys.exit(2)
    # Tavily 缺失只 warn(KB_SCAN_DEMO_MODE=true 场景可省)
    if not os.environ.get("TAVILY_API_KEY", "").strip() or os.environ.get("TAVILY_API_KEY", "").startswith("tvly-your-"):
        if os.environ.get("KB_SCAN_DEMO_MODE", "true").lower() != "true":
            print("[start_uvicorn] WARN: TAVILY_API_KEY 缺失且 KB_SCAN_DEMO_MODE != true,Agent1/4/5 真实模式会失败", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动 api_server with .env loading")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=None, help="覆盖 .env 的 PORT(默认 8000)")
    parser.add_argument("--no-reload", action="store_true", help="关闭 --reload(生产模式)")
    parser.add_argument("--check", action="store_true", help="只校验 env,不启动服务")
    args = parser.parse_args()

    env_path = PROJECT_ROOT / ".env"
    loaded = load_dotenv(env_path)
    print(f"[start_uvicorn] loaded {len(loaded)} keys from {env_path}", file=sys.stderr)

    assert_required_keys()

    port = args.port if args.port is not None else int(os.environ.get("PORT", "8000"))

    if args.check:
        print(f"[start_uvicorn] env OK · would start on {args.host}:{port}")
        return

    os.chdir(PROJECT_ROOT)
    try:
        import uvicorn
    except ImportError:
        print("[start_uvicorn] uvicorn 未安装,跑 pip install -r requirements.txt", file=sys.stderr)
        sys.exit(3)
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=port,
        reload=not args.no_reload,
    )


if __name__ == "__main__":
    main()
