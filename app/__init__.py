from flask import Flask
from .config import Config
from .routes import init_routes
from .utils.logger import logger

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 记录应用启动日志
    logger.info('WeChat Backend Application Starting...')

    # 初始化token管理器
    with app.app_context():
        from .wechat.token_manager import TokenManager
        token_manager = TokenManager(app.config['TOKEN_FILE_PATH'])
        if not token_manager.access_token:
            token_manager.refresh_token(
                app.config['WECHAT_APPID'],
                app.config['WECHAT_APPSECRET']
            )

    init_routes(app)
    return app