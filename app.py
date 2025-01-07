import os
import re
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage
import openai
from googletrans import Translator
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY
translator = Translator()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_message = event.message.text
    match = re.match(r'^/translate\s+(\w{2})\s+(.+)', user_message, re.IGNORECASE)
    if match:
        dest_lang = match.group(1)
        text_to_translate = match.group(2)
        translation = translate_text(text_to_translate, dest_language=dest_lang)
        reply = f"Перевод ({dest_lang}): {translation}"
    else:
        match = re.match(r'^/parse\s+(.+)', user_message, re.IGNORECASE)
        if match:
            url = match.group(1)
            parsed_content = parse_website(url)
            if parsed_content:
                reply = f"Содержимое <{url}>:\n{parsed_content[:1000]}..."
            else:
                reply = "Не удалось спарсить содержимое сайта."
        else:
            match = re.match(r'^/ask\s+(.+)', user_message, re.IGNORECASE)
            if match:
                question = match.group(1)
                ai_response = ask_openai(question)
                reply = ai_response
            else:
                ai_response = ask_openai(user_message)
                reply = ai_response
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id
        )
    )

def translate_text(text, dest_language='ru'):
    try:
        result = translator.translate(text, dest=dest_language)
        return result.text
    except Exception:
        return "Произошла ошибка при переводе."

def parse_website(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = '\n'.join([para.get_text(strip=True) for para in paragraphs])
        return text
    except Exception:
        return None

def ask_openai(prompt):
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
    except Exception:
        return "Извините, произошла ошибка при обработке вашего запроса."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
