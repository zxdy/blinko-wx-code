import requests
from typing import Optional, Dict, Any
from services.token_manager import TokenManager
from utils.logger import get_logger


class WeComAPI:
    """企业微信API客户端"""
    
    def __init__(self):
        self.token_manager = TokenManager()
        self.logger = get_logger(__name__)
    
    def get_latest_message(
        self,
        open_kfid: str,
        token: str,
        cursor: str = "",
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新的客服消息
        
        Args:
            open_kfid: 客服账号ID
            token: 同步 Token
            cursor: 游标,用于分页
            limit: 每次拉取的消息数量
            
        Returns:
            最新一条消息的字典,如果没有消息则返回None
        """
        url = "https://qyapi.weixin.qq.com/cgi-bin/kf/sync_msg"
        params = {"access_token": self.token_manager.get_token()}
        
        data = {
            "token": token,
            "open_kfid": open_kfid,
            "limit": limit
        }
        
        if cursor:
            data["cursor"] = cursor
        
        try:
            self.logger.debug(f"正在获取客服消息, open_kfid: {open_kfid}")
            response = requests.post(url, params=params, json=data)
            response_data = response.json()
            
            errcode = response_data.get("errcode")
            if errcode != 0:
                errmsg = response_data.get("errmsg", "unknown")
                self.logger.error(f"获取客服消息失败: errcode={errcode}, errmsg={errmsg}")
                return None
            
            msg_list = response_data.get("msg_list", [])
            if msg_list:
                latest_msg = msg_list[-1]
                self.logger.info(f"获取到最新消息, msgid: {latest_msg.get('msgid')}, msgtype: {latest_msg.get('msgtype')}")
                return latest_msg
            
            self.logger.info("未获取到消息")
            return None
        
        except requests.RequestException as e:
            self.logger.error(f"获取客服消息网络异常: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"获取客服消息异常: {str(e)}")
            return None
