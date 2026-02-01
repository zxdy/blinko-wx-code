import requests
from typing import Optional
from config.settings import settings
from config.constants import NOTE_TYPE_THOUGHT, NOTE_LENGTH_THRESHOLD
from utils.logger import get_logger


class BlinkoService:
    """Blinko API服务客户端"""
    
    def __init__(self):
        self.api_url = settings.BLINKO_API_URL
        self.api_token = settings.BLINKO_API_TOKEN
        self.callback_url = settings.CALLBACK_URL
        self.logger = get_logger(__name__)
    
    def save_note(self, content: str) -> bool:
        """
        保存笔记到Blinko
        
        Args:
            content: 笔记内容
            
        Returns:
            True表示保存成功,False表示失败
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }
        
        # 根据内容长度判断笔记类型
        note_type = NOTE_TYPE_THOUGHT if len(content) < NOTE_LENGTH_THRESHOLD else 1
        
        data = {
            "content": content,
            "type": note_type
        }
        
        try:
            self.logger.info(f"正在保存笔记, 内容长度: {len(content)}")
            response = requests.post(self.api_url, json=data, headers=headers)
            
            if response.status_code == 200:
                json_data = response.json()
                note_id = json_data.get("id", 0)
                
                if note_id > 0:
                    self.logger.info(f"笔记保存成功, ID: {note_id}")
                    self._notify_callback("笔记保存成功")
                    return True
                else:
                    self.logger.error(f"笔记保存失败: {json_data}")
                    self._notify_callback("笔记保存失败")
                    return False
            else:
                self.logger.error(f"笔记保存失败, 状态码: {response.status_code}, 响应: {response.text}")
                self._notify_callback("笔记保存失败")
                return False
        
        except requests.RequestException as e:
            self.logger.error(f"笔记保存网络异常: {str(e)}")
            self._notify_callback("笔记保存失败")
            return False
        except Exception as e:
            self.logger.error(f"笔记保存异常: {str(e)}")
            self._notify_callback("笔记保存失败")
            return False
    
    def _notify_callback(self, message: str):
        """
        发送回调通知(可选)
        
        Args:
            message: 通知消息
        """
        if not self.callback_url:
            self.logger.error(f"回调通知失败: 回调地址为空")
            return
        
        try:
            notify_url = f"{self.callback_url}/{message}"
            requests.get(notify_url, timeout=5000)
            self.logger.info(f"回调通知成功: {notify_url}")
        except Exception as e:
            self.logger.warning(f"回调通知失败: {str(e)}")
