"""
事件处理器
处理企业微信客服事件
"""

from wecom_app_svr import RspTextMsg
from core.note_handler import NoteHandler
from utils.logger import get_logger


class EventHandler:
    """事件处理器，处理企业微信客服事件"""

    def __init__(self):
        self.note_handler = NoteHandler()
        self.logger = get_logger(__name__)

    def handle(self, req_msg):
        """
        处理接收到的事件

        Args:
            req_msg: 事件消息对象

        Returns:
            响应消息对象
        """
        self.logger.info(f"收到事件: {req_msg.event}")

        # 使用统一的处理流程：拉取消息 + 保存笔记
        msgid = self.note_handler.fetch_and_save(req_msg.open_kfid, req_msg.token)

        if msgid:
            return self._success_response()
        else:
            return self._no_message_response()

    def _success_response(self):
        """返回成功响应"""
        ret = RspTextMsg()
        ret.content = "note saved"
        return ret

    def _no_message_response(self):
        """返回无消息响应"""
        ret = RspTextMsg()
        ret.content = "no new message"
        return ret