#!/usr/bin/env python
"""
企业微信应用 - Blinko笔记同步服务
主入口文件
"""

import sys
from flask import request, jsonify
from wecom_app_svr import WecomAppServer
from config.settings import settings
from core.message_handler import MessageHandler
from core.event_handler import EventHandler
from utils.logger import setup_logging
from utils.logger import get_logger


def main():
    """主函数"""
    # 配置日志
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        # 验证配置
        settings.validate()
        logger.info("配置验证通过")
        
        # 创建服务器实例
        server = WecomAppServer(
            name="wecom-app-svr",
            host=settings.HOST,
            port=settings.PORT,
            path='/wecom_app_cb',
            token=settings.WECOM_TOKEN,
            aes_key=settings.WECOM_AES_KEY,
            corp_id=settings.WECOM_CORP_ID
        )
        
        # 创建处理器
        message_handler = MessageHandler()
        event_handler = EventHandler()
        
        # 设置消息和事件处理器
        server.set_message_handler(message_handler.handle)
        server.set_event_handler(event_handler.handle)

        @server.app.route('/echo', methods=['GET'])
        def echo():
            """Echo接口,用于测试"""
            logger.info("收到echo请求")
            return 'helloworld'
        
        @server.app.route('/api/v1/save_note', methods=['POST'])
        def save_note():
            """
            保存笔记接口
            
            请求格式: {"note": "笔记内容"}
            
            Returns:
                JSON响应
            """
            try:
                # 获取请求数据
                data = request.get_json()
                
                if not data:
                    logger.warning("保存笔记: 请求体为空")
                    return jsonify({
                        "success": False,
                        "message": "请求体为空"
                    }), 400
                
                # 获取note内容
                note_content = data.get('note', '').strip()
                
                if not note_content:
                    logger.warning("保存笔记: note字段为空")
                    return jsonify({
                        "success": False,
                        "message": "note字段不能为空"
                    }), 400
                
                logger.info(f"收到保存笔记请求: {note_content[:50]}...")
                
                # 调用消息处理器处理文本内容
                success = message_handler.handle_text_content(note_content)
                
                if success:
                    logger.info(f"笔记保存成功: {note_content[:30]}...")
                    return jsonify({
                        "success": True,
                        "message": "笔记保存成功"
                    }), 200
                else:
                    logger.error(f"笔记保存失败: {note_content[:30]}...")
                    return jsonify({
                        "success": False,
                        "message": "笔记保存失败"
                    }), 500
            
            except Exception as e:
                logger.error(f"保存笔记异常: {str(e)}", exc_info=True)
                return jsonify({
                    "success": False,
                    "message": f"服务器异常: {str(e)}"
                }), 500

        @server.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查接口"""
            return jsonify({
                "status": "ok",
                "service": "blinko-wx-svr"
            }), 200

        # 启动服务
        logger.info(f"启动服务: {settings.HOST}:{settings.PORT}")
        server.run()
    
    except ValueError as e:
        logger.error(f"配置错误: {str(e)}")
        logger.error("请检查环境变量配置")
        sys.exit(1)
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
