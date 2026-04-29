# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警雷达 — 独立启动入口（v2.0 thin wrapper）

直接复用 app_demo.create_app()，以便 `python -m agent_alert.app` 或
`python agent_alert/app.py` 都能单独起一个独立端口的 Demo。
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent_alert.app_demo import create_app


def main():
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7863, show_error=True)


if __name__ == "__main__":
    main()
