"""
企业微信消息加解密模块
"""

from wx_crypt import WXBizMsgCrypt, WxChannel_Wecom
import xml.etree.cElementTree as ET


class WecomCrypto:
    """企业微信消息加解密"""

    def __init__(self, token: str, aes_key: str, corp_id: str):
        self.crypt = WXBizMsgCrypt(token, aes_key, corp_id, channel=WxChannel_Wecom)

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """
        验证 URL

        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            echostr: 加密的 echo 字符串

        Returns:
            解密后的 echo 字符串
        """
        ret, decrypted = self.crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
        if ret != 0:
            raise ValueError(f"URL验证失败: ret={ret}")
        return decrypted

    def decrypt_msg(self, body: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        """
        解密消息

        Args:
            body: 请求体
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            解密后的 XML 字符串
        """
        ret, decrypted = self.crypt.DecryptMsg(body, msg_signature, timestamp, nonce)
        if ret != 0:
            raise ValueError(f"消息解密失败: ret={ret}")
        return decrypted.decode()

    def encrypt_msg(self, plain_xml: str, nonce: str, timestamp: str) -> str:
        """
        加密消息

        Args:
            plain_xml: 明文 XML
            nonce: 随机数
            timestamp: 时间戳

        Returns:
            加密后的 XML 字符串
        """
        ret, encrypted = self.crypt.EncryptMsg(plain_xml, nonce, timestamp)
        if ret != 0:
            raise ValueError(f"消息加密失败: ret={ret}")
        return encrypted