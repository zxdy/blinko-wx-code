"""
笔记处理统一入口
统一处理来自不同渠道的消息，避免代码重复
"""

from typing import Optional, Dict, Any
from core.container import container
from services.wecom_api import WeComAPI
from services.blinko_service import BlinkoService
from utils.cache import MessageIdCache
from utils.tag_parser import TagParser
from utils.note_template import NoteSource, TEMPLATES
from utils.logger import get_logger
from config.constants import MSG_TYPE_TEXT, MSG_TYPE_LINK, TEMPLATE_STANDARD


class NoteHandler:
    """笔记保存统一入口"""

    def __init__(self, template_name: str = TEMPLATE_STANDARD):
        self.blinko: BlinkoService = container.get_blinko_service()
        self.cache: MessageIdCache = container.get_message_cache()
        self.wecom_api: WeComAPI = container.get_wecom_api()

        # 使用预设模板
        self.template = TEMPLATES.get(template_name, TEMPLATES[TEMPLATE_STANDARD])

        self.logger = get_logger(__name__)

    def save_text(
        self,
        content: str,
        source: NoteSource = NoteSource.UNKNOWN
    ) -> bool:
        """
        直接保存文本内容

        Args:
            content: 文本内容
            source: 笔记来源

        Returns:
            True 表示成功，False 表示失败
        """
        self.logger.info(f"保存文本笔记，长度: {len(content)}")

        # 解析标签
        tags = self._parse_tags(content)

        # 使用模板格式化
        formatted_content = self.template.format_text(
            content=content,
            source=source,
            tags=tags
        )

        # 保存到 Blinko
        success = self.blinko.save_note(formatted_content)

        if not success:
            self.logger.error(f"笔记保存失败: {content[:50]}...")
        else:
            self.logger.info("笔记保存成功")

        return success

    def save_link(
        self,
        title: str,
        url: str,
        desc: Optional[str] = None,
        source: NoteSource = NoteSource.UNKNOWN
    ) -> bool:
        """
        保存链接笔记

        Args:
            title: 链接标题
            url: 链接 URL
            desc: 链接描述
            source: 笔记来源

        Returns:
            True 表示成功，False 表示失败
        """
        self.logger.info(f"保存链接笔记: {title}")

        # 解析标签（基于标题和描述）
        full_text = f"{title} {desc or ''}"
        tags = self._parse_tags(full_text)

        # 使用模板格式化
        formatted_content = self.template.format_link(
            title=title,
            url=url,
            desc=desc,
            source=source,
            tags=tags
        )

        # 保存到 Blinko
        return self.blinko.save_note(formatted_content)

    def save_from_kf_message(self, msg: Dict[str, Any]) -> bool:
        """
        从客服消息保存笔记（带幂等检查）

        Args:
            msg: 客服消息字典

        Returns:
            True 表示成功，False 表示失败或已处理
        """
        msgid = msg.get('msgid')

        # 幂等检查
        if self.cache.is_processed(msgid):
            self.logger.info(f"消息已处理，跳过保存. msgid: {msgid}")
            return False

        # 标记处理中
        self.cache.mark_processed(msgid)

        # 提取并保存
        msgtype = msg.get('msgtype')

        if msgtype == MSG_TYPE_TEXT:
            content = msg.get('text', {}).get('content', '')
            return self.save_text(content, NoteSource.WECHAT_KF)

        elif msgtype == MSG_TYPE_LINK:
            link_data = msg.get('link', {})
            return self.save_link(
                title=link_data.get('title', ''),
                url=link_data.get('url', ''),
                desc=link_data.get('desc', ''),
                source=NoteSource.WECHAT_KF
            )

        else:
            self.logger.warning(f"不支持的消息类型: {msgtype}")
            return False

    def fetch_and_save(self, open_kfid: str, token: str) -> Optional[str]:
        """
        拉取客服消息并保存（完整流程）

        Args:
            open_kfid: 客服账号ID
            token: 同步 Token

        Returns:
            成功返回 msgid，失败或已处理返回 None
        """
        # 拉取最新消息
        msg = self.wecom_api.get_latest_message(open_kfid, token)

        if not msg:
            self.logger.warning("未找到最新消息")
            return None

        msgid = msg.get('msgid')
        self.logger.info(f"拉取消息，msgid: {msgid}, msgtype: {msg.get('msgtype')}")

        # 幂等检查 + 保存
        if self.save_from_kf_message(msg):
            return msgid

        return None

    def _parse_tags(self, content: str) -> Optional[str]:
        """
        解析内容中的标签

        Args:
            content: 内容

        Returns:
            标签字符串或 None
        """
        parsed = TagParser.parse(content)

        # 如果内容和解析后内容不同，说明添加了标签
        if parsed != content:
            # 提取第一行的标签
            first_line = parsed.split('\n')[0]
            if first_line.startswith('#'):
                return first_line

        return None