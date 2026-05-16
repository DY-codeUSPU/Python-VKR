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

@app.route('/gemini', methods=['POST'])
def gemini():
    if not GEMINI_API_KEY:
        return jsonify(dict(error="ключ Gemini не настроен на сервере")), 500

    data = request.json
    messages = data.get('messages')
    if not messages:
        return jsonify(dict(error="некорректные данные запроса")), 400

    contents = [
        {"role": m["role"], "parts": [{"text": m["text"]}]}
        for m in messages
    ]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        response = requests.post(url, json={"contents": contents})
        result = response.json()

        # логируем полный ответ для отладки
        print("Gemini response:", result)

        # проверяем наличие candidates
        if 'error' in result:
            return jsonify(dict(error=result['error'].get('message', 'Ошибка Gemini'))), 500
        
        candidates = result.get('candidates', [])
        if not candidates:
            return jsonify(dict(error=f"Gemini не вернул ответ. Полный ответ: {result}")), 500

        text = candidates[0]['content']['parts'][0]['text']
        return jsonify({"text": text})

    except Exception as e:
        return jsonify(dict(error=str(e))), 500

# ── запуск ──────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
