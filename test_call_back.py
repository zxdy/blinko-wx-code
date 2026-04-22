import base64
import binascii
import json
import time
import hashlib
import random
import string
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
from flask import Flask, request, make_response
import xml.etree.ElementTree as ET

app = Flask(__name__)

import os
from config.settings import settings

# -------------------------- 企业微信回调配置（从环境变量读取） --------------------------
CORP_ID = settings.WECOM_CORP_ID
AGENT_ID = os.getenv("WECOM_AGENT_ID", "1000002")  # 应用ID
TOKEN = settings.WECOM_TOKEN
ENCODING_AES_KEY = settings.WECOM_AES_KEY


msg = """

1.02 复制打开抖音，看看【杭州网的作品】# 宋威龙 回应此前在# 杭州 散步被要微信，“我... https://v.douyin.com/9XnRKSMyvIM/ 02/06 VYm:/ P@k.cn 

"""


# -------------------------- 工具函数：修复Base64 Padding问题 --------------------------
def fix_base64_padding(b64_str):
    """
    自适应修复Base64字符串的padding问题：
    Base64要求长度是4的倍数，不足补=
    """
    b64_str = b64_str.strip()  # 去除首尾空格/换行
    padding = len(b64_str) % 4
    if padding != 0:
        b64_str += '=' * (4 - padding)
    return b64_str


# -------------------------- 企业微信官方加解密工具类（修复Padding版） --------------------------
class WXBizMsgCrypt:
    def __init__(self, token, encoding_aes_key, corp_id):
        self.token = token
        self.corp_id = corp_id
        # 核心修复：自适应填充EncodingAESKey，解决padding问题
        self.aes_key = self._decode_aes_key(encoding_aes_key)
        self.block_size = 32  # AES-256-CBC 块大小

    def _decode_aes_key(self, encoding_aes_key):
        """解码EncodingAESKey，处理padding异常"""
        try:
            # 步骤1：修复Base64 padding
            fixed_key = fix_base64_padding(encoding_aes_key)
            # 步骤2：Base64解码（带异常捕获）
            aes_key = base64.b64decode(fixed_key, validate=True)
            # 步骤3：校验AES-256密钥长度（必须32字节）
            if len(aes_key) != 32:
                raise ValueError(f"AES密钥长度错误（需32字节），实际：{len(aes_key)}字节")
            return aes_key
        except binascii.Error as e:
            raise ValueError(f"Base64解码失败：{str(e)}，原始Key：{encoding_aes_key}")
        except Exception as e:
            raise ValueError(f"解码EncodingAESKey失败：{str(e)}")

    def _get_nonce(self, length=16):
        """生成随机Nonce"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def verify_signature(self, signature, timestamp, nonce, encrypt):
        """验证签名：sha1(sort(token, timestamp, nonce, encrypt))"""
        params = sorted([self.token, timestamp, nonce, encrypt])
        sign_str = ''.join(params).encode('utf-8')
        sha1 = hashlib.sha1(sign_str).hexdigest()
        return sha1 == signature

    def decrypt(self, encrypted_msg):
        """解密Encrypt字段，兼容padding修复"""
        try:
            # 修复加密字符串的padding（部分场景下企业微信返回的Encrypt也会缺padding）
            fixed_encrypted = fix_base64_padding(encrypted_msg)
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])  # IV取前16位
            decrypted = unpad(cipher.decrypt(base64.b64decode(fixed_encrypted)), self.block_size)
            # 解析明文结构：16位随机数 + 4位长度 + 消息体 + CorpID
            msg_len = int.from_bytes(decrypted[16:20], byteorder='big')
            msg = decrypted[20:20 + msg_len].decode('utf-8')
            corp_id = decrypted[20 + msg_len:].decode('utf-8')
            if corp_id != self.corp_id:
                raise ValueError(f"CorpID校验失败：预期{self.corp_id}，实际{corp_id}")
            return msg
        except Exception as e:
            raise ValueError(f"解密失败：{str(e)}")

    def encrypt(self, plain_msg):
        """加密明文消息，处理padding"""
        try:
            # 构造加密原始数据：16位随机数 + 4位长度 + 消息体 + CorpID
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
            msg_bytes = plain_msg.encode('utf-8')
            msg_len = len(msg_bytes).to_bytes(4, byteorder='big')
            corp_id_bytes = self.corp_id.encode('utf-8')
            raw = random_str + msg_len + msg_bytes + corp_id_bytes
            # PKCS7填充
            padded_raw = pad(raw, self.block_size)
            # AES加密 + Base64编码
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            encrypted = base64.b64encode(cipher.encrypt(padded_raw)).decode('utf-8')
            return encrypted
        except Exception as e:
            raise ValueError(f"加密失败：{str(e)}")


# # -------------------------- 回调接口（完整校验+异常处理） --------------------------
# @app.route("/wework/callback", methods=["GET", "POST"])
# def wework_callback():
#     try:
#         crypt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)
#     except ValueError as e:
#         return make_response(f"初始化加解密工具失败：{str(e)}", 500)
# 
#     # 1. GET请求：URL验证（首次配置回调）
#     if request.method == "GET":
#         try:
#             signature = request.args.get("signature")
#             timestamp = request.args.get("timestamp")
#             nonce = request.args.get("nonce")
#             echostr = request.args.get("echostr")
# 
#             # 校验参数完整性
#             if not all([signature, timestamp, nonce, echostr]):
#                 return make_response("参数缺失（signature/timestamp/nonce/echostr）", 400)
# 
#             # 验证签名 + 解密echostr
#             if not crypt.verify_signature(signature, timestamp, nonce, echostr):
#                 return make_response("签名验证失败", 403)
#             plain_echostr = crypt.decrypt(echostr)
#             return make_response(plain_echostr)
#         except Exception as e:
#             return make_response(f"GET验证失败：{str(e)}", 403)
# 
#     # 2. POST请求：消息回调处理
#     else:
#         try:
#             # 解析URL参数
#             signature = request.args.get("signature")
#             timestamp = request.args.get("timestamp")
#             nonce = request.args.get("nonce")
#             if not all([signature, timestamp, nonce]):
#                 return make_response("参数缺失（signature/timestamp/nonce）", 400)
# 
#             # 解析XML数据
#             xml_data = request.data.decode("utf-8")
#             root = ET.fromstring(xml_data)
#             encrypt = root.find("Encrypt").text if root.find("Encrypt") is not None else ""
#             if not encrypt:
#                 return make_response("XML中缺失Encrypt字段", 400)
# 
#             # 校验签名
#             if not crypt.verify_signature(signature, timestamp, nonce, encrypt):
#                 return make_response("签名验证失败", 403)
# 
#             # 解密并解析消息
#             plain_msg = crypt.decrypt(encrypt)
#             msg_dict = json.loads(plain_msg)
# 
#             # 解析文本消息
#             if msg_dict.get("MsgType") == "text":
#                 print("===== 解析到文本消息（修复Padding版） =====")
#                 print(f"请求参数：Signature={signature}, Timestamp={timestamp}, Nonce={nonce}")
#                 print(f"企业CorpID：{msg_dict.get('ToUserName')}")
#                 print(f"发送人UserID：{msg_dict.get('FromUserName')}")
#                 print(
#                     f"消息创建时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(msg_dict.get('CreateTime'))))}")
#                 print(f"应用ID：{msg_dict.get('AgentID')}")
#                 print(f"消息ID：{msg_dict.get('MsgId')}")
#                 print(f"文本内容：{msg_dict.get('Content')}")
#                 print("==========================================\n")
# 
#             return make_response("success")
#         except Exception as e:
#             return make_response(f"POST回调处理失败：{str(e)}", 400)


# -------------------------- 模拟回调请求（带Padding修复） --------------------------
def simulate_wework_callback():
    import requests
    try:
        crypt = WXBizMsgCrypt(TOKEN, ENCODING_AES_KEY, CORP_ID)
    except ValueError as e:
        print(f"模拟回调初始化失败：{str(e)}")
        return

    plain_text = f"""
