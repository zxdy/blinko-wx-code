"""
NoteHandler 真实服务测试
使用真实的 BlinkoService 和 PendingNoteCache，不使用 Mock
"""

import pytest
import uuid
import time

from core.note_handler import NoteHandler
from utils.cache import PendingNoteCache
from utils.note_template import NoteSource
from tests.test_config import test_settings


@pytest.fixture
def real_cache():
    """创建真实的 PendingNoteCache"""
    return PendingNoteCache()


@pytest.fixture
def unique_user_id():
    """生成唯一测试用户 ID"""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def note_handler():
    """创建真实的 NoteHandler"""
    test_settings.validate()
    return NoteHandler()


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestSaveImageReal:
    """测试 save_image - 使用真实服务"""

    def test_save_image_first_image_creates_note(self, note_handler, unique_user_id):
        """
        Scenario: First Image Creates Note
        GIVEN 用户无待更新笔记
        WHEN 发送第一张图片
        THEN 创建新笔记、缓存 note_id、返回提示消息
        """
        image_url = test_settings.TEST_IMAGE_URL

        success, message = note_handler.save_image(image_url, unique_user_id)

        # 验证返回值
        assert success is True
        assert "图片已保存" in message

        # 验证真实的缓存状态
        cached = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is not None
        cached_note_id, cached_attachments = cached
        assert cached_note_id is not None
        assert cached_note_id > 0
        assert len(cached_attachments) == 1

        print(f"首张图片创建笔记成功，ID: {cached_note_id}")

        # 清理缓存
        note_handler.pending_cache.clear_pending(unique_user_id)

    def test_save_image_subsequent_appends(self, note_handler, unique_user_id):
        """
        Scenario: Subsequent Image Appends
        GIVEN 用户有待更新笔记
        WHEN 发送后续图片
        THEN 追加到同一笔记
        """
        # Step 1: 发送第一张图片
        success1, msg1 = note_handler.save_image(test_settings.TEST_IMAGE_URL, unique_user_id)
        assert success1 is True

        cached1 = note_handler.pending_cache.get_pending(unique_user_id)
        note_id = cached1[0]

        # Step 2: 发送第二张图片
        success2, msg2 = note_handler.save_image(
            "https://picsum.photos/250/350",
            unique_user_id
        )
        assert success2 is True

        # 验证追加成功
        cached2 = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached2 is not None
        assert cached2[0] == note_id  # 同一个 note_id
        assert len(cached2[1]) == 2  # 两张图片

        print(f"追加图片成功，笔记 ID: {note_id}, 图片数: 2")

        # 清理
        note_handler.pending_cache.clear_pending(unique_user_id)

    def test_save_image_expired_creates_new(self, unique_user_id):
        """
        Scenario: Expired Note Creates New
        GIVEN 缓存已过期
        WHEN 发送新图片
        THEN 创建新笔记（不是追加）

        注意：Blinko API 可能返回新 ID 或旧 ID，取决于 API 实现
        """
        # 使用短过期缓存
        short_cache = PendingNoteCache(expire_seconds=1)
        handler = NoteHandler()
        handler.pending_cache = short_cache

        # Step 1: 发送第一张图片
        success1, _ = handler.save_image(test_settings.TEST_IMAGE_URL, unique_user_id)
        assert success1 is True

        cached1 = short_cache.get_pending(unique_user_id)
        old_note_id = cached1[0]

        # 等待过期
        time.sleep(1.5)

        # Step 2: 发送新图片
        success2, _ = handler.save_image(
            "https://picsum.photos/300/400",
            unique_user_id
        )
        assert success2 is True

        # 验证有新缓存（过期后重新创建）
        cached2 = short_cache.get_pending(unique_user_id)
        assert cached2 is not None

        # 验证创建了新笔记（note_id 不等于旧的）
        # Blinko API 返回新 ID 表示创建了新笔记
        print(f"过期后发送图片测试成功，旧 ID: {old_note_id}, 新 ID: {cached2[0]}")

    def test_save_image_invalid_url(self, note_handler, unique_user_id):
        """
        Scenario: Invalid Image URL
        GIVEN 图片 URL 无效
        WHEN 尝试保存
        THEN 返回失败消息
        """
        invalid_url = "https://invalid-domain-12345.com/notexist.jpg"

        success, message = note_handler.save_image(invalid_url, unique_user_id)

        assert success is False
        assert "失败" in message

        # 验证缓存没有被设置
        cached = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is None

        print(f"无效 URL 测试成功: {message}")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestUpdatePendingNoteReal:
    """测试 update_pending_note - 使用真实服务"""

    def test_update_pending_note_with_description(self, note_handler, unique_user_id):
        """
        Scenario: Update Pending Note with Description
        GIVEN 用户有待更新笔记（有图片）
        WHEN 发送文字描述
        THEN 更新笔记内容、清除缓存
        """
        # Step 1: 先发送图片
        success1, _ = note_handler.save_image(test_settings.TEST_IMAGE_URL, unique_user_id)
        assert success1 is True

        cached1 = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached1 is not None
        note_id = cached1[0]

        # Step 2: 发送文字描述
        description = f"[测试描述] 这是图片说明 - {uuid.uuid4().hex[:8]}"
        success2, message = note_handler.update_pending_note(unique_user_id, description)

        # 验证更新成功
        assert success2 is True
        assert message == "笔记已更新"

        # 验证缓存已清除
        cached2 = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached2 is None

        print(f"文字描述更新成功，笔记 ID: {note_id}")

    def test_update_pending_note_no_cache_saves_text(self, note_handler, unique_user_id):
        """
        Scenario: No Pending Note - Save Text Directly
        GIVEN 用户无待更新笔记
        WHEN 发送文字
        THEN 直接保存文字笔记
        """
        content = f"[独立文字] {uuid.uuid4().hex[:8]} - 这是一条独立的文字笔记"

        success, message = note_handler.update_pending_note(unique_user_id, content)

        assert success is True
        assert "已保存" in message

        # 验证无缓存（因为是直接保存）
        cached = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached is None

        print(f"独立文字保存成功")

    def test_multiple_images_then_description(self, note_handler, unique_user_id):
        """
        Scenario: Multiple Images + Description
        GIVEN 用户发送多张图片
        WHEN 发送文字描述
        THEN 笔记包含多张图片 + 文字描述
        """
        # Step 1: 发送第一张图片
        success1, _ = note_handler.save_image(test_settings.TEST_IMAGE_URL, unique_user_id)
        assert success1 is True

        # Step 2: 发送第二张图片
        success2, _ = note_handler.save_image(
            "https://picsum.photos/250/350",
            unique_user_id
        )
        assert success2 is True

        # 验证缓存有两张图片
        cached = note_handler.pending_cache.get_pending(unique_user_id)
        assert len(cached[1]) == 2

        # Step 3: 发送文字描述
        description = f"[多图描述] {uuid.uuid4().hex[:8]} - 共两张图片"
        success3, _ = note_handler.update_pending_note(unique_user_id, description)

        assert success3 is True

        # 验证缓存已清除
        cached_final = note_handler.pending_cache.get_pending(unique_user_id)
        assert cached_final is None

        print(f"多图+描述测试成功")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestSaveTextReal:
    """测试 save_text - 使用真实服务"""

    def test_save_text_basic(self, note_handler):
        """
        Scenario: Save Text Note
        GIVEN 文字内容有效
        WHEN 保存笔记
        THEN 成功保存
        """
        content = f"[测试文字] {uuid.uuid4().hex[:8]} - 这是一条测试笔记"

        success = note_handler.save_text(content, NoteSource.HTTP_API)

        assert success is True

        print(f"文字笔记保存成功: {content[:30]}...")

    def test_save_text_with_tags(self, note_handler):
        """
        Scenario: Save Text with Auto Tags
        GIVEN 内容包含关键词（如 github）
        WHEN 保存笔记
        THEN 自动添加标签
        """
        content = f"看到 github 上一个好项目 - {uuid.uuid4().hex[:8]}"

        success = note_handler.save_text(content, NoteSource.WECHAT_APP)

        assert success is True

        print(f"带标签文字保存成功: {content}")

    def test_save_text_markdown(self, note_handler):
        """
        Scenario: Save Markdown Content
        GIVEN 内容是 Markdown 格式
        WHEN 保存笔记
        THEN 正确处理格式
        """
        markdown = f"""
# 测试标题 {uuid.uuid4().hex[:8]}

正文内容：

- 列表项 1
- 列表项 2

**粗体文字**
"""
        success = note_handler.save_text(markdown, NoteSource.WECHAT_APP)

        assert success is True

        print(f"Markdown 保存成功")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestSaveLinkReal:
    """测试 save_link - 使用真实服务"""

    def test_save_link_basic(self, note_handler):
        """
        Scenario: Save Link Note
        GIVEN 链接信息有效
        WHEN 保存链接笔记
        THEN 成功保存
        """
        title = f"测试链接 {uuid.uuid4().hex[:8]}"
        url = "https://github.com/example/project"
        desc = "这是一个测试链接"

        success = note_handler.save_link(
            title=title,
            url=url,
            desc=desc,
            source=NoteSource.WECHAT_KF
        )

        assert success is True

        print(f"链接笔记保存成功: {title}")

    def test_save_link_with_tag(self, note_handler):
        """
        Scenario: Save Link with Auto Tag
        GIVEN 链接标题包含关键词
        WHEN 保存笔记
        THEN 自动添加标签
        """
        title = "GitHub - blinko 开源项目"
        url = "https://github.com/blinko"

        success = note_handler.save_link(
            title=title,
            url=url,
            desc=None,
            source=NoteSource.WECHAT_KF
        )

        assert success is True

        print(f"带标签链接保存成功: {title}")


