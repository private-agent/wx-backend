import os

class Config:
    WECHAT_TOKEN = os.getenv('WECHAT_TOKEN', 'your_token')
    WECHAT_AES_KEY = os.getenv('WECHAT_AES_KEY', 'your_aes_key')
    WECHAT_APPID = os.getenv('WECHAT_APPID', 'your_appid')