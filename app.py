#!/usr/bin/env python
"""
企业微信应用 - Blinko笔记同步服务
主入口文件 (FastAPI 版本)
"""

import sys
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config.settings import settings
from core.message_handler import MessageHandler
from core.event_handler import EventHandler
from core.note_handler import NoteHandler
from wecom_app_svr.crypto import WecomCrypto
from utils.logger import setup_logging, get_logger


# 配置日志
setup_logging()
logger = get_logger(__name__)


# 创建 FastAPI 应用
app = FastAPI(
    title="Blinko-WeChat Sync Service",
    description="企业微信应用消息同步到 Blinko 笔记服务",
    version="1.0.0"
)


# 初始化处理器
message_handler = MessageHandler()
event_handler = EventHandler()
note_handler = NoteHandler()


# 初始化企业微信加解密
crypto = WecomCrypto(
    token=settings.WECOM_TOKEN,
    aes_key=settings.WECOM_AES_KEY,
    corp_id=settings.WECOM_CORP_ID
)


class SaveNoteRequest(BaseModel):
    """保存笔记请求"""
    note: str


class SaveNoteResponse(BaseModel):
    """保存笔记响应"""
    success: bool
    message: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str


class StatsResponse(BaseModel):
    """统计信息响应"""
    token_manager: str
    message_cache: str
    wecom_api: str
    blinko_service: str


@app.get("/echo")
async def echo():
    """Echo 接口，用于测试"""
    logger.info("收到 echo 请求")
    return PlainTextResponse("helloworld")


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return HealthResponse(status="ok", service="blinko-wx-svr")


@app.get("/stats")
async def stats():
    """统计接口（显示容器状态）"""
    return StatsResponse(
        token_manager="initialized",
        message_cache="initialized",
        wecom_api="initialized",
        blinko_service="initialized"
    )


@app.post("/api/v1/save_note")
async def save_note(req: SaveNoteRequest):
    """
    保存笔记接口

    Args:
        req: 请求体，包含 note 字段

    Returns:
        JSON 响应
    """
    note_content = req.note.strip()

    if not note_content:
        logger.warning("保存笔记: note 字段为空")
        return SaveNoteResponse(success=False, message="note 字段不能为空")

    logger.info(f"收到保存笔记请求: {note_content[:50]}...")

    success = note_handler.save_text(note_content)

    if success:
        logger.info(f"笔记保存成功: {note_content[:30]}...")
        return SaveNoteResponse(success=True, message="笔记保存成功")
    else:
        logger.error(f"笔记保存失败: {note_content[:30]}...")
        return SaveNoteResponse(success=False, message="笔记保存失败")


@app.get("/wecom_app_cb")
async def wecom_callback_verify(request: Request):
    """
    企业微信回调验证接口 (GET)

    用于验证服务器配置
    """
    params = request.query_params
    msg_signature = params.get("msg_signature")
    timestamp = params.get("timestamp")
    nonce = params.get("nonce")
    echostr = params.get("echostr")

    if not all([msg_signature, timestamp, nonce, echostr]):
        logger.warning("回调验证缺少参数")
        raise HTTPException(status_code=400, detail="缺少必需参数")

    # 验证 URL
    try:
        decrypted = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info("回调验证成功")
        return PlainTextResponse(decrypted)
    except Exception as e:
        logger.error(f"回调验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail="验证失败")


@app.post("/wecom_app_cb")
async def wecom_callback_handle(request: Request):
    """
    企业微信回调处理接口 (POST)

    处理消息和事件
    """
    params = request.query_params
    msg_signature = params.get("msg_signature")
    timestamp = params.get("timestamp")
    nonce = params.get("nonce")

    if not all([msg_signature, timestamp, nonce]):
        logger.warning("回调处理缺少参数")
        raise HTTPException(status_code=400, detail="缺少必需参数")

    # 获取请求体
    body = await request.body()

    # 解密消息
    try:
        decrypted_xml = crypto.decrypt_msg(body, msg_signature, timestamp, nonce)
        logger.info(f"解密消息: {decrypted_xml[:200]}...")
    except Exception as e:
        logger.error(f"消息解密失败: {str(e)}")
        raise HTTPException(status_code=400, detail="解密失败")

    # 解析消息
    from wecom_app_svr.req_msg import ReqMsg
    msg = ReqMsg.create_msg_from_xml(decrypted_xml)

    if msg is None:
        logger.warning("无法解析消息")
        rsp_xml = crypto.encrypt_msg("<xml><MsgType>text</MsgType><Content>invalid msg</Content></xml>", nonce, timestamp)
        return PlainTextResponse(rsp_xml)

    # 处理消息
    try:
        if msg.msg_type == 'event':
            rsp_msg = event_handler.handle(msg)
        else:
            rsp_msg = message_handler.handle(msg)

        # 加密响应
        rsp_xml = crypto.encrypt_msg(rsp_msg.dump_xml(), nonce, timestamp)
        return PlainTextResponse(rsp_xml)

    except Exception as e:
        logger.error(f"消息处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="处理失败")


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    try:
        settings.validate()
        logger.info("配置验证通过")
        logger.info(f"服务启动: {settings.HOST}:{settings.PORT}")
    except ValueError as e:
        logger.error(f"配置错误: {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )


if __name__ == '__main__':
    main()