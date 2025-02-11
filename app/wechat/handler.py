from xml.etree import ElementTree as ET
import time
import logging
from app.utils.logger import logger
from typing import Union

class MessageHandler:
    @classmethod
    def parse_message(cls, xml_data: Union[bytes, str]) -> dict:
        """支持解析加密和明文两种格式"""
        try:
            if isinstance(xml_data, bytes):
                xml_str = xml_data.decode('utf-8')
            else:
                xml_str = xml_data

            # 移除可能存在的CDATA包装
            xml_str = xml_str.replace('<![CDATA[', '').replace(']]>', '')
            root = ET.fromstring(xml_str)
            return {child.tag: child.text for child in root}
        except ET.ParseError as e:
            logger.error(f"XML解析错误: {str(e)}")
            return {}

    @classmethod
    def build_reply(cls, msg_type: str, content: str, from_user: str, to_user: str) -> str:
        """生成兼容明文/加密模式的回复"""
        create_time = str(int(time.time()))
        base_xml = f"""
        <xml>
            <ToUserName><![CDATA[{to_user}]]></ToUserName>
            <FromUserName><![CDATA[{from_user}]]></FromUserName>
            <CreateTime>{create_time}</CreateTime>
            <MsgType><![CDATA[{msg_type}]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>
        """
        return base_xml.strip()