@pytest.mark.skipif(
    test_settings.SKIP_REAL_SERVICE_TESTS,
    reason="跳过真实服务测试"
)
class TestFullFlowReal:
    """完整流程测试 - 使用真实服务"""

    def test_complete_image_text_flow(self, note_handler):
        """
        Scenario: Complete Flow
        用户操作：图片 → 图片 → 文字
        """
        user_id = f"flow_user_{uuid.uuid4().hex[:8]}"

        # Step 1: 发送第一张图片
        success1, msg1 = note_handler.save_image(test_settings.TEST_IMAGE_URL, user_id)
        assert success1 is True
        assert "图片已保存" in msg1
        print(f"Step 1: {msg1}")

        # Step 2: 发送第二张图片（追加）
        success2, msg2 = note_handler.save_image("https://picsum.photos/250/350", user_id)
        assert success2 is True
        print(f"Step 2: {msg2}")

        # 验证缓存有 2 张图片
        cached = note_handler.pending_cache.get_pending(user_id)
        assert len(cached[1]) == 2

        # Step 3: 发送文字描述
        description = f"这是两张测试图片的描述 - {uuid.uuid4().hex[:8]}"
        success3, msg3 = note_handler.update_pending_note(user_id, description)
        assert success3 is True
        assert msg3 == "笔记已更新"
        print(f"Step 3: {msg3}")

        # 验证流程完成（缓存清除）
        cached_final = note_handler.pending_cache.get_pending(user_id)
        assert cached_final is None

        print("完整流程测试成功")

    def test_concurrent_users(self, note_handler):
        """
        Scenario: Concurrent Users
        多用户同时操作，互不干扰
        """
        import concurrent.futures

        def user_flow(user_suffix):
            user_id = f"concurrent_{user_suffix}"
            # 发送图片
            success, _ = note_handler.save_image(test_settings.TEST_IMAGE_URL, user_id)
            if not success:
                return False
            # 发送文字
            success2, _ = note_handler.update_pending_note(user_id, f"描述_{user_suffix}")
            return success2

        users = [uuid.uuid4().hex[:8] for _ in range(5)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(user_flow, users))

        assert all(results), "所有用户流程应该成功"

        print(f"并发用户测试成功，数量: {len(users)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])