import yfinance as yf
import pandas as pd
import json
from plotly.offline import get_plotlyjs

DEFAULT_DATE = '2024-07-01'   # kept as the default reference

tickers_my = {
    'Maybank':         '1155.KL',
    'Public Bank':     '1295.KL',
    'CIMB':            '1023.KL',
    'Hong Leong Bank': '5819.KL',
    'RHB Bank':        '1066.KL',
    'Hong Leong FG':   '1082.KL',
    'AmBank':          '1015.KL',
    'Alliance Bank':   '2488.KL',
    'Bank Islam':      '5258.KL',
    'Affin Bank':      '5185.KL',
}
tickers_sg = {
    'DBS':  'D05.SI',
    'OCBC': 'O39.SI',
    'UOB':  'U11.SI',
}
all_tickers_map = {**tickers_my, **tickers_sg}


def generate_chart():
    print("Fetching data...")
    raw = yf.download(
        list(all_tickers_map.values()),
        start="2024-06-25",
        auto_adjust=False,
        progress=False,
    )

    # Handle both old (MultiIndex) and new yfinance column shapes
    if isinstance(raw.columns, pd.MultiIndex):
        data = raw['Adj Close']
    else:
        data = raw

    data = data.ffill()

    # Build per-bank dict: {name: {country, prices:{date_str: price}}}
    banks = {}
    for bank_name, ticker in all_tickers_map.items():
        if ticker not in data.columns:
            print(f"  ⚠ {ticker} not in data — skipping")
            continue
        series = data[ticker].dropna()
        country = 'MY' if ticker in tickers_my.values() else 'SG'
        banks[bank_name] = {
            'country': country,
            'prices': {
                str(d.date()): round(float(v), 6)
                for d, v in series.items()
            },
        }

    # All unique trading dates from DEFAULT_DATE onwards (across all banks)
    trading_dates = sorted({
        d
        for b in banks.values()
        for d in b['prices']
        if d >= DEFAULT_DATE
    })

    if not trading_dates:
        raise RuntimeError("No trading dates found — check yfinance fetch.")

    print(f"  {len(banks)} banks | {len(trading_dates)} trading dates "
          f"({trading_dates[0]} to {trading_dates[-1]})")

    plotly_js = get_plotlyjs()
    html      = _build_html(banks, trading_dates, plotly_js)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Done — index.html written.")


