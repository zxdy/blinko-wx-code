"""
Blinko API 服务客户端
使用 httpx 进行 HTTP 请求
"""

import httpx
from typing import Optional
from config.settings import settings
from config.constants import NOTE_TYPE_THOUGHT, NOTE_LENGTH_THRESHOLD
from utils.logger import get_logger


class BlinkoService:
    """Blinko API 服务客户端"""

    def __init__(self):
        self.api_url = settings.BLINKO_API_URL
        self.api_token = settings.BLINKO_API_TOKEN
        self.callback_url = settings.CALLBACK_URL
        self.logger = get_logger(__name__)

        # 创建 httpx 客户端（支持异步）
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.Client:
        """获取同步客户端"""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """获取异步客户端"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=30.0)
        return self._async_client

    def save_note(self, content: str) -> bool:
        """
        保存笔记到 Blinko

        Args:
            content: 笔记内容

        Returns:
            True 表示保存成功，False 表示失败
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
            self.logger.info(f"正在保存笔记，内容长度: {len(content)}")
            response = self.client.post(self.api_url, json=data, headers=headers)

            if response.status_code == 200:
                json_data = response.json()
                note_id = json_data.get("id", 0)

                if note_id > 0:
                    self.logger.info(f"笔记保存成功，ID: {note_id}")
                    self._notify_callback_sync("笔记保存成功")
                    return True
                else:
                    self.logger.error(f"笔记保存失败: {json_data}")
                    self._notify_callback_sync("笔记保存失败")
                    return False
            else:
                self.logger.error(f"笔记保存失败，状态码: {response.status_code}，响应: {response.text}")
                self._notify_callback_sync("笔记保存失败")
                return False

        except httpx.RequestError as e:
            self.logger.error(f"笔记保存网络异常: {str(e)}")
            self._notify_callback_sync("笔记保存失败")
            return False
        except Exception as e:
            self.logger.error(f"笔记保存异常: {str(e)}")
            self._notify_callback_sync("笔记保存失败")
            return False

    async def save_note_async(self, content: str) -> bool:
        """
        异步保存笔记到 Blinko

        Args:
            content: 笔记内容

        Returns:
            True 表示保存成功，False 表示失败
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }

        note_type = NOTE_TYPE_THOUGHT if len(content) < NOTE_LENGTH_THRESHOLD else 1

        data = {
            "content": content,
            "type": note_type
        }

        try:
            self.logger.info(f"正在保存笔记（异步），内容长度: {len(content)}")
            response = await self.async_client.post(self.api_url, json=data, headers=headers)

            if response.status_code == 200:
                json_data = response.json()
                note_id = json_data.get("id", 0)

                if note_id > 0:
                    self.logger.info(f"笔记保存成功（异步），ID: {note_id}")
                    return True
                else:
                    self.logger.error(f"笔记保存失败（异步）: {json_data}")
                    return False
            else:
                self.logger.error(f"笔记保存失败（异步），状态码: {response.status_code}")
                return False

        except httpx.RequestError as e:
            self.logger.error(f"笔记保存网络异常（异步）: {str(e)}")
            return False

    def _notify_callback_sync(self, message: str):
        """
        发送回调通知（同步）

        Args:
            message: 通知消息
        """
        if not self.callback_url:
            self.logger.warning("回调地址为空，跳过通知")
            return

        try:
            notify_url = f"{self.callback_url}/{message}"
            self.client.get(notify_url, timeout=5.0)
            self.logger.info(f"回调通知成功: {notify_url}")
        except Exception as e:
            self.logger.warning(f"回调通知失败: {str(e)}")

    async def _notify_callback_async(self, message: str):
        """
        发送回调通知（异步）

        Args:
            message: 通知消息
        """
        if not self.callback_url:
            return

        try:
            notify_url = f"{self.callback_url}/{message}"
            await self.async_client.get(notify_url, timeout=5.0)
            self.logger.info(f"回调通知成功（异步）: {notify_url}")
        except Exception as e:
            self.logger.warning(f"回调通知失败（异步）: {str(e)}")

    def close(self):
        """关闭客户端"""
        if self._client:
            self._client.close()
            self._client = None

    async def close_async(self):
        """关闭异步客户端"""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None