import requests
import time
import json
import re
import base64

# --- НАСТРОЙКИ ---
# Вставь свой токен от BotFather
TELEGRAM_TOKEN = "8767299908:AAE9jRtD2Buo2OiT0HL-QLsPrdD88FvHQ38"
# Вставь свой ключ от Google AI Studio (Gemini)
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def ask_gemini(text_query=None, image_bytes=None):
    """Отправка запроса в Gemini через прямой API (HTTP)"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # Инструкция для нейросети
    system_instruction = (
        "Ты — эксперт-оценщик Avito. Твоя задача: определить точную модель товара по фото или тексту "
        "и назвать его актуальную рыночную стоимость на вторичном рынке России (в рублях). "
        "Будь смелым в оценке, не пиши 'неизвестно'. Если данных мало, дай примерный диапазон цен. "
        "Ответ верни СТРОГО в формате JSON: "
        "{\"name\": \"название товара\", \"description\": \"характеристики и состояние\", \"avg_price\": \"цена в рублях\", \"advice\": \"совет по продаже\"}"
    )

    # Собираем данные запроса
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
        
        # Извлекаем текст ответа
        raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Очищаем текст от лишних символов, чтобы остался только чистый JSON
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return None

def send_tg(chat_id, text):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    last_update_id = 0
    print("🚀 SmartSell Pro (Gemini Edition) запущен!")
    
    while True:
        try:
            # Получаем обновления из Телеграм
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": last_update_id + 1, "timeout": 20}).json()
            
            for update in res.get('result', []):
                last_update_id = update['update_id']
                msg = update.get('message')
                if not msg: continue
                chat_id = msg['chat']['id']

                # Если пользователь прислал ФОТО
                if msg.get('photo'):
                    send_tg(chat_id, "📸 Смотрю на фото... ищу цены на Avito...")
                    
                    # Скачиваем самое качественное фото из сообщения
                    file_id = msg['photo'][-1]['file_id']
                    f_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
                    file_path = f_info['result']['file_path']
                    img_content = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}").content
                    
                    # Просим Gemini распознать и оценить
                    data = ask_gemini(text_query=msg.get('caption'), image_bytes=img_content)

                # Если пользователь прислал ТЕКСТ
                elif msg.get('text'):
                    user_text = msg['text']
                    if user_text == '/start':
                        send_tg(chat_id, "Привет! Пришли фото товара или его название, и я назову цену.")
                        continue
                    
                    send_tg(chat_id, "🔍 Анализирую рынок...")
                    data = ask_gemini(text_query=user_text)

                # Выводим результат в чат
                if data:
                    result_text = (
                        f"📦 *{data.get('name', 'Товар')}*\n\n"
                        f"{data.get('description', '')}\n\n"
                        f"💰 *Средняя цена:* {data.get('avg_price', 'Не определена')}\n"
                        f"💡 *Совет:* {data.get('advice', '-')}"
                    )
                    send_tg(chat_id, result_text)
                else:
                    # Если нейросеть не вернула JSON
                    if not msg.get('text') == '/start':
                        send_tg(chat_id, "⚠️ Не удалось оценить. Попробуй сделать фото четче или напиши название текстом.")

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()