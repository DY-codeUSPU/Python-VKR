import os
import uuid
import requests
import urllib3
from flask import Flask, request, jsonify
from flask_cors import CORS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

GIGACHAT_AUTH_KEY = os.environ.get('GIGACHAT_AUTH_KEY')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# ── GigaChat: получение токена ──────────────────────────────

@app.route('/auth', methods=['POST'])
def get_token():
    if not GIGACHAT_AUTH_KEY:
        return jsonify(dict(error="ключ GigaChat не настроен на сервере")), 500

    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = {'scope': 'GIGACHAT_API_PERS'}
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False)
        return jsonify(response.json())
    except Exception as e:
        return jsonify(dict(error=str(e))), 500

# ── GigaChat: чат ───────────────────────────────────────────

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    token = data.get('token')
    messages = data.get('messages')
    if not token or not messages:
        return jsonify(dict(error="некорректные данные запроса")), 400

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {"model": "GigaChat", "messages": messages, "stream": False}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        return jsonify(response.json())
    except Exception as e:
        return jsonify(dict(error=str(e))), 500

# ── Gemini ──────────────────────────────────────────────────

@app.route('/yandex', methods=['POST'])
def yandex():
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return jsonify(dict(error="ключ YandexGPT не настроен на сервере")), 500

    data = request.json
    messages = data.get('messages')
    if not messages:
        return jsonify(dict(error="некорректные данные запроса")), 400

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Api-Key {YANDEX_API_KEY}',
        'x-folder-id': YANDEX_FOLDER_ID
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": [
            {"role": m["role"], "text": m["text"]}
            for m in messages
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        print("YandexGPT response:", result)
        if 'error' in result:
            return jsonify(dict(error=result['error'].get('message', 'Ошибка YandexGPT'))), 500
        text = result['result']['alternatives'][0]['message']['text']
        return jsonify({"text": text})
    except Exception as e:
        return jsonify(dict(error=str(e))), 500
# ── запуск ──────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
