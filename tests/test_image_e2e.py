"""
端到端真实服务测试
模拟完整的用户操作流程，使用真实的企业微信消息解析和 Blinko 服务
"""

import pytest
import uuid
import time
import os

from core.message_handler import MessageHandler
from core.note_handler import NoteHandler
from core.container import Container
from services.blinko_service import BlinkoService
from utils.cache import PendingNoteCache
from tests.test_config import test_settings


@pytest.fixture(scope="module")
def setup_container():
    """初始化容器"""
    test_settings.validate()
    Container.clear_cache()


@pytest.fixture
def message_handler(setup_container):
    """创建 MessageHandler"""
    return MessageHandler()


@pytest.fixture
def note_handler(setup_container):
    """创建 NoteHandler"""
    return NoteHandler()


@pytest.fixture
def blinko_service(setup_container):
    """创建 BlinkoService"""
    return BlinkoService()


@pytest.fixture
def pending_cache():
    """创建 PendingNoteCache"""
    return PendingNoteCache()


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestE2EFullFlow:
    """端到端完整流程测试"""

    def test_e2e_single_image_with_description(self, message_handler):
        """
        E2E: 单张图片 + 文字描述

        用户操作:
        1. 发送图片 → 创建图片笔记
        2. 发送文字 → 更新笔记内容

        验证:
        - 笔记创建成功
        - 缓存正确设置
        - 文字更新成功
        - 缓存清除
        """
        user_id = f"e2e_single_{uuid.uuid4().hex[:8]}"

        # === Step 1: 发送图片 ===
        class MockImageMsg:
            def __init__(self):
                self.msg_type = "image"
                self.from_user = user_id
                self.to_user = "app_001"
                self.image_url = test_settings.TEST_IMAGE_URL
                self.media_id = "media_001"

        image_msg = MockImageMsg()
        image_response = message_handler._handle_image(image_msg)

        # 验证图片响应
        assert "图片已保存" in image_response.content
        print(f"[Step 1] 图片响应: {image_response.content}")

        # === Step 2: 发送文字描述 ===
        class MockTextMsg:
            def __init__(self):
                self.msg_type = "text"
                self.from_user = user_id
                self.to_user = "app_001"
                self.content = f"E2E 测试描述 - {uuid.uuid4().hex[:8]}"

        text_msg = MockTextMsg()
        text_response = message_handler._handle_text(text_msg)

        # 验证文字响应
        assert "笔记已更新" in text_response.content
        print(f"[Step 2] 文字响应: {text_response.content}")

        # === 验证缓存清除 ===
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert cached is None
        print("[验证] 流程完成，缓存已清除")

    def test_e2e_multiple_images_with_description(self, message_handler):
        """
        E2E: 多张图片 + 文字描述

        用户操作:
        1. 发送图片1 → 创建笔记
        2. 发送图片2 → 追加
        3. 发送图片3 → 追加
        4. 发送文字 → 更新内容
        """
        user_id = f"e2e_multi_{uuid.uuid4().hex[:8]}"

        # === Step 1-3: 发送 3 张图片 ===
        for i in range(3):
            class MockImageMsg:
                def __init__(self, idx):
                    self.msg_type = "image"
                    self.from_user = user_id
                    self.to_user = "app_001"
                    self.image_url = f"https://picsum.photos/{200+idx*50}/{300+idx*50}"
                    self.media_id = f"media_{idx}"

            image_msg = MockImageMsg(i)
            response = message_handler._handle_image(image_msg)
            assert "图片已保存" in response.content
            print(f"[Step {i+1}] 图片{i+1} 已保存")

        # 验证缓存有 3 张图片
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert cached is not None
        assert len(cached[1]) == 3
        print(f"[验证] 缓存有 {len(cached[1])} 张图片")

        # === Step 4: 发送文字 ===
        class MockTextMsg:
            def __init__(self):
                self.msg_type = "text"
                self.from_user = user_id
                self.to_user = "app_001"
                self.content = f"E2E 多图描述 - 共 3 张图片"

        text_msg = MockTextMsg()
        text_response = message_handler._handle_text(text_msg)
        assert "笔记已更新" in text_response.content
        print(f"[Step 4] 文字已更新")

        # 验证流程完成
        cached_final = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert cached_final is None
        print("[验证] 多图流程完成")

    def test_e2e_text_only(self, message_handler):
        """
        E2E: 仅文字笔记

        用户直接发送文字，无前置图片
        """
        user_id = f"e2e_text_{uuid.uuid4().hex[:8]}"

        class MockTextMsg:
            def __init__(self):
                self.msg_type = "text"
                self.from_user = user_id
                self.to_user = "app_001"
                self.content = f"E2E 纯文字笔记 - {uuid.uuid4().hex[:8]}"

        text_msg = MockTextMsg()
        response = message_handler._handle_text(text_msg)

        assert "笔记已保存" in response.content
        print(f"[响应] {response.content}")

    def test_e2e_image_only_no_followup(self, message_handler):
        """
        E2E: 仅图片，无后续文字

        用户发送图片后不发送文字，笔记只包含图片
        """
        user_id = f"e2e_img_only_{uuid.uuid4().hex[:8]}"

        class MockImageMsg:
            def __init__(self):
                self.msg_type = "image"
                self.from_user = user_id
                self.to_user = "app_001"
                self.image_url = test_settings.TEST_IMAGE_URL
                self.media_id = "media_001"

        image_msg = MockImageMsg()
        response = message_handler._handle_image(image_msg)

        assert "图片已保存" in response.content

        # 验证缓存存在（等待文字）
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert cached is not None
        print(f"[状态] 图片笔记已创建，等待文字（2分钟窗口）")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestE2EEdgeCases:
    """边界场景测试"""

    def test_e2e_cache_expiry_real_time(self):
        """
        E2E: 缓存过期

        发送图片后等待过期，再发送文字应独立保存
        """
        # 使用短过期缓存
        short_cache = PendingNoteCache(expire_seconds=1)
        note_handler = NoteHandler()
        note_handler.pending_cache = short_cache

        msg_handler = MessageHandler()
        msg_handler.note_handler = note_handler

        user_id = f"e2e_expiry_{uuid.uuid4().hex[:8]}"

        # 发送图片
        class MockImageMsg:
            def __init__(self):
                self.msg_type = "image"
                self.from_user = user_id
                self.image_url = test_settings.TEST_IMAGE_URL

        image_msg = MockImageMsg()
        image_response = msg_handler._handle_image(image_msg)
        assert "图片已保存" in image_response.content
        print(f"[Step 1] 图片已保存")

        # 等待过期
        time.sleep(1.5)
        print(f"[等待] 1.5 秒已过")

        # 发送文字（应该独立保存）
        class MockTextMsg:
            def __init__(self):
                self.msg_type = "text"
                self.from_user = user_id
                self.content = "过期后的文字"

        text_msg = MockTextMsg()
        text_response = msg_handler._handle_text(text_msg)

        # 验证独立保存（不是更新）
        assert "笔记已保存" in text_response.content
        print(f"[Step 2] 文字独立保存（缓存已过期）")

    def test_e2e_invalid_image_url(self, message_handler):
        """
        E2E: 无效图片 URL

        发送无效图片 URL，应优雅失败
        """
        user_id = f"e2e_invalid_{uuid.uuid4().hex[:8]}"

        class MockImageMsg:
            def __init__(self):
                self.msg_type = "image"
                self.from_user = user_id
                self.image_url = "https://invalid-domain-12345.com/notexist.jpg"

        image_msg = MockImageMsg()
        response = message_handler._handle_image(image_msg)

        # 验证失败响应
        assert "失败" in response.content
        print(f"[响应] {response.content}")

        # 验证无缓存
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert cached is None
        print("[验证] 无缓存设置")

    def test_e2e_service_recovery(self, blinko_service):
        """
        E2E: 服务恢复

        测试服务在失败后的恢复能力
        """
        # 先测试一个失败的请求
        invalid_url = "https://httpbin.org/status/404"
        result_fail = blinko_service.upload_image(invalid_url)
        assert result_fail is None
        print("[失败测试] 404 图片返回 None")

        # 再测试一个成功的请求，验证服务恢复
        success_url = test_settings.TEST_IMAGE_URL
        result_success = blinko_service.upload_image(success_url)
        assert result_success is not None
        print("[恢复测试] 成功请求正常工作")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestE2EConcurrency:
    """并发场景测试"""

    def test_e2e_concurrent_users(self, message_handler):
        """
        E2E: 并发用户

        多个用户同时发送消息，互不干扰
        """
        import concurrent.futures

        def user_workflow(user_suffix):
            user_id = f"concurrent_e2e_{user_suffix}"

            # 发送图片
            class MockImageMsg:
                def __init__(self, uid):
                    self.msg_type = "image"
                    self.from_user = uid
                    self.image_url = test_settings.TEST_IMAGE_URL

            image_msg = MockImageMsg(user_id)
            image_response = message_handler._handle_image(image_msg)

            if "图片已保存" not in image_response.content:
                return False, user_id, "image_failed"

            # 发送文字
            class MockTextMsg:
                def __init__(self, uid):
                    self.msg_type = "text"
                    self.from_user = uid
                    self.content = f"描述_{user_suffix}"

            text_msg = MockTextMsg(user_id)
            text_response = message_handler._handle_text(text_msg)

            if "笔记已更新" not in text_response.content:
                return False, user_id, "text_failed"

            return True, user_id, "success"

        users = [uuid.uuid4().hex[:8] for _ in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(user_workflow, users))

        # 验证所有用户成功
        failures = [(r[1], r[2]) for r in results if not r[0]]
        assert len(failures) == 0, f"失败的用户: {failures}"

        success_count = sum(1 for r in results if r[0])
        print(f"[结果] {success_count} 个并发用户全部成功")

    def test_e2e_rapid_messages(self, message_handler):
        """
        E2E: 快速连续消息

        单个用户快速发送多条消息
        """
        user_id = f"rapid_{uuid.uuid4().hex[:8]}"

        # 快速发送 5 张图片
        for i in range(5):
            class MockImageMsg:
                def __init__(self, idx):
                    self.msg_type = "image"
                    self.from_user = user_id
                    self.image_url = f"https://picsum.photos/{200+idx*20}/{300+idx*20}"

            image_msg = MockImageMsg(i)
            response = message_handler._handle_image(image_msg)
            assert "图片已保存" in response.content

        # 验证缓存有 5 张图片
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert len(cached[1]) == 5
        print(f"[快速发送] 5 张图片已缓存")

        # 发送文字完成
        class MockTextMsg:
            def __init__(self):
                self.msg_type = "text"
                self.from_user = user_id
                self.content = "快速发送的描述"

        text_msg = MockTextMsg()
        response = message_handler._handle_text(text_msg)
        assert "笔记已更新" in response.content
        print(f"[完成] 快速流程成功")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestE2EServiceStatus:
    """服务状态验证"""

    def test_e2e_blinko_service_available(self, blinko_service):
        """
        E2E: 验证 Blinko 服务可用
        """
        # 发送简单的笔记验证服务
        test_content = f"[E2E 状态检查] {uuid.uuid4().hex[:8]}"
        success = blinko_service.save_note(test_content)

        assert success is True
        print("[状态] Blinko 服务可用")

    def test_e2e_image_upload_available(self, blinko_service):
        """
        E2E: 验证图片上传可用
        """
        result = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)

        assert result is not None
        assert "path" in result
        print(f"[状态] 图片上传可用: {result['name']}")

    def test_e2e_note_upsert_available(self, blinko_service):
        """
        E2E: 验证笔记创建/更新可用
        """
        # 创建笔记
        attachment = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment is not None

        note_id, success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment],
            note_id=None
        )

        assert success is True
        assert note_id is not None
        print(f"[状态] 笔记创建可用: ID {note_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])