from xml.etree import ElementTree as ET
import time
import logging
from app.utils.logger import logger

class MessageHandler:
    @staticmethod
    def parse_message(xml_data):
        """解析微信XML消息"""
        try:
            # 移除可能存在的XML声明
            if xml_data.startswith('<?xml'):
                xml_data = xml_data[xml_data.find('?>')+2:]

            # 移除前后的空白字符
            xml_data = xml_data.strip()

            logger.debug(f'Parsing XML: {xml_data}')

            # 解析XML
            data = ET.fromstring(xml_data)
            result = {}

            # 遍历所有子元素
            for child in data:
                if child.text is not None:
                    result[child.tag] = child.text.strip()
                else:
                    result[child.tag] = ''

            logger.debug(f'Parsed message: {result}')
            return result

        except ET.ParseError as e:
            logger.error(f'XML parsing error: {str(e)}\nXML content: {xml_data}')
            raise
        except Exception as e:
            logger.error(f'Message parsing error: {str(e)}\nXML content: {xml_data}')
            raise

    @staticmethod
    def build_reply(msg_type, content, from_user, to_user):
        """支持多种消息类型的回复构造"""
        base_xml = f"""<xml>
            <ToUserName><![CDATA[{to_user}]]></ToUserName>
            <FromUserName><![CDATA[{from_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[{msg_type}]]></MsgType>"""

        if msg_type == 'text':
            base_xml += f"<Content><![CDATA[{content}]]></Content>"
        elif msg_type == 'image':
            base_xml += f"<Image><MediaId><![CDATA[{content}]]></MediaId></Image>"
        # 可扩展其他消息类型

        base_xml += "</xml>"
        return base_xml.strip()