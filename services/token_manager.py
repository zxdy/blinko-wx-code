"""
企业微信 Access Token 管理器
使用 httpx 进行 HTTP 请求
"""

import time
import threading
import httpx
from typing import Optional
from config.settings import settings
from utils.logger import get_logger


class TokenManager:
    """企业微信 Access Token 管理器"""

    TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"

    def __init__(self):
        self.access_token: Optional[str] = None
        self.expires_at: float = 0
        self.lock = threading.Lock()
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

    def get_token(self) -> str:
        """
        获取有效的 access token（同步）

        Returns:
            有效的 access token

        Raises:
            Exception: 获取 token 失败时抛出异常
        """
        current_time = time.time()

        # 如果 token 存在且剩余时间超过 60 秒，直接返回
        if self.access_token and self.expires_at - current_time > 60:
            return self.access_token

        # 需要刷新 token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        """
        刷新 access token（同步）

        Returns:
            新的 access token
        """
        with self.lock:
            # 双重检查，避免多个线程同时刷新
            current_time = time.time()
            if self.access_token and self.expires_at - current_time > 60:
                return self.access_token

            params = {
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_CORP_SECRET
            }

            try:
                response = self.client.get(self.TOKEN_URL, params=params)
                response_data = response.json()

                if 'access_token' in response_data:
                    self.access_token = response_data['access_token']
                    expires_in = response_data.get('expires_in', 7200)
                    self.expires_at = current_time + expires_in - 60  # 提前 60 秒过期
                    self.logger.info("access_token 刷新成功")
                    return self.access_token
                else:
                    errcode = response_data.get('errcode', 'unknown')
                    errmsg = response_data.get('errmsg', 'unknown')
                    raise Exception(f"获取 access_token 失败: errcode={errcode}, errmsg={errmsg}")

            except httpx.RequestError as e:
                self.logger.error(f"请求 access_token 异常: {str(e)}")
                raise Exception(f"网络请求失败: {str(e)}")

    async def get_token_async(self) -> str:
        """
        获取有效的 access token（异步）

        Returns:
            有效的 access token
        """
        current_time = time.time()

        if self.access_token and self.expires_at - current_time > 60:
            return self.access_token

        return await self._refresh_token_async()

    async def _refresh_token_async(self) -> str:
        """
        刷新 access token（异步）

        Returns:
            新的 access token
        """
        with self.lock:
            current_time = time.time()
            if self.access_token and self.expires_at - current_time > 60:
                return self.access_token

            params = {
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_CORP_SECRET
            }

            try:
                response = await self.async_client.get(self.TOKEN_URL, params=params)
                response_data = response.json()

                if 'access_token' in response_data:
                    self.access_token = response_data['access_token']
                    expires_in = response_data.get('expires_in', 7200)
                    self.expires_at = current_time + expires_in - 60
                    self.logger.info("access_token 刷新成功（异步）")
                    return self.access_token
                else:
                    errcode = response_data.get('errcode', 'unknown')
                    errmsg = response_data.get('errmsg', 'unknown')
                    raise Exception(f"获取 access_token 失败（异步）: errcode={errcode}, errmsg={errmsg}")

            except httpx.RequestError as e:
                self.logger.error(f"请求 access_token 异常（异步）: {str(e)}")
                raise Exception(f"网络请求失败（异步）: {str(e)}")

    def clear(self):
        """清除 token，强制下次重新获取"""
        with self.lock:
            self.access_token = None
            self.expires_at = 0

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