# Tasks: Support Image Notes

## 1. BlinkoService 扩展
- [x] 1.1 实现 `upload_image(image_url)` 方法 - 从 PicUrl 下载图片并上传到 Blinko `/api/file/upload`
- [x] 1.2 实现 `upsert_note(content, attachments, note_id)` 方法 - 调用 Blinko `/api/v1/note/upsert`
- [x] 1.3 为 `upload_image` 编写单元测试（成功上传 + 下载失败场景）
- [x] 1.4 为 `upsert_note` 编写单元测试（创建笔记 + 更新笔记 + API 失败场景）

## 2. PendingNoteCache 新增
- [x] 2.1 在 `utils/cache.py` 新增 `PendingNoteCache` 类
- [x] 2.2 实现 `get_pending(user_id)` - 返回 `(note_id, attachments)` 或 `None`
- [x] 2.3 实现 `set_pending(user_id, note_id, attachments)` - 设置缓存记录
- [x] 2.4 实现 `clear_pending(user_id)` - 清除缓存记录
- [x] 2.5 实现 `is_expired(created_at)` - 检查是否超过 120秒
- [x] 2.6 为 `PendingNoteCache` 编写单元测试（设置 + 获取 + 过期检查 + 清除）

## 3. NoteHandler 扩展
- [x] 3.1 在 `core/note_handler.py` 新增 `save_image(image_url, user_id)` 方法
- [x] 3.2 实现图片上传 + 缓存检查 + 创建/更新笔记逻辑
- [x] 3.3 在 DI container 中注册 `PendingNoteCache`
- [x] 3.4 为 `save_image` 编写单元测试（首次创建 + 追加图片 + 过期重建）

## 4. MessageHandler 修改
- [x] 4.1 重写 `_handle_image(req_msg)` - 调用 `NoteHandler.save_image()`，返回提示消息
- [x] 4.2 修改 `_handle_text(req_msg)` - 检查缓存，更新笔记或独立保存
- [x] 4.3 在 `core/message_handler.py` 引入 `PendingNoteCache`
- [x] 4.4 为 `_handle_image` 编写集成测试（模拟完整消息处理流程）
- [x] 4.5 为 `_handle_text` 编写集成测试（有缓存 + 无缓存场景）

## 5. Constants 更新
- [x] 5.1 在 `config/constants.py` 新增 `PENDING_NOTE_EXPIRE_SECONDS = 120`

## 6. Verification
- [x] 6.1 运行完整测试套件 - 确保全部通过
- [x] 6.2 使用 `test_call_back.py` 模拟图片消息测试实际流程
- [x] 6.3 验证 spec scenario 覆盖率（合规矩阵）