import os
import json
import base64
import hmac
import hashlib
import logging
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, request, abort, Response
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def load_env_variables() -> (str, str, bytes):
    """
    Загружает необходимые переменные окружения и проводит базовую проверку.
    
    :return: Кортеж из CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN и ENCRYPTION_KEY.
    :raises ValueError: Если отсутствует один из обязательных параметров или ключ имеет неверную длину.
    """
    channel_secret = os.environ.get('CHANNEL_SECRET', '')
    channel_access_token = os.environ.get('CHANNEL_ACCESS_TOKEN', '')
    encryption_key_str = os.environ.get('ENCRYPTION_KEY', '')

    if not channel_secret or not channel_access_token or not encryption_key_str:
        msg = 'One or more required environment variables are missing.'
        logger.error(msg)
        raise ValueError(msg)

    encryption_key = encryption_key_str.encode('utf-8')
    if len(encryption_key) not in (16, 24, 32):
        msg = 'ENCRYPTION_KEY must be 16, 24, or 32 bytes long.'
        logger.error(msg)
        raise ValueError(msg)

    return channel_secret, channel_access_token, encryption_key


CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN, ENCRYPTION_KEY = load_env_variables()


def verify_line_signature(body_bytes: bytes, signature_header: str) -> bool:
    """
    Проверяет корректность подписи, полученной от LINE.

    :param body_bytes: Тело запроса в байтах.
    :param signature_header: Подпись из заголовка X-Line-Signature.
    :return: True, если подпись корректна, иначе False.
    """
    hmac_digest = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body_bytes,
        hashlib.sha256
    ).digest()
    calculated_signature = base64.b64encode(hmac_digest).decode('utf-8')
    valid = hmac.compare_digest(calculated_signature, signature_header)
    if not valid:
        logger.warning("Подпись не прошла валидацию.")
    return valid


def encrypt_text(plain_text: str) -> str:
    """
    Шифрует строку с использованием AES в режиме CBC.

    :param plain_text: Открытый текст.
    :return: Base64-кодированная строка, содержащая IV и зашифрованный текст.
    """
    iv = os.urandom(16)
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
    padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
    cipher_text = cipher.encrypt(padded_text)
    combined = iv + cipher_text
    encoded = base64.b64encode(combined).decode('utf-8')
    return encoded


def send_reply(reply_token: str, original_text: str) -> Optional[requests.Response]:
    """
    Отправляет зашифрованный ответ с помощью LINE Messaging API.

    :param reply_token: Токен для ответа.
    :param original_text: Исходный текст, который необходимо зашифровать и отправить.
    :return: Объект ответа от API, либо None при ошибке.
    :raises Exception: Если API возвращает ошибку.
    """
    encrypted = encrypt_text(original_text)
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
    }
    message_data = {
        'replyToken': reply_token,
        'messages': [
            {
                'type': 'text',
                'text': encrypted
            }
        ]
    }
    logger.info(f"Отправка ответа через LINE API: {message_data}")
    response = requests.post(url, headers=headers, data=json.dumps(message_data))
    if response.status_code != 200:
        msg = f'Error from LINE API: {response.status_code} {response.text}'
        logger.error(msg)
        raise Exception(msg)
    return response


def process_event(event: Dict[str, Any]) -> None:
    """
    Обрабатывает отдельное событие, если оно соответствует критериям.

    :param event: Словарь с данными события.
    """
    if event.get('type') != 'message':
        logger.debug("Событие не является сообщением, пропуск.")
        return

    reply_token = event.get('replyToken')
    if not reply_token:
        logger.debug("Нет replyToken в событии, пропуск.")
        return

    message = event.get('message', {})
    if message.get('type') != 'text':
        logger.debug("Сообщение не текстовое, пропуск.")
        return

    text_content = message.get('text', '')
    logger.info(f"Получено текстовое сообщение: {text_content}")
    try:
        send_reply(reply_token, text_content)
    except Exception as e:
        logger.exception(f"Ошибка при отправке ответа: {e}")


def handle_events(events: List[Dict[str, Any]]) -> None:
    """
    Обрабатывает список событий.

    :param events: Список событий, полученных от LINE API.
    """
    for event in events:
        process_event(event)


@app.route('/callback', methods=['POST'])
def callback() -> Response:
    """
    Точка входа для обработки запросов от LINE.
    Проверяет подпись запроса, парсит JSON и передаёт события на обработку.
    """
    request_body = request.get_data()
    signature = request.headers.get('X-Line-Signature', '')
    logger.debug(f"Получен запрос: {request_body}")

    if not verify_line_signature(request_body, signature):
        logger.error("Подпись не соответствует, прерывание обработки.")
        abort(400)

    try:
        body_dict = json.loads(request_body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
        abort(400)

    events = body_dict.get('events')
    if events is None:
        logger.error("Отсутствует ключ 'events' в запросе.")
        abort(400)

    handle_events(events)
    return Response(status=200)


def main() -> None:
    """
    Запускает Flask-приложение на указанном порту.
    """
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск приложения на порту {port}")
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
