import requests
import time
import json
import re
import base64

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8767299908:AAE9jRtD2Buo2OiT0HL-QLsPrdD88FvHQ38"
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def ask_gemini(text_query=None, image_bytes=None):
    """Запрос к Gemini с выводом технических ошибок в чат"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    system_instruction = (
        "Ты — эксперт-оценщик цен на Avito. Твоя задача: определить модель товара и его цену в РФ. "
        "Ответ дай СТРОГО в формате JSON: "
        "{\"name\": \"...\", \"description\": \"...\", \"avg_price\": \"...\", \"advice\": \"...\"}"
    )

    parts = [{"text": system_instruction}]
    if text_query:
        parts.append({"text": f"Запрос: {text_query}"})
    if image_bytes:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode('utf-8')
            }
        })
    
    try:
        response = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=30)
        res_data = response.json()
        
        # БЛОК ДИАГНОСТИКИ ОШИБОК
        if 'error' in res_data:
            err_msg = res_data['error'].get('message', 'Unknown error')
            print(f"Google API Error: {err_msg}")
            return {"error_mode": True, "message": f"Ошибка Google API: {err_msg}"}

        if 'candidates' not in res_data:
            return {"error_mode": True, "message": "Google не предложил вариантов ответа."}
            
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Извлекаем JSON
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group().replace('\n', ' '))
        
        return {"error_mode": True, "message": "Нейросеть ответила не в формате JSON."}
        
    except Exception as e:
        print(f"Ошибка связи: {e}")
        return {"error_mode": True, "message": f"Ошибка соединения: {str(e)}"}

def send_tg(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    last_id = 0
    print("🚀 SmartSell Pro запущен. Жду сообщений...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": last_id + 1, "timeout": 20}).json()
            
            for update in res.get('result', []):
                last_id = update['update_id']
                msg = update.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']

                # Если прислали ФОТО
                if msg.get('photo'):
                    send_tg(chat_id, "📸 Изучаю фото...")
                    file_id = msg['photo'][-1]['file_id']
                    f_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
                    img_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{f_info['result']['file_path']}").content
                    data = ask_gemini(text_query=msg.get('caption'), image_bytes=img_data)

                # Если прислали ТЕКСТ
                elif msg.get('text'):
                    if msg['text'] == '/start':
                        send_tg(chat_id, "Привет! Пришли фото или название товара.")
                        continue
                    send_tg(chat_id, "🔍 Анализирую...")
                    data = ask_gemini(text_query=msg['text'])

                # ОБРАБОТКА РЕЗУЛЬТАТА
                if data:
                    if data.get('error_mode'):
                        # Выводим техническую ошибку прямо пользователю
                        send_tg(chat_id, f"⚠️ *Техническая проблема:*\n{data.get('message')}")
                    else:
                        res_msg = (
                            f"📦 *{data.get('name')}*\n\n"
                            f"📝 {data.get('description')}\n\n"
                            f"💰 *Цена на Avito:* {data.get('avg_price')}\n"
                            f"💡 *Совет:* {data.get('advice')}"
                        )
                        send_tg(chat_id, res_msg)
                else:
                    send_tg(chat_id, "⚠️ Неизвестная ошибка. Попробуй еще раз.")

        except Exception as e:
            print(f"Ошибка цикла: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
