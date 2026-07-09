"""
Genera docs/index.html: página estática con tarjetas de semáforo, gráficas
interactivas de TradingView, sección de fondos con deriva visual, historial
de señales y análisis del día.
"""

import html as html_lib
import json as _json
import re

import markdown

_INICIO_ITEM = re.compile(r"^\s*[-*]\s+")

TV_SYMBOLS = {
    "CIFR": "NASDAQ:CIFR",
    "IREN": "NASDAQ:IREN",
    "LEU": "AMEX:LEU",
    "OKLO": "NYSE:OKLO",
    "CRDO": "NASDAQ:CRDO",
    "BTC": "BITSTAMP:BTCUSD",
}

MODEL_NAME = "claude-sonnet-5"


def _separar_listas(texto):
    lineas = texto.split("\n")
    salida = []
    for i, linea in enumerate(lineas):
        if i > 0 and _INICIO_ITEM.match(linea):
            anterior = lineas[i - 1]
            if anterior.strip() != "" and not _INICIO_ITEM.match(anterior):
                salida.append("")
        salida.append(linea)
    return "\n".join(salida)


SEÑAL_INFO = {
    "🟢": {"clase": "verde", "etiqueta": "Mantener / ampliar"},
    "🟡": {"clase": "ambar", "etiqueta": "Vigilar"},
    "🔴": {"clase": "rojo", "etiqueta": "Revisar / recortar"},
    "🔵": {"clase": "azul", "etiqueta": "Sin cambios"},
}
SEÑAL_DEFECTO = {"clase": "neutro", "etiqueta": "Sin señal"}

