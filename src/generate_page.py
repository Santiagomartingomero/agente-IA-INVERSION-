"""
Genera docs/index.html: una página estática de una sola pantalla con el semáforo de
posiciones y el análisis completo de la última revisión, pensada para GitHub Pages.
"""

import html as html_lib

PAGINA_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión diaria — Cartera</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    max-width: 720px;
    margin: 2rem auto;
    padding: 0 1rem;
    line-height: 1.5;
  }}
  h1 {{ font-size: 1.3rem; }}
  .fecha {{ color: #888; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
  th, td {{ text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid #ddd; }}
  th {{ font-size: 0.85rem; color: #666; }}
  .pnl-pos {{ color: #1a7f37; }}
  .pnl-neg {{ color: #c0392b; }}
  pre {{
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: inherit;
    font-size: 0.95rem;
  }}
</style>
</head>
<body>
<h1>Revisión diaria — Cartera IA / Cripto</h1>
<div class="fecha">Última actualización: {fecha}</div>
<table>
  <tr><th>Posición</th><th>Entrada</th><th>Actual</th><th>P&amp;L</th><th>Señal</th></tr>
  {filas}
</table>
<pre>{analisis}</pre>
</body>
</html>
"""

FILA_TEMPLATE = (
    "<tr><td>{ticker} · {nombre}</td><td>{entrada}</td><td>{actual}</td>"
    "<td class=\"{pnl_clase}\">{pnl}</td><td>{senal}</td></tr>"
)


def _fmt_precio(valor):
    return f"{valor:,.2f}" if valor is not None else "—"


def _fmt_pnl(valor):
    if valor is None:
        return "—"
    signo = "+" if valor >= 0 else ""
    return f"{signo}{valor:.2f}%"


def _fila(ticker, nombre, precio_entrada, contexto_posicion, senal):
    pnl = contexto_posicion.get("pnl_pct")
    pnl_clase = "pnl-pos" if (pnl or 0) >= 0 else "pnl-neg"
    return FILA_TEMPLATE.format(
        ticker=html_lib.escape(ticker),
        nombre=html_lib.escape(nombre),
        entrada=_fmt_precio(precio_entrada),
        actual=_fmt_precio(contexto_posicion.get("precio_actual")),
        pnl=_fmt_pnl(pnl),
        pnl_clase=pnl_clase,
        senal=html_lib.escape(senal or "—"),
    )


def build_html(state, contexto, respuesta_limpia, fecha_iso):
    filas = []
    for ticker, datos in state["capa_2_alta_conviccion"].items():
        ctx_pos = contexto["posiciones_capa_2"].get(ticker, {})
        filas.append(_fila(ticker, datos["nombre"], datos["precio_entrada"], ctx_pos, datos.get("ultima_senal")))

    btc = state["capa_3_cripto"]["BTC"]
    filas.append(_fila("BTC", "Bitcoin", btc["precio_entrada"], contexto["posicion_btc"], btc.get("ultima_senal")))

    return PAGINA_TEMPLATE.format(
        fecha=html_lib.escape(fecha_iso.replace("T", " ")[:16] + " UTC"),
        filas="\n  ".join(filas),
        analisis=html_lib.escape(respuesta_limpia),
    )
