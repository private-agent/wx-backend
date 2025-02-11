import base64
import binascii
import hashlib
import random
import string
import time
from Crypto.Cipher import AES
from app.utils.logger import logger

class WeChatCrypto:
    def __init__(self, token, encoding_aes_key, app_id):
        self.token = token
        self.app_id = app_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        self.iv = self.aes_key[:16]
        logger.info('WeChatCrypto initialized')

    def _create_cipher(self):
        """创建新的cipher实例"""
        return AES.new(self.aes_key, AES.MODE_CBC, self.iv)

    def check_signature(self, signature, timestamp, nonce):
        """验证消息签名"""
        params = sorted([self.token, timestamp, nonce])
        sha1 = hashlib.sha1(''.join(params).encode()).hexdigest()
        is_valid = sha1 == signature
        if not is_valid:
            logger.warning(f'Invalid signature: expected={sha1}, received={signature}')
        return is_valid

    def decrypt_message(self, encrypted_msg, signature, timestamp, nonce):
        """解密微信消息（新增签名验证）"""
        # 先验证消息签名
        if not self.check_signature(signature, timestamp, nonce):
            raise ValueError("Invalid message signature")

        try:
            # 确保输入是字符串
            if isinstance(encrypted_msg, bytes):
                encrypted_msg = encrypted_msg.decode('utf-8')
            elif not isinstance(encrypted_msg, str):
                logger.error(f'Invalid input type: {type(encrypted_msg)}')
                raise ValueError('Encrypted message must be a string')

            # 移除CDATA包装（如果存在）
            encrypted_msg = encrypted_msg.replace('<![CDATA[', '').replace(']]>', '')

            logger.debug(f'Encrypted message after preprocessing: {encrypted_msg}')

            # 处理base64填充
            pad_length = len(encrypted_msg) % 4
            if pad_length:
                encrypted_msg += '=' * (4 - pad_length)

            # 解密
            cipher = self._create_cipher()
            decrypted = cipher.decrypt(base64.b64decode(encrypted_msg))

            # 去除PKCS7填充
            pad = decrypted[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted[:-pad]

            # 解析解密后的内容
            # content = random(16B) + msg_len(4B) + msg + appid
            msg_len = int.from_bytes(content[16:20], byteorder='big')
            xml_content = content[20:20+msg_len].decode('utf-8')

            logger.debug(f'Message length from bytes: {msg_len}')
            logger.debug(f'Extracted XML content: {xml_content}')

            return xml_content

        except binascii.Error as e:
            logger.error(f'Base64 decoding error: {str(e)}', exc_info=True)
            raise
        except Exception as e:
            logger.error(f'Failed to decrypt message: {str(e)}', exc_info=True)
            raise

    def encrypt_message(self, reply_msg, nonce):
        """加密回复消息（新增nonce参数）"""
        try:
            # 生成16字节的随机字符串
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

            # 计算消息长度，转换为网络字节序(big-endian)
            msg_len = len(reply_msg.encode())
            msg_len_bytes = msg_len.to_bytes(4, byteorder='big')

            # 拼接明文: random(16B) + msg_len(4B) + msg + appid
            text = random_str.encode() + msg_len_bytes + reply_msg.encode() + self.app_id.encode()

            # PKCS7 填充
            block_size = 32
            amount_to_pad = block_size - (len(text) % block_size)
            if amount_to_pad == 0:
                amount_to_pad = block_size
            pad = chr(amount_to_pad)
            padded_text = text + (pad * amount_to_pad).encode()

            # 使用新的cipher实例进行加密
            cipher = self._create_cipher()
            encrypted = base64.b64encode(cipher.encrypt(padded_text))

            logger.debug(f'Random str: {random_str}')
            logger.debug(f'Message length: {msg_len}')
            logger.debug(f'Padded text length: {len(padded_text)}')
            logger.debug('Message encrypted successfully')

            return encrypted.decode('utf-8')

        except Exception as e:
            logger.error(f'Failed to encrypt message: {str(e)}', exc_info=True)
            raise

    def generate_signature(self, encrypted_msg, timestamp, nonce):
        """生成消息签名"""
        params = sorted([self.token, timestamp, nonce, encrypted_msg])
        return hashlib.sha1(''.join(params).encode()).hexdigest()