# Agente IA — Revisión de cartera

Agente automatizado que revisa diariamente la cartera de Santiago (Capa 2: acciones temáticas
IA infra/nuclear/compute + Capa 3: BTC), busca catalizadores recientes, aplica la regla de
"tesis rota" (-25% sin catalizador negativo), y publica el análisis con un semáforo de decisión
por posición en una página web (GitHub Pages).

## Estructura

```
├── state.json               # Estado: posiciones, precio de entrada, última señal
├── prompt_base.md            # Prompt del analista (editar aquí para cambiar el criterio)
├── requirements.txt
├── src/
│   ├── fetch_prices.py       # Precios vía Yahoo Finance (acciones) + CoinGecko (BTC), sin API key
│   ├── run_review.py         # Orquestador: junta todo, llama a Claude, actualiza estado
│   └── generate_page.py      # Genera docs/index.html con el semáforo + análisis del día
├── docs/
│   └── index.html            # Página publicada por GitHub Pages, se sobreescribe cada día
└── .github/workflows/
    └── daily_review.yml      # Ejecución automática L-V a las 07:30 UTC
```

## Setup inicial

### 1. Clave necesaria

Solo hace falta una: la **Anthropic API key** de [console.anthropic.com](https://console.anthropic.com)
(el script llama a la API de Claude, no a tu cuenta de claude.ai — requiere su propia clave con
facturación asociada). Los precios de acciones y BTC se obtienen de fuentes públicas sin clave
(Yahoo Finance y CoinGecko).

### 2. Configurar el GitHub Secret

En el repo: `Settings > Secrets and variables > Actions > New repository secret`. Añade
`ANTHROPIC_API_KEY` con el valor de tu clave.

**Nunca** pongas esta clave directamente en el código ni en `.env` subido al repo —
`.gitignore` ya lo excluye por seguridad.

### 3. Revisar y corregir `state.json`

Los precios de entrada actuales son **estimaciones** calculadas por ingeniería inversa desde
el % de P&L que muestra el bróker (`precio_actual / (1 + %var/100)`). Verifica cada uno contra
tu bróker real y corrige el campo `precio_entrada`; cambia `precio_entrada_confianza` de
`"estimado"` a `"confirmado"` una vez lo hagas.

También falta rellenar `pesos_objetivo` en `capa_1_indexado` si quieres que el agente pueda
detectar deriva de rebalanceo en el núcleo indexado (de momento esa capa no se revisa a diario,
solo la mencionará si hay una noticia macro estructural).

### 4. Probar en local (opcional, antes de fiarte del cron)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=...

python src/run_review.py
```

### 5. Activar el workflow

Una vez el Secret esté configurado, el workflow corre solo de lunes a viernes a las 07:30
UTC. También puedes lanzarlo manualmente desde la pestaña **Actions > Revisión diaria de
cartera > Run workflow** para probarlo sin esperar al cron.

### 6. Activar GitHub Pages (paso único, manual)

El workflow genera `docs/index.html` en cada ejecución, pero publicarlo requiere activar Pages
una sola vez: `Settings > Pages > Build and deployment > Source: Deploy from a branch`, rama
`main` (o la que uses como base), carpeta `/docs`. Guarda. GitHub te dará una URL del tipo
`https://<tu-usuario>.github.io/agente-IA-INVERSION-/`, que se actualizará sola en cada
ejecución del cron.

**Importante:** GitHub Pages es público por defecto — cualquiera con el link vería tu cartera,
P&L y señales. Si prefieres mantenerlo privado, hazlo saber; la alternativa sencilla es leer
`docs/index.html` (o el histórico en `state.json`) directamente desde el repo privado, sin Pages.

## Cómo funciona la persistencia de estado

Cada ejecución:
1. Lee `state.json` para saber la fecha de la última revisión y evitar repetir análisis de
   noticias ya cubiertas.
2. Al terminar, Claude devuelve un bloque JSON con las señales actualizadas por posición
   (🟢🟡🔴🔵), que el script extrae y guarda de vuelta en `state.json`.
3. El workflow hace commit automático del `state.json` actualizado, así que tienes historial
   completo y auditable de cada señal que se ha dado a lo largo del tiempo — útil para revisar
   después si el agente acertó o no.

## Ajustar el criterio de análisis

Todo el criterio vive en `prompt_base.md`. Si quieres cambiar el umbral de "tesis rota"
(actualmente -25%), el filtro de ideas nuevas, o el formato de salida, edita ese archivo — no
hace falta tocar el código Python.
