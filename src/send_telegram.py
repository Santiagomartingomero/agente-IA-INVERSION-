"""
Envía un mensaje al bot de Telegram ya existente de Santiago.

Requiere variables de entorno:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
"""

import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_message(text: str, parse_mode: str = "Markdown"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID como variables de entorno."
        )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Telegram limita mensajes a 4096 caracteres; se trocea si hace falta.
    max_len = 4000
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)] or [text]

    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
        }
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()


if __name__ == "__main__":
    send_message("✅ Test de conexión — agente de cartera IA operativo.")
