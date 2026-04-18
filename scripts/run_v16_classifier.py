"""Wrapper: 带环境变量运行 v16_classifier.py"""
import os, sys
# DeepSeek 是国内服务,不走海外代理
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "api.deepseek.com,dashscope.aliyuncs.com,open.bigmodel.cn"
os.environ["DEEPSEEK_API_KEY"] = "sk-358b17cef8a64462b7899dd2dc8a3834"
os.environ.setdefault("CLASSIFIER_PROVIDER", "deepseek")
os.chdir(r"D:\claude code\credit_report_agent_work")
sys.path.insert(0, ".")
import runpy
runpy.run_path("v16_classifier.py", run_name="__main__")
