import os

class Config:
    WECHAT_TOKEN = os.getenv('WECHAT_TOKEN', 'your_token')
    WECHAT_AES_KEY = os.getenv('WECHAT_AES_KEY', 'your_aes_key')
    WECHAT_APPID = os.getenv('WECHAT_APPID', 'your_appid')
    WECHAT_APPSECRET = os.getenv('WECHAT_APPSECRET', 'your_appsecret')
    EXTERNAL_SERVICE_URL = os.getenv('EXTERNAL_SERVICE_URL', 'http://default-service/api/wechat')
    EXTERNAL_SERVICE_TIMEOUT = int(os.getenv('EXTERNAL_SERVICE_TIMEOUT', 5))
    EXTERNAL_SERVICE_TYPE = os.getenv('EXTERNAL_SERVICE_TYPE', 'default').lower()
