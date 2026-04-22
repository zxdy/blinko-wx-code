import os
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Settings:
    """项目配置管理类"""
    
    # 企业微信配置
    WECOM_CORP_ID: str = os.getenv("WECOM_CORP_ID", "")
    WECOM_CORP_SECRET: str = os.getenv("WECOM_CORP_SECRET", "")
    WECOM_TOKEN: str = os.getenv("WECOM_TOKEN", "")
    WECOM_AES_KEY: str = os.getenv("WECOM_AES_KEY", "")
    
    # Blinko配置
    BLINKO_API_URL: str = os.getenv("BLINKO_API_URL", "")
    BLINKO_API_TOKEN: str = os.getenv("BLINKO_API_TOKEN", "")
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5001"))
    
    # 回调通知URL(可选)
    CALLBACK_URL: str = os.getenv("CALLBACK_URL", "")
    
    # 缓存过期时间(秒)
    CACHE_EXPIRE_SECONDS: int = int(os.getenv("CACHE_EXPIRE_SECONDS", "600"))
    
    @classmethod
    def validate(cls) -> bool:
        """验证必需的配置项"""
        required = [
            ("WECOM_CORP_ID", cls.WECOM_CORP_ID),
            ("WECOM_CORP_SECRET", cls.WECOM_CORP_SECRET),
            ("WECOM_TOKEN", cls.WECOM_TOKEN),
            ("WECOM_AES_KEY", cls.WECOM_AES_KEY),
            ("BLINKO_API_URL", cls.BLINKO_API_URL),
            ("BLINKO_API_TOKEN", cls.BLINKO_API_TOKEN),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing)}")
        
        return True


settings = Settings()
