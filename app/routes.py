import logging
from flask import request, current_app, make_response
from app.wechat.crypto import WeChatCrypto
from app.wechat.handler import MessageHandler
from app.utils.logger import logger

def init_routes(app):
    crypto = WeChatCrypto(
        app.config['WECHAT_TOKEN'],
        app.config['WECHAT_AES_KEY'],
        app.config['WECHAT_APPID']
    )

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
            
            # 构造回复内容
            reply_content = f'已收到：{msg.get("Content", "")}'
            reply_xml = MessageHandler.build_reply(
                msg_type='text',
                content=reply_content,
                from_user=msg.get('ToUserName'),  # 接收者变为发送者
                to_user=msg.get('FromUserName')   # 发送者变为接收者
            )
            logger.debug(f'Reply XML: {reply_xml}')
            
            # 加密回复
            encrypted_reply, timestamp, nonce = crypto.encrypt_message(reply_xml)
            logger.info(f'Sending encrypted reply to user: {msg.get("FromUserName")}')
            
            # 构造最终回复
            response = f"""<xml>
                <Encrypt><![CDATA[{encrypted_reply}]]></Encrypt>
                <MsgSignature>{crypto.generate_signature(encrypted_reply, timestamp, nonce)}</MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""
            
            return response.strip()
            
        except Exception as e:
            logger.error(f'Error processing message: {str(e)}', exc_info=True)
            return 'Internal Server Error', 500