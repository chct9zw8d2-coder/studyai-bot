
import os
import requests

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "60"))

SYSTEM_STUDY = """Ты StudyAI — помощник для школьников, студентов колледжей и университетов.
Отвечай по-русски. Структура: краткий вывод, затем подробности, затем примеры/шаги.
Для доклада/реферата: план + текст с подзаголовками + краткий список источников (типы источников).
Для задач: пошаговое решение (без скрытых рассуждений).
Для кода: рабочий код в ``` и краткие пояснения.
"""

def generate_text(prompt: str, mode: str = "study") -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    system = SYSTEM_STUDY
    if mode == "fun":
        system = "Ты дружелюбный и остроумный ассистент. Пиши коротко, смешно и безопасно."
    elif mode == "essay":
        system = SYSTEM_STUDY + "\nПиши более академично и связно."
    elif mode == "code":
        system = SYSTEM_STUDY + "\nТы опытный программист. Пиши корректный код."
    elif mode == "explain":
        system = SYSTEM_STUDY + "\nОбъясняй максимально простыми словами."

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
    }

    r = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or str(data)
