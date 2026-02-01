from wecom_app_svr import RspTextMsg
from config.constants import MSG_TYPE_TEXT, MSG_TYPE_LINK
from services.wecom_api import WeComAPI
from services.blinko_service import BlinkoService
from utils.cache import MessageIdCache
from utils.tag_parser import TagParser
from utils.logger import get_logger


class EventHandler:
    """事件处理器,处理企业微信应用事件"""
    
    def __init__(self):
        self.wecom_api = WeComAPI()
        self.msgid_cache = MessageIdCache()
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
        
        # 获取最新的客服消息
        last_msg = self.wecom_api.get_latest_message(req_msg.open_kfid, req_msg.token)
        if not last_msg:
            self.logger.warning("未找到最新消息")
            return self._success_response()
        
        # 获取msgid用于幂等性检查
        msgid = last_msg.get('msgid')
        self.logger.info(f"收到消息, msgid: {msgid}, msgtype: {last_msg.get('msgtype')}")

        # 检查msgid是否已处理
        if self.msgid_cache.is_processed(msgid):
            self.logger.info(f"消息已处理,跳过保存. msgid: {msgid}")
            return self._already_saved_response()

        self.msgid_cache.mark_processed(msgid)
        self.logger.info(f"消息标记处理中. msgid: {msgid}")
        
        # 处理消息并保存
        if not self._process_message(last_msg):
            return self._success_response()
                
        return self._success_response()
    
    def _process_message(self, msg: dict) -> bool:
        """
        处理消息内容并保存到Blinko
        
        Args:
            msg: 消息字典
            
        Returns:
            True表示处理成功,False表示不支持的类型
        """
        msgtype = msg.get('msgtype')
        
        if msgtype == MSG_TYPE_TEXT:
            content = msg.get('text', {}).get('content', '')
            if content:
                tagged_content = TagParser.parse(content)
                # 保存到Blinko
                self.logger.info(f"处理文本消息, 长度: {len(content)}")
                BlinkoService().save_note(tagged_content)
                return True
        
        elif msgtype == MSG_TYPE_LINK:
            link_data = msg.get('link', {})
            content = self._format_link_message(link_data)
            tagged_content = TagParser.parse(content)
            self.logger.info(f"处理链接消息, 标题: {link_data.get('title', 'unknown')}")
            BlinkoService().save_note(tagged_content)
            return True
        
        else:
            self.logger.warning(f"不支持的消息类型: {msgtype}")
            return False
    
    def _format_link_message(self, link_data: dict) -> str:
        """
        格式化链接消息为Markdown
        
        Args:
            link_data: 链接数据字典
            
        Returns:
            格式化后的Markdown字符串
        """
        title = link_data.get('title', '')
        desc = link_data.get('desc', '')
        url = link_data.get('url', '')
        
        # 构造Markdown格式
        parts = []
        if title:
            parts.append(f"### {title}")
        if desc:
            parts.append(f"> {desc}")
        if url:
            parts.append(url)
        
        return '\n\n'.join(parts)
    
    def _success_response(self):
        """返回成功响应"""
        ret = RspTextMsg()
        ret.content = "note saved"
        return ret
    
    def _already_saved_response(self):
        """返回已保存响应"""
        ret = RspTextMsg()
        ret.content = "note already saved"
        return ret
