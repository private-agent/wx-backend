from flask import Flask
from .config import Config
from .routes import init_routes
from .utils.logger import logger

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 记录应用启动日志
    logger.info('WeChat Backend Application Starting...')
    
    init_routes(app)
    return app