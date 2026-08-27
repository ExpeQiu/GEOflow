"""pytest 默认放宽本地安全启动约束。"""

import os

os.environ.setdefault("ALLOW_INSECURE_JWT", "true")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("CONTENT_AGENT_CALLBACK_SECRET", "test-callback-secret")
os.environ.setdefault("AI_MOCK_MODE", "true")
