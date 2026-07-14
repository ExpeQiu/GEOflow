EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


class UsageError(Exception):
    """参数 / 契约错误。"""


class StoreError(Exception):
    """本地存储错误。"""
