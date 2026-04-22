from typing import Dict


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
    
    @classmethod
    def parse(cls, message: str) -> str:
        """
        解析消息并添加标签
        
        Args:
            message: 原始消息内容
            
        Returns:
            添加标签后的消息
        """
        for keyword, tag in cls.TAG_RULES.items():
            if keyword in message:
                return f"{tag}\n\n{message}"
        return message
    
    @classmethod
    def add_rule(cls, keyword: str, tag: str):
        """
        添加标签规则
        
        Args:
            keyword: 关键词
            tag: 标签
        """
        cls.TAG_RULES[keyword] = tag
