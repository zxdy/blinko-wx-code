"""
笔记处理统一入口
统一处理来自不同渠道的消息，避免代码重复
"""

from typing import Optional, Dict, Any, List, Tuple
from core.container import container
from services.wecom_api import WeComAPI
from services.blinko_service import BlinkoService
from utils.cache import MessageIdCache, PendingNoteCache
from utils.tag_parser import TagParser
from utils.note_template import NoteSource, TEMPLATES
from utils.logger import get_logger
from config.constants import MSG_TYPE_TEXT, MSG_TYPE_LINK, MSG_TYPE_IMAGE, TEMPLATE_DETAILED


class NoteHandler:
    """笔记保存统一入口"""

    def __init__(self, template_name: str = TEMPLATE_DETAILED):
        self.blinko: BlinkoService = container.get_blinko_service()
        self.cache: MessageIdCache = container.get_message_cache()
        self.pending_cache: PendingNoteCache = container.get_pending_note_cache()
        self.wecom_api: WeComAPI = container.get_wecom_api()

        # 使用预设模板
        self.template = TEMPLATES.get(template_name, TEMPLATES[TEMPLATE_DETAILED])

        self.logger = get_logger(__name__)

    def save_image(self, image_url: str, user_id: str) -> Tuple[bool, str]:
        """
        保存图片笔记，支持追加到已有笔记

        Args:
            image_url: 图片 URL (PicUrl)
            user_id: 用户 ID（用于缓存关联）

        Returns:
            (success, message) - 是否成功和响应消息
        """
        self.logger.info(f"处理图片笔记，user_id: {user_id}, image_url: {image_url[:50]}...")

        # 1. 上传图片到 Blinko
        attachment = self.blinko.upload_image(image_url)
        if not attachment:
            self.logger.error("图片上传失败")
            return False, "图片上传失败"

        # 2. 检查用户是否有待更新笔记
        pending = self.pending_cache.get_pending(user_id)

        if pending:
            note_id, existing_attachments = pending
            # 追加图片到已有笔记
            new_attachments = existing_attachments + [attachment]

            self.logger.info(f"追加图片到笔记 ID: {note_id}, 现有图片数: {len(existing_attachments)}")

            updated_id, success = self.blinko.upsert_note(
                content=None,
                attachments=new_attachments,
                note_id=note_id
            )

            if success:
                # 更新缓存
                self.pending_cache.set_pending(user_id, updated_id, new_attachments)
                return True, "图片已保存，2分钟内发送文字可添加描述"
            else:
                return False, "图片追加失败"
        else:
            # 创建新笔记
            self.logger.info("创建新图片笔记")

            note_id, success = self.blinko.upsert_note(
                content=None,
                attachments=[attachment],
                note_id=None
            )

            if success:
                # 缓存待更新笔记
                self.pending_cache.set_pending(user_id, note_id, [attachment])
                return True, "图片已保存，2分钟内发送文字可添加描述"
            else:
                return False, "图片笔记创建失败"

    def update_pending_note(self, user_id: str, content: str) -> Tuple[bool, str]:
        """
        更新待更新笔记的内容（添加文字描述）

        Args:
            user_id: 用户 ID
            content: 文字描述内容

        Returns:
            (success, message) - 是否成功和响应消息
        """
        pending = self.pending_cache.get_pending(user_id)

        if not pending:
            # 无待更新笔记，独立保存文字
            self.logger.info(f"无待更新笔记，独立保存文字: {content[:50]}...")
            success = self.save_text(content, NoteSource.WECHAT_APP)
            return success, "笔记已保存" if success else "笔记保存失败"

        note_id, attachments = pending

        self.logger.info(f"更新笔记 ID: {note_id}, 添加描述: {content[:50]}...")

        # 解析标签
        tags, processed_content = self._parse_tags_and_content(content)

        # 使用模板格式化内容
        formatted_content = self.template.format_text(
            content=processed_content,
            source=NoteSource.WECHAT_APP,
            tags=tags
        )

        # 更换笔记内容
        updated_id, success = self.blinko.upsert_note(
            content=formatted_content,
            attachments=attachments,
            note_id=note_id
        )

        if success:
            # 清除缓存（笔记已完成）
            self.pending_cache.clear_pending(user_id)
            return True, "笔记已更新"
        else:
            return False, "笔记更新失败"

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

        # 解析标签并获取处理后的内容
        tags, processed_content = self._parse_tags_and_content(content)
        self.logger.info(f"解析结果: tags={tags}, processed_content长度={len(processed_content)}")

        # 使用模板格式化
        formatted_content = self.template.format_text(
            content=processed_content,
            source=source,
            tags=tags
        )
        self.logger.info(f"格式化后内容长度: {len(formatted_content)}, 前50字符: {formatted_content[:50]}")

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

        # 解析标签（基于标题、描述和URL）
        full_text = f"{title} {desc or ''} {url}"
        tags, _ = self._parse_tags_and_content(full_text)

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

        elif msgtype == MSG_TYPE_IMAGE:
            image_data = msg.get('image', {})
            self.logger.info(f"图片消息原始数据: {image_data}")

            # 尝试获取 pic_url 或 media_id
            pic_url = image_data.get('pic_url')
            media_id = image_data.get('media_id')
            user_id = msg.get('external_userid', 'unknown')

            if pic_url:
                success, message = self.save_image(pic_url, user_id)
                self.logger.info(f"图片保存结果: {message}")
                return success
            elif media_id:
                # 通过 media_id 下载图片
                self.logger.info(f"图片使用 media_id: {media_id}")
                image_url = self.wecom_api.get_media_url(media_id)
                if image_url:
                    success, message = self.save_image(image_url, user_id)
                    self.logger.info(f"图片保存结果: {message}")
                    return success
                else:
                    self.logger.warning("无法获取 media_id 对应的图片 URL")
                    return False
            else:
                self.logger.warning("图片消息缺少 pic_url 或 media_id")
                return False

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

    def _parse_tags_and_content(self, content: str) -> tuple:
        """
        解析内容中的标签，返回标签和处理后的内容

        Args:
            content: 原始内容

        Returns:
            (标签字符串或 None, 处理后的内容)
        """
        parsed = TagParser.parse(content)

        # 如果内容和解析后内容不同，说明添加了标签
        if parsed != content:
            lines = parsed.split('\n')
            # 第一行是标签
            if lines[0].startswith('#'):
                tag = lines[0]
                # 剩余部分是内容（去掉标签行和后面的空行）
                processed_content = '\n'.join(lines[2:]) if len(lines) > 2 else content
                return tag, processed_content

        return None, content