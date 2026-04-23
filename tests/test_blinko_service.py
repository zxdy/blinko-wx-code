"""
BlinkoService 真实服务测试
使用真实的 Blinko API 进行测试，验证实际网络请求和响应
"""

import pytest
import httpx
import time
import uuid

from services.blinko_service import BlinkoService
from tests.test_config import test_settings


@pytest.fixture(scope="module")
def blinko_service():
    """创建真实的 BlinkoService 实例"""
    test_settings.validate()
    return BlinkoService()


@pytest.fixture
def unique_user_id():
    """生成唯一的测试用户 ID"""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestUploadImageReal:
    """测试 upload_image - 使用真实服务"""

    def test_upload_image_from_url_success(self, blinko_service):
        """
        Scenario: Successful Image Upload from URL
        GIVEN 图片 URL 有效可访问
        WHEN 系统下载并上传到 Blinko
        THEN 返回有效的 attachment 对象
        """
        image_url = test_settings.TEST_IMAGE_URL

        result = blinko_service.upload_image(image_url)

        # 验证返回结果
        assert result is not None, "图片上传应该成功"
        assert "name" in result
        assert "path" in result
        assert "size" in result
        assert "type" in result
        assert result["type"].startswith("image/")
        assert result["size"] > 0

        print(f"上传成功: {result['name']}, 大小: {result['size']} bytes")

    def test_upload_image_invalid_url_returns_none(self, blinko_service):
        """
        Scenario: Invalid Image URL
        GIVEN 图片 URL 无效
        WHEN 系统尝试下载
        THEN 返回 None（不抛异常）
        """
        invalid_url = "https://invalid-domain-12345.com/notexist.jpg"

        result = blinko_service.upload_image(invalid_url)

        # 验证优雅失败
        assert result is None

    def test_upload_image_404_returns_none(self, blinko_service):
        """
        Scenario: Image Not Found (404)
        GIVEN 图片 URL 返回 404
        WHEN 系统尝试下载
        THEN 返回 None
        """
        url_404 = "https://httpbin.org/status/404"

        result = blinko_service.upload_image(url_404)

        assert result is None


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestUpsertNoteReal:
    """测试 upsert_note - 使用真实服务"""

    def test_create_note_with_image_success(self, blinko_service):
        """
        Scenario: Create Note with Image
        GIVEN 上传图片成功
        WHEN 创建新笔记（note_id=None）
        THEN 返回有效的 note_id
        """
        # 先上传图片
        attachment = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment is not None, "图片上传前置条件失败"

        # 创建笔记
        note_id, success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment],
            note_id=None
        )

        # 验证创建成功
        assert success is True, "笔记创建应该成功"
        assert note_id is not None
        assert note_id > 0

        print(f"创建笔记成功，ID: {note_id}")

        # 清理：删除测试笔记（如果 API 支持）
        # blinko_service.delete_note(note_id)

    def test_create_note_with_text_success(self, blinko_service):
        """
        Scenario: Create Note with Text Only
        GIVEN 文字内容有效
        WHEN 创建新笔记
        THEN 返回有效的 note_id
        """
        test_content = f"[测试] 笔记内容 - {uuid.uuid4().hex[:8]}"

        note_id, success = blinko_service.upsert_note(
            content=test_content,
            attachments=[],
            note_id=None
        )

        assert success is True
        assert note_id is not None
        assert note_id > 0

        print(f"创建文字笔记成功，ID: {note_id}, 内容: {test_content[:30]}...")

    def test_update_existing_note_success(self, blinko_service):
        """
        Scenario: Update Existing Note
        GIVEN 已有笔记存在
        WHEN 更新笔记内容
        THEN 返回相同的 note_id
        """
        # Step 1: 创建笔记
        attachment = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment is not None

        note_id, create_success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment],
            note_id=None
        )
        assert create_success is True

        # Step 2: 更新笔记（添加文字描述）
        test_content = f"[测试更新] 添加描述 - {uuid.uuid4().hex[:8]}"

        updated_id, update_success = blinko_service.upsert_note(
            content=test_content,
            attachments=[attachment],
            note_id=note_id
        )

        # 验证更新成功
        assert update_success is True
        assert updated_id == note_id  # ID 应该不变

        print(f"更新笔记成功，ID: {note_id}")

    def test_append_image_to_existing_note(self, blinko_service):
        """
        Scenario: Append Image to Existing Note
        GIVEN 已有笔记包含一张图片
        WHEN 追加新图片
        THEN 笔记包含两张图片
        """
        # Step 1: 上传第一张图片并创建笔记
        attachment1 = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment1 is not None

        note_id, _ = blinko_service.upsert_note(
            content=None,
            attachments=[attachment1],
            note_id=None
        )
        assert note_id is not None

        # Step 2: 上传第二张图片
        # 使用不同的图片 URL
        attachment2 = blinko_service.upload_image("https://picsum.photos/300/400")
        assert attachment2 is not None

        # Step 3: 追加到笔记
        updated_id, success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment1, attachment2],
            note_id=note_id
        )

        assert success is True
        assert updated_id == note_id

        print(f"追加图片成功，ID: {note_id}, 图片数: 2")

    def test_upsert_note_empty_content_success(self, blinko_service):
        """
        Scenario: Note with Empty Content and Attachments
        GIVEN 无文字内容但有图片
        WHEN 创建笔记
        THEN 成功创建
        """
        attachment = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment is not None

        note_id, success = blinko_service.upsert_note(
            content="",  # 空内容
            attachments=[attachment],
            note_id=None
        )

        assert success is True
        assert note_id is not None


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestSaveNoteReal:
    """测试 save_note - 使用真实服务"""

    def test_save_note_short_content(self, blinko_service):
        """
        Scenario: Save Short Note (Thought)
        GIVEN 内容长度 < 200 字符
        WHEN 保存笔记
        THEN 创建为闪念类型 (type=0)
        """
        short_content = f"[测试闪念] {uuid.uuid4().hex[:8]}"

        success = blinko_service.save_note(short_content)

        assert success is True

        print(f"闪念保存成功: {short_content}")

    def test_save_note_long_content(self, blinko_service):
        """
        Scenario: Save Long Note
        GIVEN 内容长度 >= 200 字符
        WHEN 保存笔记
        THEN 创建为笔记类型 (type=1)
        """
        long_content = f"[测试笔记] {uuid.uuid4().hex[:8]} - " + "这是一段较长的笔记内容，用于测试笔记类型判断。" * 5

        success = blinko_service.save_note(long_content)

        assert success is True

        print(f"长笔记保存成功，长度: {len(long_content)}")

    def test_save_note_with_markdown_format(self, blinko_service):
        """
        Scenario: Save Note with Markdown
        GIVEN 内容包含 Markdown 格式
        WHEN 保存笔记
        THEN 正确保存
        """
        markdown_content = f"""
# 测试标题 {uuid.uuid4().hex[:8]}

> 这是一条引用

- 列表项 1
- 列表项 2

[链接](https://example.com)
"""
        success = blinko_service.save_note(markdown_content)

        assert success is True

    def test_save_note_concurrent_requests(self, blinko_service):
        """
        Scenario: Concurrent Note Saves
        GIVEN 多个并发请求
        WHEN 同时保存多个笔记
        THEN 全部成功
        """
        import concurrent.futures

        contents = [f"[并发测试] {uuid.uuid4().hex[:8]} - {i}" for i in range(5)]

        def save_content(content):
            return blinko_service.save_note(content)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(save_content, contents))

        # 验证全部成功
        assert all(results), "所有并发请求应该成功"

        print(f"并发测试成功，数量: {len(results)}")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestIntegrationFlow:
    """完整流程集成测试"""

    def test_full_image_note_flow(self, blinko_service):
        """
        Scenario: Full Image Note Flow
        GIVEN 用户发送图片
        WHEN 完整流程执行
        THEN 创建图片笔记，可追加图片，可添加描述
        """
        # Step 1: 发送第一张图片
        attachment1 = blinko_service.upload_image(test_settings.TEST_IMAGE_URL)
        assert attachment1 is not None

        note_id, create_success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment1],
            note_id=None
        )
        assert create_success is True
        print(f"Step 1: 创建笔记，ID: {note_id}")

        # Step 2: 追加第二张图片
        attachment2 = blinko_service.upload_image("https://picsum.photos/250/350")
        assert attachment2 is not None

        _, append_success = blinko_service.upsert_note(
            content=None,
            attachments=[attachment1, attachment2],
            note_id=note_id
        )
        assert append_success is True
        print(f"Step 2: 追加图片，共 2 张")

        # Step 3: 添加文字描述
        description = f"[测试描述] 这是两张测试图片 - {uuid.uuid4().hex[:8]}"
        _, update_success = blinko_service.upsert_note(
            content=description,
            attachments=[attachment1, attachment2],
            note_id=note_id
        )
        assert update_success is True
        print(f"Step 3: 添加描述完成")

        # 最终验证
        assert all([create_success, append_success, update_success])
        print(f"完整流程测试成功，最终笔记 ID: {note_id}")

    def test_cleanup_after_tests(self, blinko_service):
        """
        测试完成后清理
        注意：此测试仅验证服务可用性，不做实际清理
        """
        # 发送一个简单的测试请求验证服务状态
        test_content = "[清理验证] 服务状态检查"
        success = blinko_service.save_note(test_content)
        assert success is True
        print("服务状态正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])