"""
企业微信 API 客户端
使用 httpx 进行 HTTP 请求
"""

import httpx
from typing import Optional, Dict, Any
from services.token_manager import TokenManager
from utils.logger import get_logger


class WeComAPI:
    """企业微信 API 客户端"""

    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self):
        self.token_manager = TokenManager()
        self.logger = get_logger(__name__)

        # 创建 httpx 客户端
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

    def get_latest_message(
        self,
        open_kfid: str,
        token: str,
        cursor: str = "",
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的客服消息（同步）

        Args:
            open_kfid: 客服账号 ID
            token: 同步 Token
            cursor: 游标，用于分页
            limit: 每次拉取的消息数量

        Returns:
            最新一条消息的字典，如果没有消息则返回 None
        """
        url = f"{self.BASE_URL}/kf/sync_msg"
        params = {"access_token": self.token_manager.get_token()}

        data = {
            "token": token,
            "open_kfid": open_kfid,
            "limit": limit
        }

        if cursor:
            data["cursor"] = cursor

        try:
            self.logger.debug(f"正在获取客服消息，open_kfid: {open_kfid}")
            response = self.client.post(url, params=params, json=data)
            response_data = response.json()

            errcode = response_data.get("errcode")
            if errcode != 0:
                errmsg = response_data.get("errmsg", "unknown")
                self.logger.error(f"获取客服消息失败: errcode={errcode}, errmsg={errmsg}")
                return None

            msg_list = response_data.get("msg_list", [])
            if msg_list:
                latest_msg = msg_list[-1]
                self.logger.info(f"获取到最新消息，msgid: {latest_msg.get('msgid')}, msgtype: {latest_msg.get('msgtype')}")
                return latest_msg

            self.logger.info("未获取到消息")
            return None

        except httpx.RequestError as e:
            self.logger.error(f"获取客服消息网络异常: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"获取客服消息异常: {str(e)}")
            return None

    async def get_latest_message_async(
        self,
        open_kfid: str,
        token: str,
        cursor: str = "",
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的客服消息（异步）

        Args:
            open_kfid: 客服账号 ID
            token: 同步 Token
            cursor: 游标
            limit: 每次拉取的消息数量

        Returns:
            最新一条消息的字典，如果没有消息则返回 None
        """
        url = f"{self.BASE_URL}/kf/sync_msg"
        access_token = await self.token_manager.get_token_async()
        params = {"access_token": access_token}

        data = {
            "token": token,
            "open_kfid": open_kfid,
            "limit": limit
        }

        if cursor:
            data["cursor"] = cursor

        try:
            self.logger.debug(f"正在获取客服消息（异步），open_kfid: {open_kfid}")
            response = await self.async_client.post(url, params=params, json=data)
            response_data = response.json()

            errcode = response_data.get("errcode")
            if errcode != 0:
                errmsg = response_data.get("errmsg", "unknown")
                self.logger.error(f"获取客服消息失败（异步）: errcode={errcode}, errmsg={errmsg}")
                return None

            msg_list = response_data.get("msg_list", [])
            if msg_list:
                latest_msg = msg_list[-1]
                self.logger.info(f"获取到最新消息（异步），msgid: {latest_msg.get('msgid')}")
                return latest_msg

            return None

        except httpx.RequestError as e:
            self.logger.error(f"获取客服消息网络异常（异步）: {str(e)}")
            return None

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

    def get_media_url(self, media_id: str) -> Optional[str]:
        """
        获取素材下载 URL

        Args:
            media_id: 素材 ID

        Returns:
            下载 URL 或 None
        """
        access_token = self.token_manager.get_token()
        return f"{self.BASE_URL}/media/get?access_token={access_token}&media_id={media_id}"