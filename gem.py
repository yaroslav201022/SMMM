import requests

# Вставь свой ключ сюда
GEMINI_API_KEY = "AIzaSyAySWwDp2fRPFEbMF1m3OOA15H7O2VnVR0"

def check_api():
    print("--- НАЧАЛО ТЕСТА API ---")
    
    # 1. Тестируем список доступных моделей
    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    
    try:
        print(f"Запрашиваю список моделей...")
        response = requests.get(models_url, timeout=15)
        data = response.json()
        
        if 'error' in data:
            print(f"❌ ОШИБКА ГУГЛА: {data['error'].get('message')}")
            print(f"Статус: {data['error'].get('status')}")
        else:
            print("✅ Ключ рабочий! Доступные модели:")
            models = [m['name'] for m in data.get('models', [])]
            for m in models:
                if "gemini-1.5" in m:
                    print(f"  > {m}")
            
            if not any("gemini-1.5-flash" in m for m in models):
                print("⚠ ВНИМАНИЕ: Модель gemini-1.5-flash не найдена в списке доступных для этого ключа.")

    except Exception as e:
        print(f"❌ ОШИБКА СОЕДИНЕНИЯ: {e}")

    print("--- КОНЕЦ ТЕСТА ---")

if __name__ == "__main__":
    check_api()
