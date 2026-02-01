from wecom_app_svr import RspTextMsg, RspImageMsg, RspVideoMsg
from config.constants import MSG_TYPE_TEXT, MSG_TYPE_IMAGE, MSG_TYPE_VIDEO
from services.blinko_service import BlinkoService
from utils.tag_parser import TagParser
from utils.logger import get_logger


class MessageHandler:
    """消息处理器,处理企业微信应用消息"""
    
    def __init__(self):
        self.blinko = BlinkoService()
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
        直接处理文本内容(用于HTTP API接口)
        
        Args:
            content: 文本内容
            
        Returns:
            True表示保存成功,False表示失败
        """
        self.logger.info(f"通过HTTP API保存文本: {content[:50]}...")
        
        # 解析标签
        tagged_content = TagParser.parse(content)
        
        # 保存到Blinko
        return self.blinko.save_note(tagged_content)
    
    def _handle_text(self, req_msg):
        """
        处理文本消息
        
        Args:
            req_msg: 文本消息对象
            
        Returns:
            文本响应消息
        """
        self.logger.info(f"收到文本消息: {req_msg.content}")
        
        
        # 解析标签
        tagged_content = TagParser.parse(req_msg.content)
        
        # 保存到Blinko
        self.blinko.save_note(tagged_content)
        
        # 返回响应
        ret = RspTextMsg()
        ret.content = "笔记已保存"
        return ret
    
    def _handle_image(self, req_msg):
        """
        处理图片消息
        
        Args:
            req_msg: 图片消息对象
            
        Returns:
            图片响应消息
        """
        self.logger.info("收到图片消息")
        return RspImageMsg(req_msg.to_user, req_msg.from_user, req_msg.media_id)
    
    def _handle_video(self, req_msg):
        """
        处理视频消息
        
        Args:
            req_msg: 视频消息对象
            
        Returns:
            视频响应消息
        """
        self.logger.info("收到视频消息")
        return RspVideoMsg(
            req_msg.to_user,
            req_msg.from_user,
            req_msg.media_id,
            "视频标题",
            "视频描述"
        )
    
    def _handle_default(self, req_msg):
        """
        处理默认/未知类型消息
        
        Args:
            req_msg: 消息对象
            
        Returns:
            文本响应消息,显示消息类型
        """
        self.logger.warning(f"收到未知消息类型: {req_msg.msg_type}")
        ret = RspTextMsg()
        ret.content = f'msg_type: {req_msg.msg_type}'
        return ret
