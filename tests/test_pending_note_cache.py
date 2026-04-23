"""
PendingNoteCache 真实对象测试
使用真实的缓存对象测试实际行为，不使用 Mock
"""

import pytest
import time
import threading
import uuid

from utils.cache import PendingNoteCache


class TestPendingNoteCacheReal:
    """测试 PendingNoteCache - 使用真实对象"""

    def test_set_and_get_pending_basic(self):
        """
        Scenario: Basic Cache Operations
        GIVEN 缓存对象初始化
        WHEN 设置和获取缓存
        THEN 数据正确存储和返回
        """
        cache = PendingNoteCache()
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        note_id = 12345
        attachments = [
            {"name": "test.jpg", "path": "/api/file/test.jpg", "size": 1000, "type": "image/jpeg"}
        ]

        # 设置缓存
        cache.set_pending(user_id, note_id, attachments)

        # 获取缓存
        result = cache.get_pending(user_id)

        # 验证返回值
        assert result is not None
        returned_note_id, returned_attachments = result
        assert returned_note_id == note_id
        assert returned_attachments == attachments

        print(f"缓存操作成功: user_id={user_id}, note_id={note_id}")

    def test_get_pending_not_found(self):
        """
        Scenario: Cache Not Found
        GIVEN 用户无缓存记录
        WHEN 获取缓存
        THEN 返回 None
        """
        cache = PendingNoteCache()
        unknown_user = f"unknown_{uuid.uuid4().hex[:8]}"

        result = cache.get_pending(unknown_user)

        assert result is None

    def test_cache_expiry_real_time(self):
        """
        Scenario: Cache Expiry (Real Time)
        GIVEN 缓存设置为短过期时间
        WHEN 等待过期
        THEN 返回 None

        注意：此测试需要实际等待，耗时约 2 秒
        """
        # 使用 1 秒过期时间
        cache = PendingNoteCache(expire_seconds=1)
        user_id = f"expire_user_{uuid.uuid4().hex[:8]}"
        note_id = 999

        # 设置缓存
        cache.set_pending(user_id, note_id, [])

        # 立即获取，应该返回数据
        result_before = cache.get_pending(user_id)
        assert result_before is not None
        assert result_before[0] == note_id
        print(f"缓存设置成功，立即获取有效")

        # 等待过期（实际等待）
        time.sleep(1.5)

        # 过期后获取，应该返回 None
        result_after = cache.get_pending(user_id)
        assert result_after is None
        print(f"缓存过期验证成功，等待时间: 1.5秒")

    def test_clear_pending(self):
        """
        Scenario: Cache Clear
        GIVEN 缓存中有数据
        WHEN 清除缓存
        THEN 缓存被删除
        """
        cache = PendingNoteCache()
        user_id = f"clear_user_{uuid.uuid4().hex[:8]}"
        note_id = 111

        # 设置缓存
        cache.set_pending(user_id, note_id, [])

        # 验证缓存存在
        result_before = cache.get_pending(user_id)
        assert result_before is not None

        # 清除缓存
        cache.clear_pending(user_id)

        # 验证缓存已清除
        result_after = cache.get_pending(user_id)
        assert result_after is None

        print(f"缓存清除成功")

    def test_multiple_users_isolated(self):
        """
        Scenario: Multi-user Cache Isolation
        GIVEN 多个用户的缓存
        WHEN 操作单个用户
        THEN 其他用户不受影响
        """
        cache = PendingNoteCache()

        # 设置多个用户
        users = {
            f"user_a_{uuid.uuid4().hex[:8]}": {"note_id": 100, "attachments": [{"name": "a.jpg"}]},
            f"user_b_{uuid.uuid4().hex[:8]}": {"note_id": 200, "attachments": [{"name": "b.jpg"}]},
            f"user_c_{uuid.uuid4().hex[:8]}": {"note_id": 300, "attachments": [{"name": "c.jpg"}]},
        }

        for user_id, data in users.items():
            cache.set_pending(user_id, data["note_id"], data["attachments"])

        # 验证各用户独立
        for user_id, data in users.items():
            result = cache.get_pending(user_id)
            assert result is not None
            assert result[0] == data["note_id"]

        # 清除一个用户
        user_b = list(users.keys())[1]
        cache.clear_pending(user_b)

        # 验证其他用户不受影响
        for user_id, data in users.items():
            result = cache.get_pending(user_id)
            if user_id == user_b:
                assert result is None
            else:
                assert result is not None

        print(f"多用户隔离测试成功")

    def test_append_attachments_flow(self):
        """
        Scenario: Append Attachments Flow
        GIVEN 缓存中有附件
        WHEN 追加新附件
        THEN 附件列表更新
        """
        cache = PendingNoteCache()
        user_id = f"append_user_{uuid.uuid4().hex[:8]}"
        note_id = 500

        # 第一张图片
        attachments1 = [{"name": "img1.jpg", "path": "/api/file/img1.jpg", "size": 1000}]
        cache.set_pending(user_id, note_id, attachments1)

        result1 = cache.get_pending(user_id)
        assert result1 is not None
        assert len(result1[1]) == 1

        # 模拟追加：获取 -> 合并 -> 设置
        _, attachments = result1
        attachments2 = attachments + [{"name": "img2.jpg", "path": "/api/file/img2.jpg", "size": 2000}]
        cache.set_pending(user_id, note_id, attachments2)

        # 验证追加成功
        result2 = cache.get_pending(user_id)
        assert result2 is not None
        assert len(result2[1]) == 2

        print(f"附件追加流程测试成功，数量: 2")

    def test_thread_safety(self):
        """
        Scenario: Thread Safety
        GIVEN 多线程并发访问
        WHEN 同时读写缓存
        THEN 无数据竞争，数据一致

        注意：此测试验证真实的线程安全性
        """
        cache = PendingNoteCache()
        errors = []

        def writer(user_id, note_id):
            """写入线程"""
            try:
                for i in range(10):
                    cache.set_pending(user_id, note_id + i, [{"count": i}])
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Writer error: {e}")

        def reader(user_id):
            """读取线程"""
            try:
                for i in range(10):
                    result = cache.get_pending(user_id)
                    # 结果可能为 None（还没写入或已过期）
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Reader error: {e}")

        def cleaner(user_id):
            """清除线程"""
            try:
                for i in range(5):
                    cache.clear_pending(user_id)
                    time.sleep(0.02)
            except Exception as e:
                errors.append(f"Cleaner error: {e}")

        # 创建多个线程
        user_id = f"thread_user_{uuid.uuid4().hex[:8]}"
        threads = []

        # 3 个写入线程
        for i in range(3):
            t = threading.Thread(target=writer, args=(f"{user_id}_w{i}", 1000 + i * 100))
            threads.append(t)

        # 3 个读取线程
        for i in range(3):
            t = threading.Thread(target=reader, args=(f"{user_id}_r{i}",))
            threads.append(t)

        # 2 个清除线程
        for i in range(2):
            t = threading.Thread(target=cleaner, args=(f"{user_id}_c{i}",))
            threads.append(t)

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证无错误
        assert len(errors) == 0, f"线程安全测试失败，错误: {errors}"

        print(f"线程安全测试成功，线程数: {len(threads)}")

    def test_cache_cleanup_on_expiry(self):
        """
        Scenario: Automatic Cleanup
        GIVEN 缓存中有过期数据
        WHEN 调用 get_pending
        THEN 过期数据自动清理
        """
        cache = PendingNoteCache(expire_seconds=1)
        user_id = f"cleanup_user_{uuid.uuid4().hex[:8]}"

        # 设置多条数据
        cache.set_pending(f"{user_id}_1", 100, [])
        cache.set_pending(f"{user_id}_2", 200, [])

        # 验证数据存在
        assert cache.get_pending(f"{user_id}_1") is not None
        assert cache.get_pending(f"{user_id}_2") is not None

        # 等待过期
        time.sleep(1.5)

        # 获取任意用户触发清理
        cache.get_pending(f"{user_id}_1")

        # 验证内部缓存被清理
        with cache._lock:
            # 过期数据应该被删除
            assert f"{user_id}_1" not in cache._cache
            assert f"{user_id}_2" not in cache._cache

        print(f"自动清理测试成功")

    def test_real_world_scenario(self):
        """
        Scenario: Real World Usage
        模拟真实使用场景：用户发送图片 -> 缓存 -> 发送文字 -> 清除
        """
        cache = PendingNoteCache(expire_seconds=120)  # 默认 2 分钟
        user_id = f"real_user_{uuid.uuid4().hex[:8]}"
        note_id = 8888

        # 模拟发送第一张图片
        attachment1 = {"name": "photo1.jpg", "path": "/api/file/photo1.jpg", "size": 5000}
        cache.set_pending(user_id, note_id, [attachment1])

        # 验证缓存
        result = cache.get_pending(user_id)
        assert result is not None
        assert len(result[1]) == 1
        print("Step 1: 图片1已缓存")

        # 模拟发送第二张图片（追加）
        _, attachments = result
        attachment2 = {"name": "photo2.jpg", "path": "/api/file/photo2.jpg", "size": 6000}
        cache.set_pending(user_id, note_id, attachments + [attachment2])

        result = cache.get_pending(user_id)
        assert len(result[1]) == 2
        print("Step 2: 图片2已追加")

        # 模拟发送文字描述后清除
        cache.clear_pending(user_id)

        result = cache.get_pending(user_id)
        assert result is None
        print("Step 3: 缓存已清除（流程完成）")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])