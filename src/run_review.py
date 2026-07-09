"""
Orquesta la revisión diaria de la cartera:
1. Lee state.json (posiciones, precios de entrada, última revisión).
2. Obtiene precios actuales (Yahoo Finance para acciones, CoinGecko para BTC).
3. Construye el prompt combinando prompt_base.md + estado + precios actuales.
4. Llama a la API de Claude (con web_search activado) para el análisis.
5. Parsea el bloque JSON de actualización de señales al final de la respuesta.
6. Actualiza y persiste state.json.
7. Regenera docs/index.html (página de GitHub Pages) con el semáforo y el análisis.

Requiere variable de entorno:
- ANTHROPIC_API_KEY

Opcional:
- CLAUDE_MODEL  (por defecto: claude-sonnet-5)
"""

import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from fetch_prices import fetch_stock_prices, fetch_btc_price_eur
from generate_page import build_html

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "state.json"
PROMPT_PATH = REPO_ROOT / "prompt_base.md"
DOCS_DIR = REPO_ROOT / "docs"

DEFAULT_MODEL = "claude-sonnet-5"


def load_state():
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def build_context(state, precios_acciones, precio_btc):
    """Construye el bloque de contexto con estado + precios actuales para inyectar en el prompt."""
    contexto = {
        "ultima_revision": state["meta"]["ultima_revision"],
        "posiciones_capa_2": {},
        "posicion_btc": {},
    }

    for ticker, datos in state["capa_2_alta_conviccion"].items():
        precio_actual = precios_acciones.get(ticker, {}).get("precio")
        entrada = datos["precio_entrada"]
        pnl_pct = None
        if precio_actual and entrada:
            pnl_pct = round((precio_actual / entrada - 1) * 100, 2)

        contexto["posiciones_capa_2"][ticker] = {
            "nombre": datos["nombre"],
            "precio_entrada": entrada,
            "precio_actual": precio_actual,
            "pnl_pct": pnl_pct,
            "ultima_senal_previa": datos.get("ultima_senal"),
            "ultima_senal_fecha_previa": datos.get("ultima_senal_fecha"),
        }

    btc_data = state["capa_3_cripto"]["BTC"]
    precio_btc_actual = precio_btc.get("precio_eur")
    entrada_btc = btc_data["precio_entrada"]
    pnl_btc_pct = None
    if precio_btc_actual and entrada_btc:
        pnl_btc_pct = round((precio_btc_actual / entrada_btc - 1) * 100, 2)

    contexto["posicion_btc"] = {
        "cantidad": btc_data["cantidad"],
        "precio_entrada": entrada_btc,
        "precio_actual": precio_btc_actual,
        "pnl_pct": pnl_btc_pct,
    }

    return contexto


def call_claude(prompt_base, contexto, model):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    client = anthropic.Anthropic(api_key=api_key)

    mensaje_usuario = (
        f"{prompt_base}\n\n"
        f"---\n"
        f"ESTADO ACTUAL DE LA CARTERA (JSON):\n"
        f"```json\n{json.dumps(contexto, indent=2, ensure_ascii=False)}\n```\n\n"
        f"Realiza la revisión de hoy siguiendo las instrucciones anteriores."
    )

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": mensaje_usuario}],
    )

    print(f"Modelo: {model}")
    print(f"stop_reason: {response.stop_reason}, bloques de contenido: {len(response.content)}")

    texto_completo = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    return texto_completo, response.stop_reason


def extraer_bloque_json(texto):
    """Busca un bloque ```json ... ``` al final de la respuesta con las actualizaciones de señal."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def actualizar_estado(state, actualizaciones, fecha_iso):
    if not actualizaciones:
        return state

    for ticker, senal in actualizaciones.get("capa_2_alta_conviccion", {}).items():
        if ticker in state["capa_2_alta_conviccion"]:
            state["capa_2_alta_conviccion"][ticker]["ultima_senal"] = senal
            state["capa_2_alta_conviccion"][ticker]["ultima_senal_fecha"] = fecha_iso

    if "BTC" in actualizaciones.get("capa_3_cripto", {}):
        state["capa_3_cripto"]["BTC"]["ultima_senal"] = actualizaciones["capa_3_cripto"]["BTC"]
        state["capa_3_cripto"]["BTC"]["ultima_senal_fecha"] = fecha_iso

    return state


def main():
    model = os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL).strip()
    fecha_iso = datetime.now(timezone.utc).isoformat()

    state = load_state()
    prompt_base = PROMPT_PATH.read_text(encoding="utf-8")

    print("Obteniendo precios actuales...")
    precios_acciones = fetch_stock_prices()
    precio_btc = fetch_btc_price_eur()

    contexto = build_context(state, precios_acciones, precio_btc)

    print(f"Llamando a Claude ({model}) para el análisis...")
    respuesta, stop_reason = call_claude(prompt_base, contexto, model)

    actualizaciones = extraer_bloque_json(respuesta)
    state = actualizar_estado(state, actualizaciones, fecha_iso)
    state["meta"]["ultima_revision"] = fecha_iso
    state["historial_revisiones"].append({
        "fecha": fecha_iso,
        "resumen": respuesta[:500],
        "cortado_por_tokens": stop_reason == "max_tokens",
    })

    # Mantener historial acotado a las últimas 30 revisiones
    state["historial_revisiones"] = state["historial_revisiones"][-30:]

    save_state(state)
    print("Estado actualizado y guardado.")

    respuesta_limpia = re.sub(r"```json.*?```", "", respuesta, flags=re.DOTALL).strip()
    if stop_reason == "max_tokens":
        respuesta_limpia += (
            "\n\n---\n⚠️ Respuesta cortada por límite de tokens: puede faltar contenido "
            "al final (incluidas las señales del semáforo)."
        )

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(
        build_html(state, contexto, respuesta_limpia, fecha_iso, modelo=model),
        encoding="utf-8"
    )
    print("Página docs/index.html regenerada.")


if __name__ == "__main__":
    main()
