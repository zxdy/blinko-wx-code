"""企业微信服务异常"""

from exceptions.base import BlinkoBaseException


class WeComAPIError(BlinkoBaseException):
    """企业微信 API 错误"""

    def __init__(self, message: str, errcode: int = None):
        self.errcode = errcode
        super().__init__(message, code="WECOM_API_ERROR")


class WeComTokenError(WeComAPIError):
    """Token 获取失败"""

    def __init__(self, message: str, errcode: int = None):
        super().__init__(message, errcode=errcode)
        self.code = "WECOM_TOKEN_ERROR"


class WeComMessageError(WeComAPIError):
    """消息获取失败"""

    def __init__(self, message: str, errcode: int = None):
        super().__init__(message, errcode=errcode)
        self.code = "WECOM_MSG_ERROR"