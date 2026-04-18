"""Wrapper: 带环境变量运行 v16_classifier_consistency.py"""
import os, sys
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "api.deepseek.com,dashscope.aliyuncs.com,open.bigmodel.cn"
os.environ["DEEPSEEK_API_KEY"] = "sk-358b17cef8a64462b7899dd2dc8a3834"
os.environ.setdefault("CLASSIFIER_PROVIDER", "deepseek")
os.chdir(r"D:\claude code\credit_report_agent_work")
sys.path.insert(0, ".")
import runpy
runpy.run_path("v16_classifier_consistency.py", run_name="__main__")