PAGINA_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión diaria — Cartera</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f7f7f8; --fg: #1c1c1e; --muted: #6b6b70; --card-bg: #ffffff; --border: #e5e5e7;
    --verde-bg: #e6f4ea; --verde-fg: #1a7f37;
    --ambar-bg: #fff7e0; --ambar-fg: #92600a;
    --rojo-bg: #fdecea; --rojo-fg: #c0392b;
    --azul-bg: #e8f0fe; --azul-fg: #1a56db;
    --neutro-bg: #eeeeee; --neutro-fg: #6b6b70;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #17181a; --fg: #f0f0f1; --muted: #9a9a9f; --card-bg: #232427; --border: #34353a;
      --verde-bg: #16321f; --verde-fg: #4ade80;
      --ambar-bg: #3a2c0a; --ambar-fg: #fbbf24;
      --rojo-bg: #3a1a17; --rojo-fg: #f87171;
      --azul-bg: #17233d; --azul-fg: #7fa6f7;
      --neutro-bg: #2c2d31; --neutro-fg: #9a9a9f;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    max-width: 960px;
    margin: 0 auto;
    padding: 1.5rem 1rem 3rem;
    background: var(--bg);
    color: var(--fg);
    line-height: 1.55;
  }}
  h1 {{ font-size: 1.35rem; margin-bottom: 0.2rem; }}
  .fecha {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 0.4rem; }}
  .modelo-badge {{
    display: inline-block;
    font-size: 0.72rem;
    background: var(--azul-bg);
    color: var(--azul-fg);
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    margin-bottom: 1.5rem;
    font-weight: 600;
  }}
  /* ── Tarjetas semáforo ── */
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
    margin-bottom: 2rem;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.9rem 1rem;
  }}
  .card .ticker {{ font-weight: 700; font-size: 1rem; }}
  .card .nombre {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 0.5rem; }}
  .card .precio {{ font-size: 1.1rem; font-weight: 600; }}
  .card .pnl {{ font-size: 0.9rem; font-weight: 600; margin-bottom: 0.6rem; }}
  .pnl.pos {{ color: var(--verde-fg); }}
  .pnl.neg {{ color: var(--rojo-fg); }}
  .badge {{
    display: inline-block;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
  }}
  .badge.verde {{ background: var(--verde-bg); color: var(--verde-fg); }}
  .badge.ambar {{ background: var(--ambar-bg); color: var(--ambar-fg); }}
  .badge.rojo  {{ background: var(--rojo-bg);  color: var(--rojo-fg);  }}
  .badge.azul  {{ background: var(--azul-bg);  color: var(--azul-fg);  }}
  .badge.neutro{{ background: var(--neutro-bg);color: var(--neutro-fg);}}
  /* ── Fondos indexados ── */
  .fondos-section {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 2rem;
  }}
  .fondos-section h2 {{ font-size: 1rem; margin: 0 0 0.8rem; }}
  .fondos-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.8rem;
  }}
  .fondo-card {{ padding: 0.5rem 0; }}
  .fondo-nombre {{ color: var(--muted); font-size: 0.78rem; }}
  .fondo-valor  {{ font-weight: 600; font-size: 0.95rem; }}
  .fondo-pnl   {{ font-size: 0.82rem; font-weight: 600; }}
  .fondo-pnl.pos {{ color: var(--verde-fg); }}
  .fondo-pnl.neg {{ color: var(--rojo-fg); }}
  /* Barra de deriva */
  .deriva-label {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.4rem; }}
  .barra-wrap {{
    position: relative;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    margin-top: 0.25rem;
    overflow: visible;
  }}
  .barra-actual {{
    position: absolute;
    top: 0; left: 0;
    height: 6px;
    border-radius: 3px;
    background: var(--azul-fg);
    transition: width 0.4s;
  }}
  .barra-objetivo {{
    position: absolute;
    top: -3px;
    width: 2px;
    height: 12px;
    background: var(--ambar-fg);
    border-radius: 1px;
  }}
  .deriva-ok   {{ color: var(--verde-fg); }}
  .deriva-warn {{ color: var(--ambar-fg); }}
  .deriva-alert{{ color: var(--rojo-fg);  }}
  .fondos-total {{
    margin-top: 0.8rem;
    font-size: 0.9rem;
    font-weight: 700;
    border-top: 1px solid var(--border);
    padding-top: 0.6rem;
  }}
  /* ── Historial señales ── */
  .historial-section {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 2rem;
    overflow-x: auto;
  }}
  .historial-section h2 {{ font-size: 1rem; margin: 0 0 0.8rem; }}
  .historial-table {{
    border-collapse: collapse;
    width: 100%;
    font-size: 0.82rem;
  }}
  .historial-table th {{
    text-align: left;
    color: var(--muted);
    font-weight: 600;
    padding: 0.3rem 0.6rem;
    border-bottom: 1px solid var(--border);
  }}
  .historial-table td {{
    padding: 0.35rem 0.6rem;
    border-bottom: 1px solid var(--border);
    text-align: center;
  }}
  .historial-table td:first-child {{ text-align: left; color: var(--muted); }}
  /* ── Gráficas ── */
  .charts-section {{ margin-bottom: 2rem; }}
  .charts-section h2 {{ font-size: 1.1rem; margin-bottom: 1rem; }}
  .charts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1rem;
  }}
  .chart-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }}
  .chart-label {{
    font-size: 0.82rem;
    font-weight: 700;
    padding: 0.55rem 1rem 0.3rem;
    color: var(--muted);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}
  /* ── Análisis ── */
  article {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.5rem 1.5rem 1.25rem;
  }}
  article h1 {{ font-size: 1.1rem; }}
  article h2 {{
    font-size: 1.05rem;
    margin: 1.4rem 0 0.5rem;
    padding-top: 0.6rem;
    border-top: 1px solid var(--border);
  }}
  article h2:first-child {{ border-top: none; padding-top: 0; margin-top: 1rem; }}
  article hr {{ border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }}
  article p  {{ margin: 0.6rem 0; }}
  article ul {{ padding-left: 1.2rem; }}
  article em {{ color: var(--muted); }}
  article strong {{ color: var(--fg); }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 1.5rem; text-align: center; }}
</style>
</head>
<body>
<h1>📊 Revisión diaria — Cartera IA / Cripto</h1>
<div class="fecha">Última actualización: {fecha}</div>
<span class="modelo-badge">🤖 {modelo}</span>

<div class="grid">
  {tarjetas}
</div>

{fondos_html}

{historial_html}

<div class="charts-section">
  <h2>📈 Gráficas técnicas en tiempo real</h2>
  <div class="charts-grid">
    {charts}
  </div>
</div>

<article>
{analisis_html}
</article>

<footer>Generado automáticamente · no constituye asesoramiento de inversión personalizado</footer>

