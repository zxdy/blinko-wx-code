# Design: Support Image Notes

## Context

当前 `MessageHandler._handle_image()` 仅返回原图片响应。需要扩展为完整的图片笔记处理流程，支持创建、追加图片，以及文字描述关联。

关键约束：
- 使用 PicUrl 下载图片（不调用企业微信素材 API）
- 2分钟窗口期内可追加图片或添加描述
- 使用 Blinko upsert API（id=null 创建，有值更新）

## Goals / Non-Goals

**Goals:**
- 图片消息能保存为 Blinko 笔记
- 用户能在 2 分钟内追加图片或添加文字描述
- 多张图片合并到同一笔记

**Non-Goals:**
- 视频、语音消息处理
- 企业微信客服（KF）图片处理
- 图片自动描述（OCR/AI）

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MessageHandler                                │
├─────────────────────────────────────────────────────────────────┤
│  _handle_image(req_msg)                                         │
│    ↓                                                            │
│  NoteHandler.save_image(image_url, user_id)                     │
│    ↓                                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  1. PendingNoteCache.get_pending(user_id)                   ││
│  │     - 检查是否过期（120秒）                                   ││
│  │  2. BlinkoService.upload_image(image_url)                   ││
│  │     - 下载图片、上传到 Blinko                                ││
│  │  3. 根据缓存状态:                                            ││
│  │     - 有缓存 → upsert_note(追加 attachment)                 ││
│  │     - 无缓存 → upsert_note(创建新笔记)                       ││
│  │  4. PendingNoteCache.set_pending(user_id, note_id)          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  _handle_text(req_msg)                                          │
│    ↓                                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  1. PendingNoteCache.get_pending(user_id)                   ││
│  │     - 检查是否过期                                           ││
│  │  2. 根据缓存状态:                                            ││
│  │     - 有缓存 → upsert_note(更新 content) + 清除缓存         ││
│  │     - 无缓存 → save_text(独立保存)                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    PendingNoteCache (新增)                       │
├─────────────────────────────────────────────────────────────────┤
│  结构: {user_id: {note_id, created_at, attachments}}            │
│  方法:                                                          │
│    - get_pending(user_id) → (note_id, attachments) | None       │
│    - set_pending(user_id, note_id, attachments)                 │
│    - clear_pending(user_id)                                     │
│    - is_expired(created_at) → bool                              │
│  过期时间: 120秒                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    BlinkoService (扩展)                          │
├─────────────────────────────────────────────────────────────────┤
│  新增方法:                                                       │
│    - upload_image(image_url) → attachment                       │
│      - 下载图片、POST /api/file/upload                          │
│    - upsert_note(content, attachments, note_id) → (note_id, ok) │
│      - POST /api/v1/note/upsert                                 │
│      - id=null 创建，id有值更新                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Decisions

### Decision 1: Use PicUrl Instead of MediaId

**Choice:** 从 PicUrl 直接下载图片
**Rationale:** PicUrl 是可直接访问的图片 URL，无需额外调用企业微信 API 获取临时素材，实现更简单
**Alternatives Considered:**
- MediaId + 企业微信素材 API: 更可靠但需要额外 token 管理，复杂度更高

### Decision 2: Lazy Expiry (惰性过期检查)

**Choice:** 不使用后台定时器，在消息到达时检查过期
**Rationale:** 实现简单，无需定时器管理，服务重启不影响缓存状态（内存缓存本身会丢失）
**Alternatives Considered:**
- 真实时定时器: 精确超时但定时器管理复杂，服务重启丢失状态

### Decision 3: Upsert API for Both Create and Update

**Choice:** 统一使用 Blinko upsert API
**Rationale:** API 设计支持 id=null 创建、id 有值更新，逻辑统一
**Alternatives Considered:**
- 分离 create 和 update API: 当前 Blinko 已提供统一的 upsert

### Decision 4: Memory Cache for Pending Notes

**Choice:** 使用内存缓存（类似现有 MessageIdCache）
**Rationale:** 简单高效，与现有架构一致，服务重启丢失不影响（图片已保存）
**Alternatives Considered:**
- Redis/数据库缓存: 过度设计，窗口期短、数据量小

## Data Model Changes

无数据库变更。新增内存缓存结构：

```python
# PendingNoteCache 内部结构
{
    "user_id_1": {
        "note_id": 123,
        "created_at": 1713859200.0,  # timestamp
        "attachments": [
            {"name": "img1.png", "path": "/api/file/xxx.png", "size": 1000, "type": "image/png"}
        ]
    }
}
```

## API Changes

### BlinkoService 新增方法

```python
def upload_image(self, image_url: str) -> Optional[Dict]:
    """
    从 URL 下载图片并上传到 Blinko

    Returns:
        attachment 对象 {"name", "path", "size", "type"} 或 None
    """

def upsert_note(
    self,
    content: Optional[str] = None,
    attachments: List[Dict] = [],
    note_id: Optional[int] = None
) -> Tuple[Optional[int], bool]:
    """
    创建或更新笔记

    Args:
        content: 笔记内容（文字描述）
        attachments: 图片附件列表
        note_id: None=创建，有值=更新

    Returns:
        (note_id, success)
    """
```

## Risks & Trade-offs

- [PicUrl 可能失效] → 失败时记录日志，返回错误响应
- [内存缓存服务重启丢失] → 不影响，图片笔记已保存
- [大图片上传慢] → 同步处理，用户等待响应（可后续优化为异步）

## Open Questions

无。