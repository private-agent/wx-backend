import requests
import json
from typing import Optional, Dict, Any, Callable
from app.utils.logger import logger
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from app.wechat.token_manager import TokenManager

class AsyncResponseHandler:
    def __init__(self, token_manager: TokenManager, appid: str, appsecret: str):
        self.token_manager = token_manager
        self.appid = appid
        self.appsecret = appsecret
        self.executor = ThreadPoolExecutor(max_workers=20)

    def _build_message_payload(self, external_resp: Dict, openid: str) -> Optional[Dict]:
        """增加默认消息处理"""
        msg_type = external_resp.get("msg_type", "text")
        content = external_resp.get("content", "")

        # 空内容处理
        if not content.strip():
            content = "未收到有效回复"

        return {
            "touser": openid,
            "msgtype": msg_type,
            "text": {"content": content}
        }

    def _send_custom_message(self, openid: str, payload: Dict):
        """实际发送客服消息"""
        try:
            access_token = self.token_manager.get_token(self.appid, self.appsecret)

            if not access_token:
                logger.error("Failed to get access token for customer service message")
                return

            url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()

            result = response.json()
            if result.get("errcode") != 0:
                logger.error(f"Failed to send customer service message: {result}")

        except Exception as e:
            logger.error(f"Error sending customer service message: {str(e)}")

    def send_async_response(self, openid: str, external_resp: Dict):
        """异步发送客服消息"""
        self.executor.submit(self._send_custom_message, openid, external_resp)

class ExternalServiceAdapter:
    def __init__(self, async_handler: AsyncResponseHandler, timeout: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.timeout = timeout
        self.async_handler = async_handler

    def _send_request(self, url: str, payload: Dict) -> Optional[Dict]:
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"External service request failed: {str(e)}")
            return None

    def call_service(
        self,
        wechat_msg: Dict,
        endpoint: str,
        request_mapper: Callable,
        response_mapper: Callable,
        openid: str
    ) -> Optional[Dict]:
        try:
            request_payload = request_mapper(wechat_msg)
            logger.debug(f"External request payload: {json.dumps(request_payload, indent=2)}")

            future = self.executor.submit(self._send_request, endpoint, request_payload)

            # 先立即返回success，后续异步处理
            self.executor.submit(self._handle_async_response, future, response_mapper, openid)
            return None

        except Exception as e:
            logger.error(f"Service call error: {str(e)}")
            return None

    def _handle_async_response(self, future, response_mapper: Callable, openid: str):
        try:
            result = future.result(timeout=self.timeout)
            if result:
                mapped_response = response_mapper(result)
                if mapped_response:
                    payload = self.async_handler._build_message_payload(mapped_response, openid)
                    if payload:
                        self.async_handler.send_async_response(openid, payload)
        except TimeoutError:
            logger.warning("External service timeout, sending notification")
            # 构建超时提示消息
            timeout_msg = {
                "msg_type": "text",
                "content": "请求处理超时，请稍后再试"
            }
            payload = self.async_handler._build_message_payload(timeout_msg, openid)
            if payload:
                self.async_handler.send_async_response(openid, payload)
        except Exception as e:
            logger.error(f"Async response handling failed: {str(e)}")
            # 发送通用错误提示
            error_msg = {
                "msg_type": "text",
                "content": "服务暂时不可用，请稍后重试"
            }
            payload = self.async_handler._build_message_payload(error_msg, openid)
            if payload:
                self.async_handler.send_async_response(openid, payload)

# 默认请求/响应映射器示例
def default_request_mapper(wechat_msg: Dict) -> Dict:
    """将微信消息转换为默认请求格式"""
    return {
        "user_id": wechat_msg.get("FromUserName"),
        "message_type": wechat_msg.get("MsgType"),
        "content": wechat_msg.get("Content"),
        "timestamp": wechat_msg.get("CreateTime")
    }

def default_response_mapper(external_resp: Dict) -> Dict:
    """将外部服务响应转换为微信回复格式"""
    return {
        "msg_type": external_resp.get("message_type", "text"),
        "content": external_resp.get("content", "")
    }

def openai_request_mapper(wechat_msg: Dict) -> Dict:
    """将微信消息转换为OpenAI请求格式"""
    return {
        # "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": wechat_msg.get("Content")}],
        "stream": False,
    }

def openai_response_mapper(external_resp: Dict) -> Dict:
    """将OpenAI响应转换为微信回复格式"""
    try:
        return {
            "msg_type": "text",
            "content": external_resp['choices'][0]['message']['content']
        }
    except KeyError as e:
        logger.error(f"OpenAI响应格式错误，缺少关键字段: {str(e)}")
        return {
            "msg_type": "text",
            "content": "OpenAI 响应错误，请联系管理员"
        }
    except Exception as e:
        logger.error(f"OpenAI response mapping failed: {str(e)}")
        return {
            "msg_type": "text",
            "content": "OpenAI 响应错误，请联系管理员"
        }

def ollama_request_mapper(wechat_msg: Dict) -> Dict:
    """将微信消息转换为Ollama请求格式"""
    return {
        "model": "llama2",
        "prompt": wechat_msg.get("Content"),
        "stream": False
    }

def ollama_response_mapper(external_resp: Dict) -> Dict:
    """将Ollama响应转换为微信回复格式"""
    try:
        return {
            "msg_type": "text",
            "content": external_resp.get("response", "未收到有效回复")
        }
    except Exception as e:
        logger.error(f"Ollama response mapping failed: {str(e)}")
        return {
            "msg_type": "text",
            "content": "Ollama 服务响应异常"
        }

def custom_request_mapper(wechat_msg: Dict) -> Dict:
    """自定义请求格式（需用户实现）"""
    return {
        "session_id": f"{wechat_msg['FromUserName']}_{wechat_msg['CreateTime']}",
        "query": wechat_msg.get("Content"),
        "metadata": {
            "msg_type": wechat_msg.get("MsgType"),
            "user_id": wechat_msg.get("FromUserName")
        }
    }

def custom_response_mapper(external_resp: Dict) -> Dict:
    """自定义响应解析（需用户实现）"""
    return {
        "msg_type": external_resp.get("msg_type", "text"),
        "content": external_resp.get("text", "未识别响应格式")
    }