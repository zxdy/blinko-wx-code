"""
测试配置管理
使用真实服务进行测试，需要配置真实的 API 端点和 Token
"""

import os
from dotenv import load_dotenv

# 加载测试环境变量
load_dotenv('.env.test')


class TestSettings:
    """测试环境配置"""

    # Blinko 真实服务配置
    BLINKO_API_URL: str = os.getenv("BLINKO_API_URL", "")
    BLINKO_API_TOKEN: str = os.getenv("BLINKO_API_TOKEN", "")

    # 企业微信真实配置（可选，用于完整 E2E 测试）
    WECOM_CORP_ID: str = os.getenv("WECOM_CORP_ID", "")
    WECOM_CORP_SECRET: str = os.getenv("WECOM_CORP_SECRET", "")

    # 测试用户 ID
    TEST_USER_ID: str = os.getenv("TEST_USER_ID", "test_user_001")

    # 测试图片 URL（真实可访问的图片）
    TEST_IMAGE_URL: str = os.getenv(
        "TEST_IMAGE_URL",
        "https://picsum.photos/200/300"  # 随机图片服务
    )

    # 是否跳过需要真实服务的测试
    SKIP_REAL_SERVICE_TESTS: bool = os.getenv("SKIP_REAL_SERVICE_TESTS", "false").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """验证必需的测试配置"""
        if cls.SKIP_REAL_SERVICE_TESTS:
            return True

        if not cls.BLINKO_API_URL or not cls.BLINKO_API_TOKEN:
            raise ValueError(
                "缺少必需的测试配置，请设置环境变量:\n"
                "BLINKO_API_URL - Blinko API 地址\n"
                "BLINKO_API_TOKEN - Blinko API Token\n"
                "或设置 SKIP_REAL_SERVICE_TESTS=true 跳过真实服务测试"
            )

        return True


test_settings = TestSettings()