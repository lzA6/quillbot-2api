import time
import logging
import asyncio
import threading
from typing import Dict, Any, List

import cloudscraper
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings, AuthCredential

logger = logging.getLogger(__name__)

class QuillbotProvider:
    BASE_URL = "https://quillbot.com/api/raven/generate/image"

    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self._cred_index = 0
        self._cred_lock = threading.Lock()

    def _get_auth_credential(self) -> AuthCredential:
        """线程安全地轮询获取一个凭证"""
        with self._cred_lock:
            cred = settings.AUTH_CREDENTIALS[self._cred_index]
            self._cred_index = (self._cred_index + 1) % len(settings.AUTH_CREDENTIALS)
            return cred

    def _prepare_headers(self, cred: AuthCredential) -> Dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "cookie": cred.cookie,
            "origin": "https://quillbot.com",
            "platform-type": "webapp",
            "referer": "https://quillbot.com/image-tools/ai-image-generator",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "useridtoken": cred.token,
            "webapp-version": "34.0.1"
        }

    def _prepare_payload(self, prompt: str, aspect_ratio: str) -> Dict[str, Any]:
        return {
            "prompt": prompt,
            "category": "Auto",
            "aspectRatio": aspect_ratio,
            "promptId": "image/image_Scribbr_LT"
        }

    async def _send_single_request(self, payload: Dict[str, Any]) -> List[str]:
        loop = asyncio.get_running_loop()
        cred = self._get_auth_credential()
        headers = self._prepare_headers(cred)
        
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: self.scraper.post(
                    self.BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=settings.API_REQUEST_TIMEOUT
                )
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success") or "data" not in data or "images" not in data["data"]:
                error_message = data.get("message", "未知错误")
                logger.error(f"上游 API 返回失败: {error_message}")
                raise Exception(f"上游 API 错误: {error_message}")

            image_urls = [img["downloadUrl"] for img in data["data"]["images"] if "downloadUrl" in img]
            if not image_urls:
                raise ValueError("上游 API 未返回有效的图像 URL。")
            
            return image_urls

        except Exception as e:
            logger.error(f"请求上游失败: {e}", exc_info=True)
            raise

    async def generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request_data.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="参数 'prompt' 不能为空。")

        num_images = request_data.get("n", 1)
        # Quillbot 的长宽比参数是字符串 "1:1", "16:9" 等
        aspect_ratio = request_data.get("size", "1:1")
        
        # Quillbot 一次请求会生成多张图片，我们只需要根据 n 的值决定请求几次
        # 假设一次请求生成2张，如果 n=3，则需要请求2次
        num_requests = (num_images + 1) // 2 

        payload = self._prepare_payload(prompt, aspect_ratio)
        
        tasks = [self._send_single_request(payload) for _ in range(num_requests)]
        
        logger.info(f"准备向上游并发发送 {num_requests} 个请求以满足 {num_images} 张图片的需求...")

        try:
            results_list = await asyncio.gather(*tasks)
            
            all_urls = [url for sublist in results_list for url in sublist]
            
            # 截取所需数量的图片
            final_urls = all_urls[:num_images]

            response_data = {
                "created": int(time.time()),
                "data": [{"url": url} for url in final_urls]
            }
            return response_data

        except Exception as e:
            logger.error(f"处理并发请求时发生严重错误: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"上游服务错误: {str(e)}")

    async def get_models(self) -> JSONResponse:
        model_data = {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
        return JSONResponse(content=model_data)
