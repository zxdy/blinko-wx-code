"""Blinko 服务异常"""

from exceptions.base import BlinkoBaseException


class BlinkoAPIError(BlinkoBaseException):
    """Blinko API 调用错误"""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message, code="BLINKO_API_ERROR")


class BlinkoSaveError(BlinkoAPIError):
    """笔记保存失败"""

    def __init__(self, message: str = "笔记保存失败"):
        super().__init__(message, status_code=500)


class BlinkoNetworkError(BlinkoAPIError):
    """网络请求失败"""

    def __init__(self, message: str):
        super().__init__(message, status_code=None)