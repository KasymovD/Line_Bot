import os
import json
import base64
import hmac
import hashlib
import requests
from flask import Flask, request, abort, Response
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)

def load_env_variables():
    channel_secret = os.environ.get('CHANNEL_SECRET', '')
    channel_access_token = os.environ.get('CHANNEL_ACCESS_TOKEN', '')
    encryption_key_str = os.environ.get('ENCRYPTION_KEY', '')
    if not channel_secret or not channel_access_token or not encryption_key_str:
        raise ValueError('One or more required environment variables are missing.')
    encryption_key = encryption_key_str.encode('utf-8')
    if len(encryption_key) not in (16, 24, 32):
        raise ValueError('ENCRYPTION_KEY must be 16, 24, or 32 bytes long.')
    return channel_secret, channel_access_token, encryption_key

CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN, ENCRYPTION_KEY = load_env_variables()

def verify_line_signature(body_bytes, signature_header):
    hmac_digest = hmac.new(CHANNEL_SECRET.encode('utf-8'), body_bytes, hashlib.sha256).digest()
    calculated_signature = base64.b64encode(hmac_digest).decode('utf-8')
    result = hmac.compare_digest(calculated_signature, signature_header)
    return result

def encrypt_text(plain_text):
    iv = os.urandom(16)
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
    padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
    cipher_text = cipher.encrypt(padded_text)
    combined = iv + cipher_text
    encoded = base64.b64encode(combined).decode('utf-8')
    return encoded

def send_reply(reply_token, original_text):
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
    response = requests.post(url, headers=headers, data=json.dumps(message_data))
    if response.status_code != 200:
        raise Exception(f'Error from LINE API: {response.status_code} {response.text}')
    return response

def process_event(event):
    if 'type' not in event:
        return
    if event['type'] != 'message':
        return
    if 'replyToken' not in event:
        return
    reply_token = event['replyToken']
    message = event.get('message', {})
    if 'type' not in message:
        return
    if message['type'] != 'text':
        return
    text_content = message.get('text', '')
    send_reply(reply_token, text_content)

def handle_events(events):
    if not isinstance(events, list):
        return
    for event in events:
        process_event(event)

@app.route('/callback', methods=['POST'])
def callback():
    request_body = request.get_data()
    signature = request.headers.get('X-Line-Signature', '')
    if not verify_line_signature(request_body, signature):
        abort(400)
    try:
        body_dict = json.loads(request_body.decode('utf-8'))
    except Exception as e:
        abort(400)
    events = body_dict.get('events')
    if events is None:
        abort(400)
    handle_events(events)
    return Response(status=200)

def main():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