<xml>
   <ToUserName><![CDATA[toUser]]></ToUserName>
   <FromUserName><![CDATA[fromUser]]></FromUserName> 
   <CreateTime>1348831860</CreateTime>
   <MsgType><![CDATA[text]]></MsgType>
   <Content><![CDATA[{msg}]]></Content>
   <MsgId>1234567890123456</MsgId>
   <AgentID>1</AgentID>
</xml>

"""

    # 加密
    encrypt = crypt.encrypt(plain_text)
    # 生成随机参数
    nonce = crypt._get_nonce()
    timestamp = str(int(time.time()))
    # 生成签名
    params = sorted([TOKEN, timestamp, nonce, encrypt])
    signature = hashlib.sha1(''.join(params).encode('utf-8')).hexdigest()

    # 构造XML
    xml_data = f"""
    <xml>
      <ToUserName><![CDATA[{CORP_ID}]]></ToUserName>
      <Encrypt><![CDATA[{encrypt}]]></Encrypt>
      <AgentID><![CDATA[{AGENT_ID}]]></AgentID>
    </xml>
    """

    # 发送请求
    try:
        response = requests.post(
            url=f"http://127.0.0.1:5001/wecom_app_cb?msg_signature={signature}&timestamp={timestamp}&nonce={nonce}",
            data=xml_data.encode("utf-8"),
            headers={"Content-Type": "text/xml"}
        )
        print(f"模拟回调响应：状态码={response.status_code}，内容={response.text}")
    except requests.exceptions.ConnectionError:
        print("连接失败：请确认Flask服务已启动（端口5000）")


if __name__ == "__main__":
    # 启动Flask服务
    # import threading
    # 
    # threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False)).start()
    # time.sleep(1)  # 等待服务启动

    # 模拟回调
    simulate_wework_callback()