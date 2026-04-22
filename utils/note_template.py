"""
笔记内容模板
用于格式化保存到 Blinko 的 Markdown 内容
"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class NoteSource(Enum):
    """笔记来源"""
    WECHAT_APP = "wechat_app"      # 企业微信应用
    WECHAT_KF = "wechat_kf"        # 企业微信客服
    HTTP_API = "http_api"          # HTTP API
    UNKNOWN = "unknown"


class NoteTemplate:
    """笔记内容模板"""

    # 默认模板配置
    DEFAULT_CONFIG = {
        "include_source": False,        # 是否包含来源
        "include_time": False,          # 是否包含时间
        "include_type": False,          # 是否包含类型标签
        "link_style": "card",           # 链接样式: card/simple/full
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self.DEFAULT_CONFIG.copy()

    def format_text(
        self,
        content: str,
        source: NoteSource = NoteSource.UNKNOWN,
        tags: Optional[str] = None
    ) -> str:
        """
        格式化文本笔记

        Args:
            content: 文本内容
            source: 来源
            tags: 标签（可选）

        Returns:
            格式化后的 Markdown
        """
        parts = []

        # 标签
        if tags:
            parts.append(tags)

        # 元信息
        if self.config["include_source"] or self.config["include_time"]:
            meta_parts = []
            if self.config["include_time"]:
                meta_parts.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            if self.config["include_source"] and source != NoteSource.UNKNOWN:
                source_map = {
                    NoteSource.WECHAT_APP: "微信",
                    NoteSource.WECHAT_KF: "微信客服",
                    NoteSource.HTTP_API: "API",
                }
                meta_parts.append(f"保存来源: {source_map.get(source, '未知')}")
            if meta_parts:
                parts.append("> " + " | ".join(meta_parts))

        # 主内容
        parts.append(content)

        return "\n\n".join(parts)

    def format_link(
        self,
        title: str,
        url: str,
        desc: Optional[str] = None,
        source: NoteSource = NoteSource.UNKNOWN,
        tags: Optional[str] = None
    ) -> str:
        """
        格式化链接笔记

        Args:
            title: 链接标题
            url: 链接 URL
            desc: 链接描述（可选）
            source: 来源
            tags: 标签（可选）

        Returns:
            格式化后的 Markdown
        """
        style = self.config.get("link_style", "card")

        if style == "simple":
            # 简单样式：标题 + URL
            return self._format_link_simple(title, url, desc, tags)

        elif style == "card":
            # 卡片样式：标题 + 描述 + URL
            return self._format_link_card(title, url, desc, source, tags)

        elif style == "full":
            # 完整样式：带元信息的卡片
            return self._format_link_full(title, url, desc, source, tags)

        return self._format_link_card(title, url, desc, source, tags)

    def _format_link_simple(
        self,
        title: str,
        url: str,
        desc: Optional[str],
        tags: Optional[str]
    ) -> str:
        """简单链接样式"""
        parts = []

        if tags:
            parts.append(tags)

        parts.append(f"**{title}**")
        parts.append(url)

        if desc:
            parts.append(desc)

        return "\n\n".join(parts)

    def _format_link_card(
        self,
        title: str,
        url: str,
        desc: Optional[str],
        source: NoteSource,
        tags: Optional[str]
    ) -> str:
        """卡片链接样式"""
        parts = []

        if tags:
            parts.append(tags)

        # 标题作为链接
        parts.append(f"### [{title}]({url})")

        if desc:
            parts.append(f"> {desc}")

        return "\n\n".join(parts)

    def _format_link_full(
        self,
        title: str,
        url: str,
        desc: Optional[str],
        source: NoteSource,
        tags: Optional[str]
    ) -> str:
        """完整链接样式"""
        parts = []

        if tags:
            parts.append(tags)

        # 元信息
        meta_parts = []
        if self.config["include_time"]:
            meta_parts.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if self.config["include_source"] and source != NoteSource.UNKNOWN:
            source_map = {
                NoteSource.WECHAT_APP: "企业微信",
                NoteSource.WECHAT_KF: "企业微信客服",
                NoteSource.HTTP_API: "API",
            }
            meta_parts.append(f"📌 {source_map.get(source, '未知')}")
        if meta_parts:
            parts.append("> " + " | ".join(meta_parts))

        # 标题
        parts.append(f"### [{title}]({url})")

        # 描述
        if desc:
            parts.append(f"\n{desc}")

        # 原链接（可选显示）
        if self.config["include_type"]:
            parts.append(f"\n链接: {url}")

        return "\n\n".join(parts)

    def update_config(self, key: str, value: Any):
        """更新配置"""
        self.config[key] = value


# 默认模板实例
default_template = NoteTemplate()


# 预设模板
TEMPLATES = {
    "minimal": NoteTemplate({
        "include_source": False,
        "include_time": False,
        "include_type": False,
        "link_style": "simple",
    }),
    "standard": NoteTemplate({
        "include_source": False,
        "include_time": False,
        "include_type": False,
        "link_style": "card",
    }),
    "detailed": NoteTemplate({
        "include_source": True,
        "include_time": True,
        "include_type": True,
        "link_style": "full",
    }),
}