def _build_html(banks, trading_dates, plotly_js):
    my_banks   = [n for n in banks if banks[n]['country'] == 'MY']
    sg_banks   = [n for n in banks if banks[n]['country'] == 'SG']
    bank_order = my_banks + sg_banks          # trace order: MY first, SG second

    banks_json   = json.dumps(banks,         separators=(',', ':'))
    dates_json   = json.dumps(trading_dates, separators=(',', ':'))
    order_json   = json.dumps(bank_order,    separators=(',', ':'))
    max_date     = trading_dates[-1]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MY &amp; SG Bank Performance</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f4f6f8;
      padding: 18px;
      color: #212529;
    }}
    h1 {{ font-size: 1.25rem; margin-bottom: 12px; }}

    /* ── Controls bar ── */
    .controls {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 14px;
      background: #fff;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      padding: 12px 18px;
      margin-bottom: 14px;
      max-width: 1100px;
    }}
    .ctrl-group {{ display: flex; align-items: center; gap: 8px; }}
    .ctrl-label  {{ font-size: 0.82rem; font-weight: 600; color: #495057; white-space: nowrap; }}
    input[type=date] {{
      padding: 5px 10px;
      border: 1px solid #ced4da;
      border-radius: 5px;
      font-size: 0.88rem;
      cursor: pointer;
      background: #fff;
    }}
    .ref-note {{
      font-size: 0.76rem;
      color: #6c757d;
      font-style: italic;
      min-width: 0;
    }}
    .filter-btns {{ display: flex; gap: 6px; margin-left: auto; }}
    .filter-btns button {{
      padding: 5px 16px;
      border: 1px solid #ced4da;
      border-radius: 5px;
      background: #fff;
      font-size: 0.84rem;
      cursor: pointer;
      transition: background .15s, color .15s, border-color .15s;
    }}
    .filter-btns button.active {{
      background: #0d6efd;
      color: #fff;
      border-color: #0d6efd;
    }}
    #chart {{ max-width: 1100px; }}
  </style>
</head>
<body>

<h1>MY &amp; SG Bank Relative Performance</h1>

<div class="controls">
  <div class="ctrl-group">
    <span class="ctrl-label">Reference Date:</span>
    <input type="date" id="ref-input"
           min="{DEFAULT_DATE}"
           max="{max_date}"
           value="{DEFAULT_DATE}">
    <span class="ref-note" id="ref-note"></span>
  </div>

  <div class="filter-btns">
    <button id="btn-all" class="active" onclick="setFilter('all')">All Banks</button>
    <button id="btn-my"               onclick="setFilter('my')">Malaysia</button>
    <button id="btn-sg"               onclick="setFilter('sg')">Singapore</button>
  </div>
</div>

<div id="chart"></div>

<!-- Plotly bundled inline — no CDN dependency -->
<script>{plotly_js}</script>

<script>
// ── Data injected by main.py ──────────────────────────────────────────────────
const BANKS         = {banks_json};
const TRADING_DATES = {dates_json};   // sorted, weekdays only, from {DEFAULT_DATE}
const BANK_ORDER    = {order_json};   // MY banks first, SG banks second
const MY_COUNT      = {len(my_banks)};
const DEFAULT_DATE  = '{DEFAULT_DATE}';

// ── State ─────────────────────────────────────────────────────────────────────
let currentFilter = 'all';
let chartReady    = false;

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Returns the latest trading date that is <= dateStr, or null if none. */
function closestTradingDate(dateStr) {{
  let best = null;
  for (const d of TRADING_DATES) {{
    if (d <= dateStr) best = d;
    else break;
  }}
  return best;
}}

/** Build Plotly trace array rebased to refDate. */
function buildTraces(refDate) {{
  return BANK_ORDER.map((name, idx) => {{
    const bank      = BANKS[name];
    const basePrice = bank.prices[refDate];
    if (!basePrice) return null;

    const dates  = Object.keys(bank.prices).filter(d => d >= refDate).sort();
    const yVals  = dates.map(d => parseFloat((bank.prices[d] / basePrice).toFixed(4)));
    const ismy   = idx < MY_COUNT;
    const visible = (
      currentFilter === 'all' ||
      (currentFilter === 'my' && ismy) ||
      (currentFilter === 'sg' && !ismy)
    );
    return {{
      type: 'scatter',
      mode: 'lines',
      name: `${{name}} (${{bank.country}})`,
      x: dates,
      y: yVals,
      visible,
      hovertemplate: '%{{y:.3f}}x | %{{text}}<extra></extra>',
      text: Array(dates.length).fill(name),
    }};
  }}).filter(Boolean);
}}

const layout = {{
  height: 750,
  xaxis: {{
    title: 'Date',
    rangeslider: {{ visible: true }},
    rangeselector: {{
      buttons: [
        {{ count: 1, label: '1m', step: 'month', stepmode: 'backward' }},
        {{ count: 3, label: '3m', step: 'month', stepmode: 'backward' }},
        {{ step: 'all', label: 'All' }},
      ],
    }},
  }},
  yaxis: {{
    title: 'Relative Performance (1.0 = reference date)',
    hoverformat: '.3f',
  }},
  hovermode: 'x unified',
  template: 'plotly_white',
  legend: {{ title: {{ text: 'Banks' }} }},
  margin: {{ b: 60, t: 50 }},
}};

const plotConfig = {{ displayModeBar: true, responsive: true }};

// ── Render ────────────────────────────────────────────────────────────────────
function render(selectedDate) {{
  const actual = closestTradingDate(selectedDate);
  if (!actual) {{ console.warn('No trading date found for', selectedDate); return; }}

  // Update the note if we fell back to a different date
  const note = document.getElementById('ref-note');
  if (actual !== selectedDate) {{
    note.textContent = `↳ Using ${{actual}} (last trading day before selected date)`;
  }} else {{
    note.textContent = '';
  }}

  // Update chart title
  layout.title = `Relative Performance — Base: ${{actual}} = 1.0`;

  const traces = buildTraces(actual);
  if (!chartReady) {{
    Plotly.newPlot('chart', traces, layout, plotConfig);
    chartReady = true;
  }} else {{
    Plotly.react('chart', traces, layout, plotConfig);
  }}
}}

// ── Filter buttons ────────────────────────────────────────────────────────────
function setFilter(f) {{
  currentFilter = f;
  document.querySelectorAll('.filter-btns button').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + f).classList.add('active');

  if (!chartReady) return;

  // Update only visibility — keep existing data and axes intact
  const visibleArr = BANK_ORDER.map((_, i) => {{
    const ismy = i < MY_COUNT;
    return (
      f === 'all' ||
      (f === 'my' && ismy) ||
      (f === 'sg' && !ismy)
    );
  }});
  Plotly.restyle('chart', {{ visible: visibleArr }});
}}

// ── Date input event ──────────────────────────────────────────────────────────
document.getElementById('ref-input').addEventListener('change', function () {{
  render(this.value);
}});

// ── Boot ──────────────────────────────────────────────────────────────────────
render(DEFAULT_DATE);
</script>

</body>
</html>"""


if __name__ == '__main__':
    generate_chart()
