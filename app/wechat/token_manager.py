import time
import requests
from threading import Lock
from app.utils.logger import logger
import os
import json
from flask import current_app

class TokenManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, token_file_path: str = None):
        if hasattr(self, '_initialized'):  # 防止重复初始化
            return

        self.access_token = None
        self.expires_at = 0
        self.last_error = None
        self.retry_count = 0
        self.max_retries = 3
        self.lock = Lock()
        self.token_file = token_file_path  # 通过参数传入路径
        self._load_from_file()
        self._initialized = True  # 标记已初始化

    def _load_from_file(self):
        """从文件加载token"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)

                    # 验证配置一致性
                    current_appid = current_app.config['WECHAT_APPID']
                    current_appsecret = current_app.config['WECHAT_APPSECRET']

                    # 检查appid和appsecret是否匹配（前3位验证）
                    file_appsecret_prefix = data.get('appsecret', '')[:3]
                    current_appsecret_prefix = current_appsecret[:3]

                    if (data.get('appid') != current_appid or
                        file_appsecret_prefix != current_appsecret_prefix):
                        logger.warning("配置信息变更，已存储的access_token失效")
                        return

                    # 检查有效期
                    if data['expires_at'] > time.time() + 300:
                        self.access_token = data['access_token']
                        self.expires_at = data['expires_at']
                        logger.info(f"从文件加载有效access_token，有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.expires_at))}")

        except Exception as e:
            logger.warning(f"加载token文件失败: {str(e)}")

    def _save_to_file(self):
        """保存token到文件"""
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump({
                    "access_token": self.access_token,
                    "expires_at": self.expires_at,
                    "appid": self.appid,
                    "appsecret": self.appsecret[:3] + "***"  # 安全记录
                }, f, indent=2)
        except Exception as e:
            logger.error(f"保存token文件失败: {str(e)}")

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
                        self.appid = appid
                        self.appsecret = appsecret
                        self._save_to_file()
                        self.retry_count = 0
                        logger.info(f"Access token刷新成功，有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.expires_at))}")
                        return self.access_token

                    # 错误处理逻辑
                    errcode = data.get('errcode', -1)
                    errmsg = data.get('errmsg', 'unknown error')
                    self.last_error = f"{errcode}: {errmsg}"

                    if errcode == -1:  # 系统繁忙
                        wait = 2 ** attempt
                        logger.warning(f"系统繁忙，{wait}秒后重试。错误信息: {errcode} {errmsg}")
                        time.sleep(wait)
                        continue

                    if errcode == 40164:  # IP白名单错误
                        logger.error(f"IP未在白名单中，请登录微信公众平台配置。错误信息: {errcode} {errmsg}")
                        break

                    if errcode == 89503:  # 需要管理员确认
                        logger.critical(f"{errcode} 需要管理员在微信公众平台确认此IP的调用权限")
                        break

                    logger.error(f"获取access_token失败: {errcode} {errmsg}")
                    break

                except requests.exceptions.RequestException as e:
                    logger.error(f"网络请求异常: {str(e)}")
                    self.last_error = str(e)
                    time.sleep(1)

            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                logger.critical("连续获取access_token失败，停止重试")
            return None