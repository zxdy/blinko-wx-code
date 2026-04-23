"""
消息处理器
处理企业微信应用的被动回调消息
"""

from wecom_app_svr import RspTextMsg, RspImageMsg, RspVideoMsg
from config.constants import MSG_TYPE_TEXT, MSG_TYPE_IMAGE, MSG_TYPE_VIDEO, MSG_IMAGE_SAVED, MSG_NOTE_UPDATED
from core.note_handler import NoteHandler
from utils.note_template import NoteSource
from utils.logger import get_logger


class MessageHandler:
    """消息处理器，处理企业微信应用消息"""

    def __init__(self):
        self.note_handler = NoteHandler()
        self.logger = get_logger(__name__)

    def handle(self, req_msg):
        """
        处理接收到的消息

        Args:
            req_msg: 请求消息对象

        Returns:
            响应消息对象
        """
        handlers = {
            MSG_TYPE_TEXT: self._handle_text,
            MSG_TYPE_IMAGE: self._handle_image,
            MSG_TYPE_VIDEO: self._handle_video
        }

        handler = handlers.get(req_msg.msg_type, self._handle_default)
        return handler(req_msg)

    def handle_text_content(self, content: str) -> bool:
        """
        直接处理文本内容（用于 HTTP API 接口）

        Args:
            content: 文本内容

        Returns:
            True 表示保存成功，False 表示失败
        """
        self.logger.info(f"通过 HTTP API 保存文本: {content[:50]}...")
        return self.note_handler.save_text(content, NoteSource.HTTP_API)

    def _handle_text(self, req_msg):
        """
        处理文本消息

        检查用户是否有待更新笔记：
        - 有：更新笔记内容（添加描述）
        - 无：独立保存文字笔记
        """
        self.logger.info(f"收到文本消息: {req_msg.content}")
        user_id = req_msg.from_user

        # 检查是否有待更新笔记
        success, message = self.note_handler.update_pending_note(user_id, req_msg.content)

        self.logger.info(f"文本处理结果: {message}")

        # 返回响应
        ret = RspTextMsg()
        ret.content = message
        return ret

    def _handle_image(self, req_msg):
        """
        处理图片消息

        保存图片笔记，支持：
        - 首张图片：创建新笔记
        - 后续图片：追加到已有笔记（2分钟窗口期内）
        """
        self.logger.info(f"收到图片消息，user_id: {req_msg.from_user}")
        user_id = req_msg.from_user
        image_url = req_msg.image_url

        # 保存图片笔记
        success, message = self.note_handler.save_image(image_url, user_id)

        self.logger.info(f"图片处理结果: {message}")

        # 返回响应
        ret = RspTextMsg()
        ret.content = message
        return ret

    def _handle_video(self, req_msg):
        """处理视频消息"""
        self.logger.info("收到视频消息")
        return RspVideoMsg(
            req_msg.to_user,
            req_msg.from_user,
            req_msg.media_id,
            "视频标题",
            "视频描述"
        )

    def _handle_default(self, req_msg):
        """处理默认/未知类型消息"""
        self.logger.warning(f"收到未知消息类型: {req_msg.msg_type}")
        ret = RspTextMsg()
        ret.content = f'msg_type: {req_msg.msg_type}'
        return ret