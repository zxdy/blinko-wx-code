import time
import threading
import requests
from config.settings import settings
from utils.logger import get_logger


class TokenManager:
    """企业微信Access Token管理器"""
    
    def __init__(self):
        self.access_token: str = None
        self.expires_at: float = 0
        self.lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    def get_token(self) -> str:
        """
        获取有效的access token
        
        Returns:
            有效的access token
            
        Raises:
            Exception: 获取token失败时抛出异常
        """
        current_time = time.time()
        
        # 如果token存在且剩余时间超过60秒,直接返回
        if self.access_token and self.expires_at - current_time > 60:
            return self.access_token
        
        # 需要刷新token
        return self._refresh_token()
    
    def _refresh_token(self) -> str:
        """
        刷新access token
        
        Returns:
            新的access token
        """
        with self.lock:
            # 双重检查,避免多个线程同时刷新
            current_time = time.time()
            if self.access_token and self.expires_at - current_time > 60:
                return self.access_token
            
            url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            params = {
                "corpid": settings.WECOM_CORP_ID,
                "corpsecret": settings.WECOM_CORP_SECRET
            }
            
            try:
                response = requests.get(url, params=params)
                response_data = response.json()
                
                if 'access_token' in response_data:
                    self.access_token = response_data['access_token']
                    expires_in = response_data.get('expires_in', 7200)
                    self.expires_at = current_time + expires_in - 60  # 提前60秒过期
                    self.logger.info(f"access_token刷新成功")
                    return self.access_token
                else:
                    errcode = response_data.get('errcode', 'unknown')
                    errmsg = response_data.get('errmsg', 'unknown')
                    raise Exception(f"获取access_token失败: errcode={errcode}, errmsg={errmsg}")
            
            except requests.RequestException as e:
                self.logger.error(f"请求access_token异常: {str(e)}")
                raise Exception(f"网络请求失败: {str(e)}")
    
    def clear(self):
        """清除token,强制下次重新获取"""
        with self.lock:
            self.access_token = None
            self.expires_at = 0
