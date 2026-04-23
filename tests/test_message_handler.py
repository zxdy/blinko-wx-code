"""
MessageHandler 真实服务测试
使用真实的 NoteHandler 和 BlinkoService，不使用 Mock
"""

import pytest
import uuid
import time

from core.message_handler import MessageHandler
from config.constants import MSG_IMAGE_SAVED, MSG_NOTE_UPDATED
from tests.test_config import test_settings


class MockImageReqMsg:
    """模拟企业微信图片请求消息（只模拟消息结构，不模拟服务）"""
    def __init__(self, from_user="test_user", image_url="https://picsum.photos/200/300"):
        self.msg_type = "image"
        self.from_user = from_user
        self.to_user = "app_001"
        self.image_url = image_url
        self.media_id = "media_id_001"


class MockTextReqMsg:
    """模拟企业微信文本请求消息"""
    def __init__(self, from_user="test_user", content="这是一条消息"):
        self.msg_type = "text"
        self.from_user = from_user
        self.to_user = "app_001"
        self.content = content


@pytest.fixture
def message_handler():
    """创建真实的 MessageHandler"""
    test_settings.validate()
    return MessageHandler()


@pytest.fixture
def unique_user_id():
    """生成唯一测试用户 ID"""
    return f"msg_user_{uuid.uuid4().hex[:8]}"


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestHandleImageReal:
    """测试 _handle_image - 使用真实服务"""

    def test_handle_image_first_image(self, message_handler, unique_user_id):
        """
        Scenario: First Image Creates Note
        GIVEN 用户无待更新笔记
        WHEN 发送第一张图片
        THEN 响应内容为"图片已保存，2分钟内发送文字可添加描述"
        """
        req_msg = MockImageReqMsg(from_user=unique_user_id, image_url=test_settings.TEST_IMAGE_URL)

        response = message_handler._handle_image(req_msg)

        # 验证响应内容
        assert response.content == MSG_IMAGE_SAVED

        # 验证真实的缓存状态
        cached = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is not None
        note_id, attachments = cached
        assert note_id > 0
        assert len(attachments) == 1

        print(f"图片处理成功，笔记 ID: {note_id}")

        # 清理
        message_handler.note_handler.pending_cache.clear_pending(unique_user_id)

    def test_handle_image_second_appends(self, message_handler, unique_user_id):
        """
        Scenario: Second Image Appends
        GIVEN 用户有待更新笔记
        WHEN 发送第二张图片
        THEN 追加到同一笔记
        """
        # Step 1: 发送第一张图片
        req_msg1 = MockImageReqMsg(from_user=unique_user_id, image_url=test_settings.TEST_IMAGE_URL)
        response1 = message_handler._handle_image(req_msg1)
        assert response1.content == MSG_IMAGE_SAVED

        cached1 = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        note_id = cached1[0]

        # Step 2: 发送第二张图片
        req_msg2 = MockImageReqMsg(from_user=unique_user_id, image_url="https://picsum.photos/250/350")
        response2 = message_handler._handle_image(req_msg2)
        assert response2.content == MSG_IMAGE_SAVED

        # 验证追加
        cached2 = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached2[0] == note_id
        assert len(cached2[1]) == 2

        print(f"追加图片成功，共 2 张")

        # 清理
        message_handler.note_handler.pending_cache.clear_pending(unique_user_id)

    def test_handle_image_invalid_url(self, message_handler, unique_user_id):
        """
        Scenario: Invalid Image URL
        GIVEN 图片 URL 无效
        WHEN 处理图片消息
        THEN 返回失败消息
        """
        req_msg = MockImageReqMsg(
            from_user=unique_user_id,
            image_url="https://invalid-domain-12345.com/notexist.jpg"
        )

        response = message_handler._handle_image(req_msg)

        # 验证失败响应
        assert "失败" in response.content

        # 验证无缓存
        cached = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is None

        print(f"无效 URL 处理: {response.content}")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestHandleTextReal:
    """测试 _handle_text - 使用真实服务"""

    def test_handle_text_with_pending_note(self, message_handler, unique_user_id):
        """
        Scenario: Text Updates Pending Note
        GIVEN 用户有待更新笔记（有图片）
        WHEN 发送文字消息
        THEN 更新笔记内容、响应"笔记已更新"
        """
        # Step 1: 先发送图片创建待更新笔记
        image_msg = MockImageReqMsg(from_user=unique_user_id, image_url=test_settings.TEST_IMAGE_URL)
        image_response = message_handler._handle_image(image_msg)
        assert image_response.content == MSG_IMAGE_SAVED

        # 验证缓存存在
        cached = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is not None

        # Step 2: 发送文字描述
        text_msg = MockTextReqMsg(from_user=unique_user_id, content=f"这是图片描述 - {uuid.uuid4().hex[:8]}")
        text_response = message_handler._handle_text(text_msg)

        # 验证响应
        assert text_response.content == MSG_NOTE_UPDATED

        # 验证缓存已清除
        cached_final = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached_final is None

        print("文字更新笔记成功")

    def test_handle_text_no_pending_note(self, message_handler, unique_user_id):
        """
        Scenario: Text Creates Separate Note
        GIVEN 用户无待更新笔记
        WHEN 发送文字消息
        THEN 独立保存文字笔记
        """
        text_msg = MockTextReqMsg(
            from_user=unique_user_id,
            content=f"独立文字笔记 - {uuid.uuid4().hex[:8]}"
        )

        response = message_handler._handle_text(text_msg)

        # 验证保存成功
        assert response.content == "笔记已保存"

        # 验证无缓存（因为是直接保存）
        cached = message_handler.note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is None

        print("独立文字保存成功")

    def test_handle_text_with_tag_keyword(self, message_handler, unique_user_id):
        """
        Scenario: Text with Auto Tag
        GIVEN 文字内容包含关键词
        WHEN 保存笔记
        THEN 自动添加标签
        """
        text_msg = MockTextReqMsg(
            from_user=unique_user_id,
            content=f"在 github 上发现一个好项目"
        )

        response = message_handler._handle_text(text_msg)

        assert response.content == "笔记已保存"

        print("带标签文字保存成功")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestFullFlowReal:
    """完整流程测试 - 使用真实服务"""

    def test_image_then_text_flow(self, message_handler):
        """
        Scenario: Full Flow - Image → Text
        完整的用户操作流程
        """
        user_id = f"full_flow_{uuid.uuid4().hex[:8]}"

        # Step 1: 发送图片
        image_msg = MockImageReqMsg(from_user=user_id, image_url=test_settings.TEST_IMAGE_URL)
        image_response = message_handler._handle_image(image_msg)
        assert image_response.content == MSG_IMAGE_SAVED
        print(f"Step 1: {image_response.content}")

        # Step 2: 发送文字描述
        text_msg = MockTextReqMsg(from_user=user_id, content="这是图片的完整描述")
        text_response = message_handler._handle_text(text_msg)
        assert text_response.content == MSG_NOTE_UPDATED
        print(f"Step 2: {text_response.content}")

        print("完整流程测试成功")

    def test_multiple_images_flow(self, message_handler):
        """
        Scenario: Multiple Images Flow
        连续发送多张图片
        """
        user_id = f"multi_img_{uuid.uuid4().hex[:8]}"

        # 发送 3 张图片
        for i in range(3):
            image_msg = MockImageReqMsg(
                from_user=user_id,
                image_url=f"https://picsum.photos/{200+i*10}/{300+i*10}"
            )
            response = message_handler._handle_image(image_msg)
            assert response.content == MSG_IMAGE_SAVED
            print(f"发送图片 {i+1}: {response.content}")

        # 验证缓存有 3 张图片
        cached = message_handler.note_handler.pending_cache.get_pending(user_id)
        assert len(cached[1]) == 3

        # 发送文字完成流程
        text_msg = MockTextReqMsg(from_user=user_id, content="三张图片的描述")
        text_response = message_handler._handle_text(text_msg)
        assert text_response.content == MSG_NOTE_UPDATED

        print("多图片流程测试成功")

    def test_timeout_expiry_flow(self, message_handler):
        """
        Scenario: Timeout Expiry
        缓存过期后发送文字，应该独立保存
        """
        # 使用短过期时间的缓存
        from utils.cache import PendingNoteCache
        from core.note_handler import NoteHandler

        short_cache = PendingNoteCache(expire_seconds=1)
        handler = NoteHandler()
        handler.pending_cache = short_cache

        msg_handler = MessageHandler()
        msg_handler.note_handler = handler

        user_id = f"timeout_{uuid.uuid4().hex[:8]}"

        # Step 1: 发送图片
        image_msg = MockImageReqMsg(from_user=user_id, image_url=test_settings.TEST_IMAGE_URL)
        image_response = msg_handler._handle_image(image_msg)
        assert image_response.content == MSG_IMAGE_SAVED

        # Step 2: 等待过期
        time.sleep(1.5)

        # Step 3: 发送文字（应该独立保存，不是更新）
        text_msg = MockTextReqMsg(from_user=user_id, content="过期后的文字")
        text_response = msg_handler._handle_text(text_msg)

        # 验证独立保存
        assert text_response.content == "笔记已保存"

        print("超时过期流程测试成功")

    def test_concurrent_message_handling(self, message_handler):
        """
        Scenario: Concurrent Handling
        多个用户同时发送消息
        """
        import concurrent.futures

        def handle_user_flow(user_suffix):
            user_id = f"concurrent_{user_suffix}"

            # 发送图片
            image_msg = MockImageReqMsg(from_user=user_id, image_url=test_settings.TEST_IMAGE_URL)
            image_response = message_handler._handle_image(image_msg)

            if image_response.content != MSG_IMAGE_SAVED:
                return False

            # 发送文字
            text_msg = MockTextReqMsg(from_user=user_id, content=f"描述_{user_suffix}")
            text_response = message_handler._handle_text(text_msg)

            return text_response.content == MSG_NOTE_UPDATED

        users = [uuid.uuid4().hex[:8] for _ in range(5)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(handle_user_flow, users))

        assert all(results), "所有用户流程应该成功"

        print(f"并发处理测试成功，用户数: {len(users)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])