import os
import re
import logging
from urllib.parse import urlparse

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    StickerMessage, StickerSendMessage
)
import openai
from googletrans import Translator
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка базового логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask-приложения
app = Flask(__name__)

# Получение токенов и ключей API из переменных окружения
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not (LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET and OPENAI_API_KEY):
    logger.error("Один или несколько ключей/токенов не заданы!")
    exit(1)

# Инициализация API Line и OpenAI
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# Инициализация переводчика
translator = Translator()


@app.route("/callback", methods=['POST'])
def callback():
    """Обработчик входящих запросов от сервера LINE."""
    signature = request.headers.get('X-Line-Signature', None)
    body = request.get_data(as_text=True)
    logger.info(f"Request body: {body}")
    
    if signature is None:
        logger.warning("Нет X-Line-Signature в заголовках!")
        abort(400)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.exception("Неверная подпись!")
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """Обработка текстовых сообщений от пользователей."""
    user_message = event.message.text.strip()
    reply = "Не удалось обработать запрос."  # Значение по умолчанию
    
    # Команда перевода: /translate <язык> <текст>
    translate_match = re.match(r'^/translate\s+(\w{2})\s+(.+)', user_message, re.IGNORECASE)
    if translate_match:
        dest_lang = translate_match.group(1)
        text_to_translate = translate_match.group(2)
        translation = translate_text(text_to_translate, dest_language=dest_lang)
        reply = f"Перевод ({dest_lang}): {translation}"
    
    # Команда парсинга сайта: /parse <URL>
    elif (parse_match := re.match(r'^/parse\s+(.+)', user_message, re.IGNORECASE)):
        url = parse_match.group(1)
        parsed_content = parse_website(url)
        if parsed_content:
            # Ограничиваем длину ответа
            reply = f"Содержимое <{url}>:\n{parsed_content[:1000]}..."
        else:
            reply = "Не удалось спарсить содержимое сайта."
    
    # Команда обращения к OpenAI: /ask <вопрос>
    elif (ask_match := re.match(r'^/ask\s+(.+)', user_message, re.IGNORECASE)):
        question = ask_match.group(1)
        ai_response = ask_openai(question)
        reply = ai_response
    
    # Если не найдено ни одной специфической команды, отправляем сообщение в OpenAI
    else:
        ai_response = ask_openai(user_message)
        reply = ai_response

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    except Exception as e:
        logger.exception(f"Ошибка при отправке ответа: {e}")


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    """Пересылаем стикеры обратно пользователю."""
    try:
        line_bot_api.reply_message(
            event.reply_token,
            StickerSendMessage(
                package_id=event.message.package_id,
                sticker_id=event.message.sticker_id
            )
        )
    except Exception as e:
        logger.exception(f"Ошибка при обработке стикера: {e}")


def translate_text(text, dest_language='ru'):
    """Перевод текста с помощью googletrans."""
    try:
        result = translator.translate(text, dest=dest_language)
        return result.text
    except Exception as e:
        logger.exception(f"Ошибка при переводе текста: {e}")
        return "Произошла ошибка при переводе."


def is_valid_url(url):
    """Базовая проверка валидности URL."""
    parsed = urlparse(url)
    return all([parsed.scheme in ('http', 'https'), parsed.netloc])


def parse_website(url):
    """Парсит содержимое сайта, извлекая текст из тегов <p>."""
    if not is_valid_url(url):
        logger.warning(f"Некорректный URL: {url}")
        return None

    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = '\n'.join(para.get_text(strip=True) for para in paragraphs if para.get_text(strip=True))
        return text
    except Exception as e:
        logger.exception(f"Ошибка при парсинге сайта {url}: {e}")
        return None


def ask_openai(prompt):
    """Получает ответ от OpenAI с использованием модели GPT-4."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты помогающий ассистент."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        ai_reply = response.choices[0].message['content'].strip()
        return ai_reply
    except Exception as e:
        logger.exception(f"Ошибка при обращении к OpenAI: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса."


if __name__ == "__main__":
    # Запуск Flask-приложения
    app.run(host='0.0.0.0', port=5000)
