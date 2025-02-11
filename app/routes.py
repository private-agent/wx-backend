import logging
from flask import request, current_app, make_response
from app.wechat.crypto import WeChatCrypto
from app.wechat.handler import MessageHandler
from app.utils.logger import logger
from app.wechat.external_service import ExternalServiceAdapter, default_request_mapper, default_response_mapper, AsyncResponseHandler, openai_request_mapper, openai_response_mapper, ollama_request_mapper, ollama_response_mapper, custom_request_mapper, custom_response_mapper
from app.wechat.token_manager import TokenManager
import time

def init_routes(app):
    crypto = WeChatCrypto(
        app.config['WECHAT_TOKEN'],
        app.config['WECHAT_AES_KEY'],
        app.config['WECHAT_APPID']
    )

    async_handler = AsyncResponseHandler(
        app.token_manager,
        appid=app.config['WECHAT_APPID'],
        appsecret=app.config['WECHAT_APPSECRET']
    )
    external_adapter = ExternalServiceAdapter(async_handler)

    @app.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        # 验证签名
        if request.method == 'GET':
            signature = request.args.get('signature', '')
            timestamp = request.args.get('timestamp', '')
            nonce = request.args.get('nonce', '')
            echostr = request.args.get('echostr', '')

            logger.info(f'Receiving verification request: signature={signature}, timestamp={timestamp}, nonce={nonce}')

            if crypto.check_signature(signature, timestamp, nonce):
                logger.info('Signature verification successful')
                return echostr
            logger.warning('Signature verification failed')
            return 'Verification Failed', 403

        # 处理消息
        try:
            encrypted_xml = request.data
            logger.debug(f'Raw request data (str): {encrypted_xml}')
            logger.debug(f'Raw request data (hex): {encrypted_xml.hex() if isinstance(encrypted_xml, bytes) else None}')

            # 检查是否为加密消息
            if not encrypted_xml:
                logger.error('Empty request data')
                return 'Empty Request', 400

            # 解析XML获取加密内容
            try:
                from xml.etree import ElementTree as ET
                xml_tree = ET.fromstring(encrypted_xml)
                encrypt_elem = xml_tree.find('Encrypt')
                if encrypt_elem is None:
                    logger.error('No Encrypt field in XML')
                    return 'Invalid Format', 400
                encrypted_msg = encrypt_elem.text
                logger.debug(f'Extracted encrypted message: {encrypted_msg}')
            except ET.ParseError as e:
                logger.error(f'Failed to parse XML: {str(e)}')
                return 'Invalid XML', 400

            # 解密消息
            decrypted_xml = crypto.decrypt_message(encrypted_msg)
            logger.debug(f'Decrypted XML: {decrypted_xml}')

            # 解析消息内容
            msg = MessageHandler.parse_message(decrypted_xml)
            logger.info(f'Parsed message: type={msg.get("MsgType")}, from={msg.get("FromUserName")}')

            # 检查access_token状态
            if not app.token_manager.access_token:
                error_msg = f"系统服务暂时不可用，请稍后再试。（access_token error: {app.token_manager.last_error}）"
                reply_xml = MessageHandler.build_reply(
                    msg_type='text',
                    content=error_msg,
                    from_user=msg.get('ToUserName'),
                    to_user=msg.get('FromUserName')
                )
                return reply_xml

            # 在调用外部服务前添加分发逻辑
            service_type = current_app.config['EXTERNAL_SERVICE_TYPE']

            # 定义服务类型映射表
            service_mappers = {
                'default': (default_request_mapper, default_response_mapper),
                'openai': (openai_request_mapper, openai_response_mapper),
                'ollama': (ollama_request_mapper, ollama_response_mapper),
                'custom': (custom_request_mapper, custom_response_mapper)
            }

            # 获取对应的映射器
            req_mapper, resp_mapper = service_mappers.get(
                service_type,
                (default_request_mapper, default_response_mapper)
            )

            # 调用服务时使用动态映射器
            external_response = external_adapter.call_service(
                wechat_msg=msg,
                endpoint=current_app.config['EXTERNAL_SERVICE_URL'],
                request_mapper=req_mapper,
                response_mapper=resp_mapper,
                openid=msg.get('FromUserName')
            )

            # 无论是否有响应都先返回success
            logger.info("Returning success immediately")
            return 'success'

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return 'success' if isinstance(e, TimeoutError) else 'Internal Server Error', 500
