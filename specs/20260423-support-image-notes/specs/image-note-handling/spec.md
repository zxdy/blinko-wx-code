# Spec: Image Note Handling

## Purpose

处理企业微信应用发送的图片消息，创建或更新 Blinko 笔记，支持用户在 2 分钟窗口期内追加图片或添加文字描述。

## Definitions

- **Pending Note**: 已创建但可能被更新的笔记（缓存中存在 note_id 且未过期）
- **Window Period**: 120秒时间窗口，用户可在此期间追加图片或添加描述
- **Attachment**: Blinko 图片附件对象，包含 name、path、size、type 字段

## ADDED Requirements

### Requirement: Image Upload

系统 SHALL 从图片消息的 PicUrl 下载图片并上传到 Blinko 文件服务。

#### Scenario: Successful Image Upload
- **GIVEN** 图片消息包含有效的 PicUrl
- **WHEN** 系统处理图片消息
- **THEN** 系统 SHALL 下载图片、上传到 Blinko、返回 attachment 对象

#### Scenario: Image Upload Failure
- **GIVEN** PicUrl 无效或网络异常
- **WHEN** 系统尝试下载/上传图片
- **THEN** 系统 SHALL 记录错误日志、返回失败响应给用户

---

### Requirement: Image Note Creation

系统 SHALL 为图片创建 Blinko 笔记，使用 upsert API。

#### Scenario: First Image Creates Note
- **GIVEN** 用户无待更新笔记（缓存中没有记录）
- **WHEN** 用户发送第一张图片
- **THEN** 系统 SHALL 创建新笔记（id=null）、缓存 note_id 和创建时间、返回提示消息

#### Scenario: Subsequent Image Appends to Note
- **GIVEN** 用户有待更新笔记且未过期（created_at + 120秒 > 当前时间）
- **WHEN** 用户发送后续图片
- **THEN** 系统 SHALL 上传图片、追加 attachment 到已有笔记、更新缓存、返回提示消息

#### Scenario: Expired Note
- **GIVEN** 用户有待更新笔记但已过期
- **WHEN** 用户发送新图片
- **THEN** 系统 SHALL 创建新笔记（视为第一张图片）、清除旧缓存、缓存新 note_id

---

### Requirement: Pending Note Cache

系统 SHALL 按用户缓存待更新笔记信息，支持 120秒过期检查。

#### Scenario: Cache Structure
- **GIVEN** 系统需要缓存待更新笔记
- **THEN** 缓存结构 SHALL 为 `{user_id: {note_id, created_at, attachments}}`

#### Scenario: Cache Expiry Check
- **GIVEN** 缓存中有用户记录
- **WHEN** 检查是否过期
- **THEN** 系统 SHALL 返回 `created_at + 120秒 > 当前时间` 的布尔结果

#### Scenario: Cache Clear on Text Update
- **GIVEN** 文字消息成功更新笔记内容
- **WHEN** 更新完成
- **THEN** 系统 SHALL 清除该用户的缓存记录

---

### Requirement: Text Description Association

系统 SHALL 在收到文字消息时检查是否有待更新笔记并关联。

#### Scenario: Text Updates Pending Note
- **GIVEN** 用户有待更新笔记且未过期
- **WHEN** 用户发送文字消息
- **THEN** 系统 SHALL 调用 upsert 更换笔记 content、清除缓存、返回"笔记已更新"

#### Scenario: Text Creates Separate Note (No Pending)
- **GIVEN** 用户无待更新笔记或已过期
- **WHEN** 用户发送文字消息
- **THEN** 系统 SHALL 独立保存文字笔记、返回"笔记已保存"

---

### Requirement: User Response Messages

系统 SHALL 返回明确的提示消息给用户。

#### Scenario: Image Saved Response
- **GIVEN** 图片成功保存（创建或追加）
- **WHEN** 返回响应
- **THEN** 响应内容 SHALL 为"图片已保存，2分钟内发送文字可添加描述"

#### Scenario: Note Updated Response
- **GIVEN** 文字成功更新待更新笔记
- **WHEN** 返回响应
- **THEN** 响应内容 SHALL 为"笔记已更新"

## Constraints

- **CON-001**: 时间窗口为 120秒，不可配置
- **CON-002**: 仅处理企业微信应用消息，不处理客服（KF）消息
- **CON-003**: 使用 PicUrl 下载图片，不使用 MediaId 调用企业微信 API

## Dependencies

- **DEP-001**: Blinko 文件上传 API (`/api/file/upload`)
- **DEP-002**: Blinko 笔记 upsert API (`/api/v1/note/upsert`)
- **DEP-003**: httpx 用于 HTTP 请求（已有）