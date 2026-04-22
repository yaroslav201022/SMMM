import requests
import time
import json
import re
import base64

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8767299908:AAE9jRtD2Buo2OiT0HL-QLsPrdD88FvHQ38"
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def ask_gemini(text_query=None, image_bytes=None):
    """Максимально упрощенная версия запроса"""
    # Если flash не находится, пробуем вызвать её через v1beta без префиксов
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "Ты эксперт Avito. Оцени товар. Верни ТОЛЬКО JSON: {\"name\": \"...\", \"description\": \"...\", \"avg_price\": \"...\", \"advice\": \"...\"}"},
                {"text": f"Запрос: {text_query if text_query else 'Оцени товар на фото'}"}
            ]
        }]
    }

    if image_bytes:
        payload["contents"][0]["parts"].append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        })

    try:
        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()
        
        # Если снова ошибка 404, пробуем альтернативную модель (Pro)
        if 'error' in res_data and 'not found' in res_data['error'].get('message', '').lower():
            url = url.replace('gemini-1.5-flash', 'gemini-1.5-pro')
            response = requests.post(url, json=payload, timeout=30)
            res_data = response.json()

        if 'error' in res_data:
            return {"error_mode": True, "message": res_data['error'].get('message')}

        text = res_data['candidates'][0]['content']['parts'][0]['text']
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group().replace('\n', ' '))
        return None
    except Exception as e:
        return {"error_mode": True, "message": str(e)}

def send_tg(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    last_id = 0
    print("🚀 Бот запущен. Ожидание...")
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", params={"offset": last_id + 1, "timeout": 20}).json()
            for update in res.get('result', []):
                last_id = update['update_id']
                msg = update.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']

                if msg.get('photo'):
                    send_tg(chat_id, "📸 Смотрю на фото...")
                    f_id = msg['photo'][-1]['file_id']
                    f_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={f_id}").json()
                    img = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{f_info['result']['file_path']}").content
                    data = ask_gemini(text_query=msg.get('caption'), image_bytes=img)
                elif msg.get('text'):
                    if msg['text'] == '/start':
                        send_tg(chat_id, "Привет! Пришли фото или название.")
                        continue
                    send_tg(chat_id, "🔍 Считаю...")
                    data = ask_gemini(text_query=msg['text'])

                if data:
                    if data.get('error_mode'):
                        send_tg(chat_id, f"⚠️ *Ошибка:* {data['message']}")
                    else:
                        m = f"📦 *{data.get('name')}*\n\n{data.get('description')}\n\n💰 *Цена:* {data.get('avg_price')}\n💡 *Совет:* {data.get('advice')}"
                        send_tg(chat_id, m)
        except:
            time.sleep(3)

if __name__ == "__main__":
    main()
