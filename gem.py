import requests
import time
import json
import re
import base64

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8767299908:AAE9jRtD2Buo2OiT0HL-QLsPrdD88FvHQ38"
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def ask_gemini(text_query=None, image_bytes=None):
    """Версия с жестко прописанным путем v1 для стабильности"""
    # Используем v1 — это самая стабильная точка входа сейчас
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = (
        "Ты — эксперт Avito. Определи точную модель товара и его цену на б/у рынке РФ. "
        "Ответ дай СТРОГО в формате JSON. "
        "Формат: {\"name\": \"название\", \"description\": \"хар-ки\", \"avg_price\": \"цена руб\", \"advice\": \"совет\"}"
    )

    parts = [{"text": system_instruction}]
    if text_query:
        parts.append({"text": f"Объект для оценки: {text_query}"})
    if image_bytes:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        })
    
    payload = {"contents": [{"parts": parts}]}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        res_data = response.json()
        
        # Если всё равно ошибка 'not found', пробуем экстренный метод (v1beta с другим префиксом)
        if 'error' in res_data and res_data['error'].get('code') == 404:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            res_data = response.json()

        if 'error' in res_data:
            return {"error_mode": True, "message": res_data['error'].get('message', 'API Error')}
            
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Поиск JSON в ответе
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            # Чистим от переносов, которые ломают парсинг
            clean_json = match.group().replace('\n', ' ').replace('\r', ' ')
            return json.loads(clean_json)
        
        return {"error_mode": True, "message": "Нейросеть ответила в неверном формате."}
        
    except Exception as e:
        return {"error_mode": True, "message": f"Ошибка системы: {str(e)}"}

def send_tg(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    last_id = 0
    print("🚀 SmartSell Pro запущен на стабильной версии v1")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": last_id + 1, "timeout": 20}).json()
            
            for update in res.get('result', []):
                last_id = update['update_id']
                msg = update.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']

                if msg.get('photo'):
                    send_tg(chat_id, "📸 Изучаю фото товара...")
                    file_id = msg['photo'][-1]['file_id']
                    f_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
                    img_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{f_info['result']['file_path']}").content
                    data = ask_gemini(text_query=msg.get('caption'), image_bytes=img_data)
                elif msg.get('text'):
                    if msg['text'] == '/start':
                        send_tg(chat_id, "Привет! Пришли фото или название товара, я оценю его.")
                        continue
                    send_tg(chat_id, "🔍 Считаю среднюю цену...")
                    data = ask_gemini(text_query=msg['text'])

                if data:
                    if data.get('error_mode'):
                        send_tg(chat_id, f"⚠️ *Ошибка:* {data.get('message')}")
                    else:
                        res_msg = (
                            f"📦 *{data.get('name')}*\n\n"
                            f"📝 {data.get('description')}\n\n"
                            f"💰 *Цена на Avito:* {data.get('avg_price')}\n"
                            f"💡 *Совет:* {data.get('advice')}"
                        )
                        send_tg(chat_id, res_msg)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
