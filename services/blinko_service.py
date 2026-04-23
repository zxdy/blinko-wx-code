"""
Blinko API 服务客户端
使用 httpx 进行 HTTP 请求
"""

import httpx
import io
import uuid
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, urljoin
from config.settings import settings
from config.constants import NOTE_TYPE_THOUGHT, NOTE_LENGTH_THRESHOLD
from utils.logger import get_logger


class BlinkoService:
    """Blinko API 服务客户端"""

    def __init__(self):
        # 从 BLINKO_API_URL 提取服务器基础 URL
        # 例如: http://192.168.50.118:1111/api/v1/note/upsert -> http://192.168.50.118:1111
        full_api_url = settings.BLINKO_API_URL.rstrip('/')
        parsed = urlparse(full_api_url)
        self.server_url = f"{parsed.scheme}://{parsed.netloc}"

        # 笔记保存 URL（完整路径）
        self.api_url = full_api_url
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

    def upload_image(self, image_url: str) -> Optional[Dict]:
        """
        从 URL 下载图片并上传到 Blinko 文件服务

        Args:
            image_url: 图片 URL (PicUrl)

        Returns:
            attachment 对象 {"name", "path", "size", "type"} 或 None
        """
        # 文件上传 URL（基于服务器地址）
        upload_url = f"{self.server_url}/api/file/upload"
        headers = {
            "Authorization": f"Bearer {self.api_token}"
        }

        try:
            # 1. 从 PicUrl 下载图片
            self.logger.info(f"正在下载图片: {image_url}")
            download_response = self.client.get(image_url, timeout=30.0, follow_redirects=True)

            if download_response.status_code != 200:
                self.logger.error(f"图片下载失败，状态码: {download_response.status_code}")
                return None

            # 获取图片内容
            image_content = download_response.content
            content_type = download_response.headers.get("content-type", "image/png")

            # 从 URL 或 Content-Type 推断文件名
            parsed_url = urlparse(image_url)
            filename = parsed_url.path.split('/')[-1] or f"image_{uuid.uuid4().hex[:8]}"
            if not filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                # 根据 content-type 推断扩展名
                ext_map = {
                    "image/png": ".png",
                    "image/jpeg": ".jpg",
                    "image/jpg": ".jpg",
                    "image/gif": ".gif",
                    "image/webp": ".webp"
                }
                ext = ext_map.get(content_type, ".png")
                filename = f"{filename}{ext}"

            # 2. 上传到 Blinko
            self.logger.info(f"正在上传图片到 Blinko，文件名: {filename}, 大小: {len(image_content)}")
            files = {
                "file": (filename, io.BytesIO(image_content), content_type)
            }

            upload_response = self.client.post(upload_url, files=files, headers=headers)

            if upload_response.status_code == 200:
                result = upload_response.json()
                self.logger.info(f"图片上传成功: {result}")
                # 转换为标准 attachment 格式
                # Blinko 返回: fileName, filePath -> 需要: name, path
                attachment = {
                    "name": result.get("fileName", result.get("name", f"image_{uuid.uuid4().hex[:8]}.jpg")),
                    "path": result.get("filePath", result.get("path", "")),
                    "size": result.get("size", len(image_content)),
                    "type": result.get("type", content_type)
                }
                return attachment
            else:
                self.logger.error(f"图片上传失败，状态码: {upload_response.status_code}, 响应: {upload_response.text}")
                return None

        except httpx.RequestError as e:
            self.logger.error(f"图片下载/上传网络异常: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"图片处理异常: {str(e)}")
            return None

    def upsert_note(
        self,
        content: Optional[str] = None,
        attachments: List[Dict] = [],
        note_id: Optional[int] = None
    ) -> Tuple[Optional[int], bool]:
        """
        创建或更新笔记 (使用 upsert API)

        Args:
            content: 笔记内容（文字描述）
            attachments: 图片附件列表
            note_id: None=创建新笔记，有值=更新已有笔记

        Returns:
            (note_id, success) - 笔记 ID 和是否成功
        """
        upsert_url = f"{self.server_url}/api/v1/note/upsert"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }

        # 构建请求体 - 只发送必要字段，让 Blinko 自动设置时间
        data = {
            "content": content,
            "type": NOTE_TYPE_THOUGHT,
            "attachments": attachments,
            "id": note_id,
            "references": []
        }

        # 如果是更新已有笔记，需要传入 id
        if note_id is not None:
            data["id"] = note_id

        try:
            action = "创建" if note_id is None else f"更新(ID:{note_id})"
            self.logger.info(f"正在{action}笔记，attachments数量: {len(attachments)}")
            response = self.client.post(upsert_url, json=data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                # Blinko 返回格式: {"0": {"json": {...}, "meta": {...}}
                # 或者直接返回笔记对象
                note_data = result.get("0", {}).get("json", result)

                returned_id = note_data.get("id")
                if returned_id:
                    self.logger.info(f"笔记{action}成功，ID: {returned_id}")
                    return returned_id, True
                else:
                    self.logger.error(f"笔记{action}失败: {result}")
                    return None, False
            else:
                self.logger.error(f"笔记{action}失败，状态码: {response.status_code}, 响应: {response.text}")
                return None, False

        except httpx.RequestError as e:
            self.logger.error(f"笔记{action}网络异常: {str(e)}")
            return None, False
        except Exception as e:
            self.logger.error(f"笔记{action}异常: {str(e)}")
            return None, False