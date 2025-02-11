import time
import requests
from threading import Lock
from app.utils.logger import logger

class TokenManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.access_token = None
        self.expires_at = 0
        self.last_error = None
        self.retry_count = 0
        self.max_retries = 3
        self.lock = Lock()

    def get_token(self, appid, appsecret):
        """获取当前有效的access_token"""
        if time.time() < self.expires_at - 300:  # 提前5分钟刷新
            return self.access_token
        return self.refresh_token(appid, appsecret)

    def refresh_token(self, appid, appsecret):
        """主动刷新access_token"""
        with self.lock:
            url = "https://api.weixin.qq.com/cgi-bin/token"
            params = {
                "grant_type": "client_credential",
                "appid": appid,
                "secret": appsecret
            }

            for attempt in range(self.max_retries):
                try:
                    response = requests.get(url, params=params, timeout=5)
                    data = response.json()

                    if 'access_token' in data:
                        self.access_token = data['access_token']
                        self.expires_at = time.time() + data['expires_in']
                        self.retry_count = 0
                        logger.info(f"Access token刷新成功，有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.expires_at))}")
                        return self.access_token

                    # 错误处理逻辑
                    errcode = data.get('errcode', -1)
                    errmsg = data.get('errmsg', 'unknown error')
                    self.last_error = f"{errcode}: {errmsg}"

                    if errcode == -1:  # 系统繁忙
                        wait = 2 ** attempt
                        logger.warning(f"系统繁忙，{wait}秒后重试。错误信息: {errmsg}")
                        time.sleep(wait)
                        continue

                    if errcode == 40164:  # IP白名单错误
                        logger.error(f"IP未在白名单中，请登录微信公众平台配置。错误信息: {errmsg}")
                        break

                    if errcode == 89503:  # 需要管理员确认
                        logger.critical("需要管理员在微信公众平台确认此IP的调用权限")
                        break

                    logger.error(f"获取access_token失败: {errmsg}")
                    break

                except requests.exceptions.RequestException as e:
                    logger.error(f"网络请求异常: {str(e)}")
                    self.last_error = str(e)
                    time.sleep(1)

            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                logger.critical("连续获取access_token失败，停止重试")
            return None