<script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
<script type="text/javascript">
(function() {{
  var configs = {tv_configs};
  configs.forEach(function(cfg) {{ new TradingView.widget(cfg); }});
}})();
</script>
</body>
</html>
"""

TARJETA_TEMPLATE = """<div class="card">
    <div class="ticker">{ticker}</div>
    <div class="nombre">{nombre}</div>
    <div class="precio">{actual}</div>
    <div class="pnl {pnl_clase}">{pnl}</div>
    <span class="badge {badge_clase}">{badge_emoji} {badge_etiqueta}</span>
  </div>"""


def _fmt_precio(valor):
    return f"{valor:,.2f}" if valor is not None else "—"


def _fmt_pnl(valor):
    if valor is None:
        return "—"
    signo = "+" if valor >= 0 else ""
    return f"{signo}{valor:.2f}%"


def _tarjeta(ticker, nombre, contexto_posicion, senal):
    pnl = contexto_posicion.get("pnl_pct")
    pnl_clase = "pos" if (pnl or 0) >= 0 else "neg"
    info_senal = SEÑAL_INFO.get(senal, SEÑAL_DEFECTO)
    return TARJETA_TEMPLATE.format(
        ticker=html_lib.escape(ticker),
        nombre=html_lib.escape(nombre),
        actual=_fmt_precio(contexto_posicion.get("precio_actual")),
        pnl=_fmt_pnl(pnl),
        pnl_clase=pnl_clase,
        badge_clase=info_senal["clase"],
        badge_emoji=senal if senal else "",
        badge_etiqueta=html_lib.escape(info_senal["etiqueta"]),
    )


def _fondos_html(state):
    """Sección de fondos con barra visual de deriva actual vs objetivo."""
    fondos = state.get("capa_1_indexado", {}).get("posiciones", {})
    if not fondos:
        return ""
    total = state["capa_1_indexado"].get("valor_total_eur", 0)
    pesos_obj = state["capa_1_indexado"].get("pesos_objetivo", {})

    items = []
    for key, f in fondos.items():
        pnl_pct = f.get("pnl_pct", 0)
        pnl_eur = f.get("pnl_eur", 0)
        pnl_clase = "pos" if pnl_pct >= 0 else "neg"
        signo = "+" if pnl_eur >= 0 else ""

        peso_actual = round(f["valor_eur"] / total * 100, 1) if total else 0
        peso_obj = pesos_obj.get(key, 0)
        deriva = abs(peso_actual - peso_obj)
        if deriva < 2:
            deriva_clase = "deriva-ok"
            deriva_icon = "✓"
        elif deriva < 5:
            deriva_clase = "deriva-warn"
            deriva_icon = "⚠"
        else:
            deriva_clase = "deriva-alert"
            deriva_icon = "🔴"

        barra_html = (
            f'<div class="deriva-label">'
            f'Peso actual: <strong>{peso_actual}%</strong> · '
            f'Objetivo: {peso_obj}% · '
            f'<span class="{deriva_clase}">{deriva_icon} Δ {deriva:.1f} pp</span>'
            f'</div>'
            f'<div class="barra-wrap">'
            f'  <div class="barra-actual" style="width:{min(peso_actual,100)}%"></div>'
            f'  <div class="barra-objetivo" style="left:{min(peso_obj,100)}%"></div>'
            f'</div>'
        )

        items.append(
            f'<div class="fondo-card">'
            f'<div class="fondo-nombre">{html_lib.escape(f["nombre"])}</div>'
            f'<div class="fondo-valor">{f["valor_eur"]:,.2f} €</div>'
            f'<div class="fondo-pnl {pnl_clase}">{signo}{pnl_eur:.2f} € &nbsp; {signo}{pnl_pct:.2f}%</div>'
            f'{barra_html}'
            f'</div>'
        )

    return (
        '<div class="fondos-section">'
        '<h2>📂 Fondos indexados — Capa 1</h2>'
        f'<div class="fondos-grid">{" ".join(items)}</div>'
        f'<div class="fondos-total">Total fondos: {total:,.2f} €</div>'
        '</div>'
    )


def _historial_html(state):
    """Tabla con las últimas 7 revisiones: fecha + señal por ticker."""
    tickers = list(state.get("capa_2_alta_conviccion", {}).keys()) + ["BTC"]
    historial = state.get("historial_revisiones", [])

    # Recopilar señales parseando el resumen de cada revisión
    # El resumen guarda solo texto libre, pero las señales ya están en state.
    # Construimos la tabla mostrando las últimas N fechas donde hay señal registrada.
    # Para eso usamos ultima_senal_fecha de cada posición y el historial de fechas.
    fechas = sorted(
        {r["fecha"][:10] for r in historial if r.get("fecha")},
        reverse=True
    )[:7]

    if not fechas:
        return ""

    cabecera = "<tr><th>Fecha</th>" + "".join(f"<th>{t}</th>" for t in tickers) + "</tr>"

    # Para cada fecha, mostramos la señal más reciente conocida para ese día
    # (usamos ultima_senal de state como proxy para la última fecha registrada)
    filas = []
    for fecha in fechas:
        celdas = [f'<td>{fecha}</td>']
        for t in tickers:
            if t == "BTC":
                datos = state.get("capa_3_cripto", {}).get("BTC", {})
            else:
                datos = state.get("capa_2_alta_conviccion", {}).get(t, {})
            senal_fecha = (datos.get("ultima_senal_fecha") or "")[:10]
            senal = datos.get("ultima_senal", "—") if senal_fecha == fecha else "—"
            celdas.append(f'<td>{senal}</td>')
        filas.append("<tr>" + "".join(celdas) + "</tr>")

    return (
        '<div class="historial-section">'
        '<h2>🕐 Historial de señales recientes</h2>'
        '<table class="historial-table">'
        f'<thead>{cabecera}</thead>'
        f'<tbody>{" ".join(filas)}</tbody>'
        '</table>'
        '</div>'
    )


def _build_charts(tickers_nombres):
    chart_divs = []
    tv_configs = []
    for ticker, nombre in tickers_nombres:
        symbol = TV_SYMBOLS.get(ticker, ticker)
        cid = f"tv_{ticker.replace('-', '_')}"
        chart_divs.append(
            f'<div class="chart-card">'
            f'<div class="chart-label">{html_lib.escape(ticker)} — {html_lib.escape(nombre)}</div>'
            f'<div id="{cid}"></div>'
            f'</div>'
        )
        tv_configs.append({
            "autosize": True,
            "symbol": symbol,
            "interval": "D",
            "timezone": "Europe/Madrid",
            "theme": "dark",
            "style": "1",
            "locale": "es",
            "enable_publishing": False,
            "hide_top_toolbar": False,
            "save_image": False,
            "container_id": cid,
            "height": 380,
            "width": "100%",
        })
    return "\n    ".join(chart_divs), _json.dumps(tv_configs, ensure_ascii=False)


def build_html(state, contexto, respuesta_limpia, fecha_iso, modelo=MODEL_NAME):
    tarjetas = []
    tickers_nombres = []

    for ticker, datos in state["capa_2_alta_conviccion"].items():
        ctx_pos = contexto["posiciones_capa_2"].get(ticker, {})
        tarjetas.append(_tarjeta(ticker, datos["nombre"], ctx_pos, datos.get("ultima_senal")))
        tickers_nombres.append((ticker, datos["nombre"]))

    btc = state["capa_3_cripto"]["BTC"]
    tarjetas.append(_tarjeta("BTC", "Bitcoin", contexto["posicion_btc"], btc.get("ultima_senal")))
    tickers_nombres.append(("BTC", "Bitcoin"))

    fondos_html = _fondos_html(state)
    historial_html = _historial_html(state)
    charts_html, tv_configs = _build_charts(tickers_nombres)

    # CORRECCIÓN: markdown primero (sobre texto plano), luego el HTML resultante
    # no se escapa. El escape previo rompía emojis y caracteres especiales.
    texto_md = _separar_listas(respuesta_limpia)
    analisis_html = markdown.markdown(texto_md, extensions=["extra"])

    fecha_legible = fecha_iso.replace("T", " ")[:16] + " UTC"

    return PAGINA_TEMPLATE.format(
        fecha=html_lib.escape(fecha_legible),
        modelo=html_lib.escape(modelo),
        tarjetas="\n  ".join(tarjetas),
        fondos_html=fondos_html,
        historial_html=historial_html,
        charts=charts_html,
        tv_configs=tv_configs,
        analisis_html=analisis_html,
    )
