# Proposal: Support Image Notes

## Problem Statement

当前系统只支持文本消息保存为笔记。用户发送图片消息时，`_handle_image()` 仅返回原图片响应，不保存到 Blinko。

用户需要：
- 发送图片后能保存为笔记
- 图片可以附带文字描述（2分钟窗口期内）
- 连续发送多张图片可合并到同一笔记

## Scope

**In Scope:**
- 图片消息处理：从 PicUrl 下载图片并上传到 Blinko
- 待更新笔记缓存：按用户缓存 note_id，支持 2 分钟窗口期
- 笔记创建与更新：使用 Blinko upsert API
- 文字描述关联：文字消息检查缓存，更新已有笔记

**Out of Scope:**
- 视频、语音消息处理（保持现状）
- 企业微信客服（KF）消息的图片处理（本次只针对企业微信应用消息）
- 图片 OCR 或 AI 自动描述

## Capabilities

1. **Image Upload** - 从 PicUrl 下载图片并上传到 Blinko，获取 attachment 信息
2. **Image Note Creation** - 创建包含图片的笔记，支持追加多张图片
3. **Pending Note Cache** - 按用户缓存待更新笔记，120秒过期
4. **Text Description Association** - 文字消息关联待更新笔记，添加描述

## Success Criteria

- 用户发送单张图片，能创建笔记并返回提示
- 用户连续发送多张图片（2分钟内），能追加到同一笔记
- 用户发送文字（有待更新笔记），能更新笔记内容
- 用户发送文字（无待更新笔记），能独立保存文字笔记
- 超时后的图片笔记保持已保存状态（无描述）