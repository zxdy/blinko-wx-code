"""项目常量定义"""

# 消息类型常量
MSG_TYPE_TEXT = "text"
MSG_TYPE_IMAGE = "image"
MSG_TYPE_VOICE = "voice"
MSG_TYPE_VIDEO = "video"
MSG_TYPE_EVENT = "event"
MSG_TYPE_LINK = "link"

# 笔记类型常量
NOTE_TYPE_THOUGHT = 0  # 闪念
NOTE_TYPE_NOTE = 1     # 笔记

# 笔记长度阈值
NOTE_LENGTH_THRESHOLD = 200

# API响应消息
MSG_NOTE_SAVED = "note saved"
MSG_NOTE_ALREADY_SAVED = "note already saved"
MSG_SAVE_FAILED = "note save failed"

# 笔记模板预设
TEMPLATE_MINIMAL = "minimal"     # 最简模板
TEMPLATE_STANDARD = "standard"   # 标准模板（默认）
TEMPLATE_DETAILED = "detailed"   # 详细模板

# 待更新笔记缓存过期时间（秒）
PENDING_NOTE_EXPIRE_SECONDS = 120

# 图片笔记响应消息
MSG_IMAGE_SAVED = "图片已保存，2分钟内发送文字可添加描述"
MSG_NOTE_UPDATED = "笔记已更新"
