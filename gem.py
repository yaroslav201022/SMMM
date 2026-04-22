import requests
import time
import json
import re
import base64

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8767299908:AAE9jRtD2Buo2OiT0HL-QLsPrdD88FvHQ38"
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def ask_gemini(text_query=None, image_bytes=None):
    """Запрос к Gemini с улучшенной обработкой JSON"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = (
        "Ты — эксперт-оценщик Avito. Определи точную модель товара и назови его цену на б/у рынке РФ. "
        "Ответ дай СТРОГО в формате JSON без кавычек markdown и лишнего текста. "
        "ОБЯЗАТЕЛЬНО заполни все поля. Если не уверен в цене, дай диапазон (например, 20000-25000 руб). "
        "Формат: {\"name\": \"название\", \"description\": \"хар-ки\", \"avg_price\": \"цена руб\", \"advice\": \"совет\"}"
    )

    parts = [{"text": system_instruction}]
    if text_query:
        parts.append({"text": f"Запрос пользователя: {text_query}"})
    if image_bytes:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        })
    
    payload = {"contents": [{"parts": parts}]}

    try:
        response = requests.post(url, json=payload, timeout=30)
        res_data = response.json()
        
        # Проверка на ошибки в ответе API
        if 'candidates' not in res_data:
            print(f"Ошибка API: {res_data}")
            return None
            
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Регулярка для поиска JSON внутри любого текста
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            json_str = match.group()
            # Убираем возможные ошибки форматирования
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            return json.loads(json_str)
        
        print(f"Не удалось найти JSON в тексте: {raw_text}")
        return None
    except Exception as e:
        print(f"Критическая ошибка функции: {e}")
        return None

def send_tg(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    last_id = 0
    print("🚀 SmartSell Pro (Gemini) запущен и готов к работе!")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": last_id + 1, "timeout": 20}).json()
            
            for update in res.get('result', []):
                last_id = update['update_id']
                msg = update.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']

                # Если ФОТО
                if msg.get('photo'):
                    send_tg(chat_id, "📸 Изучаю товар по фото...")
                    file_id = msg['photo'][-1]['file_id']
                    f_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
                    img_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{f_info['result']['file_path']}").content
                    data = ask_gemini(text_query=msg.get('caption'), image_bytes=img_data)

                # Если ТЕКСТ
                elif msg.get('text'):
                    if msg['text'] == '/start':
                        send_tg(chat_id, "Привет! Пришли фото товара или его название. Я оценю его стоимость на Avito.")
                        continue
                    send_tg(chat_id, "🔍 Ищу похожие объявления...")
                    data = ask_gemini(text_query=msg['text'])

                # Результат
                if data:
                    res_msg = (
                        f"📦 *{data.get('name', 'Товар')}*\n\n"
                        f"📝 {data.get('description', '')}\n\n"
                        f"💰 *Средняя цена:* {data.get('avg_price', 'Не определена')}\n"
                        f"💡 *Совет:* {data.get('advice', '-')}"
                    )
                    send_tg(chat_id, res_msg)
                else:
                    if msg.get('text') != '/start':
                        send_tg(chat_id, "⚠️ Не удалось получить оценку. Попробуйте уточнить название или сделать другое фото.")

        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
