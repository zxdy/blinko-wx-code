from typing import Dict, List


class TagParser:
    """标签解析器,根据关键词自动添加标签"""
    
    # 标签规则: 关键词 -> 标签
    TAG_RULES: Dict[str, str] = {
        "xiaohongshu": "#小红书",
        "小红书": "#小红书",
        "zhihu": "#知乎",
        "douyin": "#抖音",
        "抖音": "#抖音",
        "github": "#github",
        "doubao": "#豆包",
    }

    # URL 规则: 特定平台链接自动添加待解析标签
    URL_RULES: Dict[str, str] = {
        "mp.weixin.qq.com": "#待解析文章",  # 微信公众号
        "xiaohongshu.com": "#待解析文章",   # 小红书
        "zhihu.com": "#待解析文章",         # 知乎
    }
    
    @classmethod
    def parse(cls, message: str) -> str:
        """
        解析消息并添加标签

        Args:
            message: 原始消息内容

        Returns:
            添加标签后的消息
        """
        tags = []

        # 检查关键词规则
        for keyword, tag in cls.TAG_RULES.items():
            if keyword in message:
                tags.append(tag)

        # 检查 URL 规则
        for url_prefix, tag in cls.URL_RULES.items():
            if url_prefix in message:
                tags.append(tag)

        # 去重并合并标签
        unique_tags = list(dict.fromkeys(tags))  # 保持顺序去重
        if unique_tags:
            tags_str = " ".join(unique_tags)
            return f"{tags_str}\n\n{message}"

        return message
    
    @classmethod
    def add_rule(cls, keyword: str, tag: str, is_url: bool = False):
        """
        添加标签规则

        Args:
            keyword: 关键词
            tag: 标签
            is_url: 是否为 URL 规则
        """
        if is_url:
            cls.URL_RULES[keyword] = tag
        else:
            cls.TAG_RULES[keyword] = tag
