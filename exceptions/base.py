"""统一异常定义"""

class BlinkoBaseException(Exception):
    """基础异常类"""

    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or "UNKNOWN_ERROR"
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}"