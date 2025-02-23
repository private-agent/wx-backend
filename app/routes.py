from flask import request, current_app
from app.wechat.crypto import WeChatCrypto
from app.wechat.handler import MessageHandler
from app.utils.logger import logger
from app.wechat.external_service import ExternalServiceAdapter, default_request_mapper, default_response_mapper, AsyncResponseHandler, openai_request_mapper, openai_response_mapper, ollama_request_mapper, ollama_response_mapper, custom_request_mapper, custom_response_mapper
import time
import xml.etree.ElementTree as ET
import random
import string

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
    external_adapter = ExternalServiceAdapter(async_handler, timeout=app.config['EXTERNAL_SERVICE_TIMEOUT'])

    @app.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        # 公共参数获取
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        msg_signature = request.args.get('msg_signature', '')
        encrypt_type = request.args.get('encrypt_type', 'raw')  # 新增加密类型判断

        # 验证签名逻辑
        if request.method == 'GET':
            echo_str = request.args.get('echostr', '')
            if crypto.check_signature(signature, timestamp, nonce):
                return echo_str
            return 'Verification failed', 403

        # 处理POST消息
        try:
            # 根据加密类型处理消息
            xml_str = request.data
            logger.debug(f'Raw request data (str): {xml_str}')
            logger.debug(f'Raw request data (hex): {xml_str.hex()}')

            # 判断消息模式
            is_encrypted = 'encrypt_type' in request.args or 'aes' in request.args.values()
            if is_encrypted:
                # 先解析XML获取Encrypt字段
                try:
                    xml_tree = ET.fromstring(xml_str)
                    encrypt_node = xml_tree.find('Encrypt')
                    if encrypt_node is None:
                        raise ValueError("No Encrypt field in XML")
                    encrypted_msg = encrypt_node.text
                except ET.ParseError as e:
                    logger.error(f"Failed to parse XML: {str(e)}")
                    return 'Invalid XML', 400

                # 加密消息处理
                decrypted_xml = crypto.decrypt_message(
                    encrypted_msg,  # 传入Encrypt字段的内容
                    signature,
                    timestamp,
                    nonce
                )
                msg = MessageHandler.parse_message(decrypted_xml)
            else:
                # 明文消息处理
                msg = MessageHandler.parse_message(xml_str)

            # 检查access_token状态
            if not app.token_manager.access_token:
                error_msg = f"系统服务暂时不可用，请稍后再试。（access_token error: {app.token_manager.last_error}）"
                reply_data = {
                    'msg_type': 'text',
                    'content': error_msg,
                    'from_user': msg.get('ToUserName'),
                    'to_user': msg.get('FromUserName')
                }
                if is_encrypted:
                    reply_xml = MessageHandler.build_reply(**reply_data)
                    encrypted_reply = crypto.encrypt_message(reply_xml, nonce)
                    return encrypted_reply
                else:
                    return MessageHandler.build_reply(**reply_data)

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

            # 构建回复
            reply_content = "AI处理中..."  # 替换为实际回复内容
            reply_data = {
                'msg_type': 'text',
                'content': reply_content,
                'from_user': msg.get('ToUserName'),
                'to_user': msg.get('FromUserName')
            }

            # 根据加密模式返回不同格式
            if is_encrypted:
                reply_xml = MessageHandler.build_reply(**reply_data)
                encrypted_reply = crypto.encrypt_message(reply_xml, nonce)
                # 生成新的消息签名
                timestamp = str(int(time.time()))
                new_nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                msg_signature = crypto.generate_signature(encrypted_reply, timestamp, new_nonce)
                # 构建符合微信要求的加密消息结构
                encrypted_xml = f"""
                <xml>
                    <Encrypt><![CDATA[{encrypted_reply}]]></Encrypt>
                    <MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
                    <TimeStamp>{timestamp}</TimeStamp>
                    <Nonce><![CDATA[{new_nonce}]]></Nonce>
                </xml>
                """
                return encrypted_xml.strip()
            else:
                return MessageHandler.build_reply(**reply_data)

        except ValueError as e:
            logger.error(f"签名验证失败: {str(e)}")
            return 'Invalid signature', 403
        except ET.ParseError as e:
            logger.error(f"XML解析错误: {str(e)}")
            return 'XML parse error', 400
