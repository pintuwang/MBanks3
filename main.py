import yfinance as yf
import pandas as pd
import json
from plotly.offline import get_plotlyjs

DEFAULT_DATE = '2024-07-01'

# ── Bank definitions per country ──────────────────────────────────────────────
COUNTRY_BANKS = {
    'MY': {
        'label': 'Malaysia',
        'banks': {
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
        },
    },
    'SG': {
        'label': 'Singapore',
        'banks': {
            'DBS':  'D05.SI',
            'OCBC': 'O39.SI',
            'UOB':  'U11.SI',
        },
    },
    'ID': {
        'label': 'Indonesia',
        'banks': {
            'BCA':              'BBCA.JK',
            'Bank Mandiri':     'BMRI.JK',
            'BRI':              'BBRI.JK',
            'BNI':              'BBNI.JK',
            'BTN':              'BBTN.JK',
            'CIMB Niaga':       'BNGA.JK',
            'Danamon':          'BDMN.JK',
            'Permata':          'BNLI.JK',
            'Panin Bank':       'PNBN.JK',
            'Maybank Indonesia':'BNII.JK',
        },
    },
    'TH': {
        'label': 'Thailand',
        'banks': {
            'Bangkok Bank': 'BBL.BK',
            'KBank':        'KBANK.BK',
            'SCB':          'SCB.BK',
            'Krungthai':    'KTB.BK',
            'Krungsri':     'BAY.BK',
            'TTB Bank':     'TTB.BK',
            'Kiatnakin':    'KKP.BK',
            'TISCO':        'TISCO.BK',
            'LH Financial': 'LHFG.BK',
            'CIMB Thai':    'CIMBT.BK',
        },
    },
    'VN': {
        'label': 'Vietnam',
        'banks': {
            'Vietcombank': 'VCB.VN',
            'BIDV':        'BID.VN',
            'VietinBank':  'CTG.VN',
            'Techcombank': 'TCB.VN',
            'MB Bank':     'MBB.VN',
            'VP Bank':     'VPB.VN',
            'ACB':         'ACB.VN',
            'HDBank':      'HDB.VN',
            'Sacombank':   'STB.VN',
            'LPBank':      'LPB.VN',
        },
    },
    'JP': {
        'label': 'Japan',
        'banks': {
            'MUFG':         '8306.T',
            'SMFG':         '8316.T',
            'Mizuho':       '8411.T',
            'Resona':       '8308.T',
            'SM Trust':     '8309.T',
            'Concordia FG': '7186.T',
            'Fukuoka FG':   '8354.T',
            'Yamaguchi FG': '8418.T',
            'Chiba Bank':   '8331.T',
            'Gunma Bank':   '8334.T',
        },
    },
    'KR': {
        'label': 'S. Korea',
        'banks': {
            'KB Financial':    '105560.KS',
            'Shinhan':         '055550.KS',
            'Hana Financial':  '086790.KS',
            'Woori Financial': '316140.KS',
            'IBK':             '024110.KS',
            'BNK Financial':   '138930.KS',
            'JB Financial':    '175330.KS',
            'DGB Financial':   '139130.KS',
        },
    },
}

COUNTRY_ORDER = ['MY', 'SG', 'ID', 'TH', 'VN', 'JP', 'KR']


def generate_chart():
    # Build flat ticker list
    all_tickers = {
        bank: ticker
        for code in COUNTRY_ORDER
        for bank, ticker in COUNTRY_BANKS[code]['banks'].items()
    }

    print(f"Fetching {len(all_tickers)} tickers across {len(COUNTRY_ORDER)} countries...")
    raw = yf.download(
        list(all_tickers.values()),
        start='2024-06-25',
        auto_adjust=False,
        progress=False,
    )

    # Handle both old (MultiIndex) and new yfinance column shapes
    if isinstance(raw.columns, pd.MultiIndex):
        data = raw['Adj Close']
    else:
        data = raw

    data = data.ffill()

    # Build per-bank dict {name: {country, prices:{date_str: price}}}
    # Reverse map: ticker -> country code
    ticker_to_country = {
        ticker: code
        for code in COUNTRY_ORDER
        for bank, ticker in COUNTRY_BANKS[code]['banks'].items()
    }
    ticker_to_name = {v: k for code in COUNTRY_ORDER
                      for k, v in COUNTRY_BANKS[code]['banks'].items()}

    banks = {}
    loaded_by_country = {code: 0 for code in COUNTRY_ORDER}

    for code in COUNTRY_ORDER:
        for bank_name, ticker in COUNTRY_BANKS[code]['banks'].items():
            if ticker not in data.columns:
                print(f"  [!] {ticker} ({bank_name}) -- no data, skipped")
                continue
            series = data[ticker].dropna()
            if series.empty:
                print(f"  [!] {ticker} ({bank_name}) -- empty series, skipped")
                continue
            banks[bank_name] = {
                'country': code,
                'prices': {
                    str(d.date()): round(float(v), 6)
                    for d, v in series.items()
                },
            }
            loaded_by_country[code] += 1

    for code, n in loaded_by_country.items():
        label = COUNTRY_BANKS[code]['label']
        total = len(COUNTRY_BANKS[code]['banks'])
        print(f"  {label}: {n}/{total} banks loaded")

    # All unique trading dates from DEFAULT_DATE (union across all banks)
    trading_dates = sorted({
        d
        for b in banks.values()
        for d in b['prices']
        if d >= DEFAULT_DATE
    })

    if not trading_dates:
        raise RuntimeError("No trading dates found — check yfinance fetch.")

    print(f"\n  {len(banks)} banks total | "
          f"{len(trading_dates)} trading dates "
          f"({trading_dates[0]} to {trading_dates[-1]})")

    # Bank order: country by country, preserving insertion order
    bank_order = [
        name
        for code in COUNTRY_ORDER
        for name in COUNTRY_BANKS[code]['banks']
        if name in banks
    ]

    # Country metadata for JS
    country_meta = {
        code: COUNTRY_BANKS[code]['label']
        for code in COUNTRY_ORDER
    }

    plotly_js = get_plotlyjs()
    html = _build_html(banks, bank_order, trading_dates, country_meta, plotly_js)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Done -- index.html written.")


def _build_html(banks, bank_order, trading_dates, country_meta, plotly_js):
    banks_json        = json.dumps(banks,         separators=(',', ':'))
    order_json        = json.dumps(bank_order,    separators=(',', ':'))
    dates_json        = json.dumps(trading_dates, separators=(',', ':'))
    country_meta_json = json.dumps(country_meta,  separators=(',', ':'))
    country_order_json= json.dumps(COUNTRY_ORDER, separators=(',', ':'))
    max_date          = trading_dates[-1]

    # Build country button HTML
    buttons_html = '\n    '.join(
        f'<button id="btn-{code}" class="country-btn active" '
        f'onclick="toggleCountry(\'{code}\')">'
        f'{meta}</button>'
        for code, meta in country_meta.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Asian Bank Relative Performance</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f4f6f8;
      padding: 16px;
      color: #212529;
    }}
    h1 {{ font-size: 1.2rem; margin-bottom: 12px; font-weight: 600; }}

    .controls {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 14px;
      background: #fff;
      border: 1px solid #dee2e6;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 12px;
      max-width: 1200px;
    }}
    .ctrl-group {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
    .ctrl-label  {{ font-size: 0.8rem; font-weight: 600; color: #495057; white-space: nowrap; }}

    input[type=date] {{
      padding: 5px 10px;
      border: 1px solid #ced4da;
      border-radius: 5px;
      font-size: 0.87rem;
      cursor: pointer;
    }}
    .ref-note {{
      font-size: 0.74rem;
      color: #6c757d;
      font-style: italic;
    }}

    .country-btns {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }}
    .country-btns .lbl {{
      font-size: 0.8rem;
      font-weight: 600;
      color: #495057;
      margin-right: 2px;
    }}
    .country-btn {{
      padding: 5px 12px;
      border: 1px solid #ced4da;
      border-radius: 5px;
      background: #fff;
      font-size: 0.82rem;
      cursor: pointer;
      transition: background .12s, color .12s, border-color .12s;
      white-space: nowrap;
    }}
    .country-btn.active {{
      background: #0d6efd;
      color: #fff;
      border-color: #0d6efd;
    }}
    .country-btn:hover:not(.active) {{
      background: #e9ecef;
    }}

    #chart {{ max-width: 1200px; }}
  </style>
</head>
<body>

<h1>Asian Bank Relative Performance</h1>

<div class="controls">
  <!-- Reference date picker -->
  <div class="ctrl-group">
    <span class="ctrl-label">Reference Date:</span>
    <input type="date" id="ref-input"
           min="{DEFAULT_DATE}"
           max="{max_date}"
           value="{DEFAULT_DATE}">
    <span class="ref-note" id="ref-note"></span>
  </div>

  <!-- Country toggle buttons -->
  <div class="country-btns">
    <span class="lbl">Countries:</span>
    {buttons_html}
  </div>
</div>

<div id="chart"></div>

<script>{plotly_js}</script>

<script>
// ── Injected data ─────────────────────────────────────────────────────────────
const BANKS          = {banks_json};
const BANK_ORDER     = {order_json};
const TRADING_DATES  = {dates_json};
const COUNTRY_META   = {country_meta_json};
const COUNTRY_ORDER  = {country_order_json};

// ── State ─────────────────────────────────────────────────────────────────────
let selectedCountries = new Set(COUNTRY_ORDER);  // all on by default
let chartReady        = false;

// ── Helpers ───────────────────────────────────────────────────────────────────
function closestTradingDate(dateStr) {{
  let best = null;
  for (const d of TRADING_DATES) {{
    if (d <= dateStr) best = d;
    else break;
  }}
  return best;
}}

function buildTraces(refDate) {{
  return BANK_ORDER.map(name => {{
    const bank      = BANKS[name];
    const basePrice = bank.prices[refDate];
    if (!basePrice) return null;

    const dates = Object.keys(bank.prices).filter(d => d >= refDate).sort();
    const yVals = dates.map(d => parseFloat((bank.prices[d] / basePrice).toFixed(4)));

    return {{
      type: 'scatter',
      mode: 'lines',
      name: `${{name}} (${{bank.country}})`,
      x: dates,
      y: yVals,
      visible: selectedCountries.has(bank.country),
      hovertemplate: '%{{y:.3f}}x | %{{text}}<extra></extra>',
      text: Array(dates.length).fill(name),
      legendgroup: bank.country,
      legendgrouptitle: {{ text: COUNTRY_META[bank.country] }},
    }};
  }}).filter(Boolean);
}}

const layout = {{
  height: 800,
  xaxis: {{
    title: 'Date',
    rangeslider: {{ visible: true }},
    rangeselector: {{
      buttons: [
        {{ count: 1, label: '1m', step: 'month', stepmode: 'backward' }},
        {{ count: 3, label: '3m', step: 'month', stepmode: 'backward' }},
        {{ count: 6, label: '6m', step: 'month', stepmode: 'backward' }},
        {{ count: 1, label: '1y', step: 'year',  stepmode: 'backward' }},
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
  legend: {{
    groupclick: 'toggleitem',
    font: {{ size: 10 }},
    tracegroupgap: 4,
  }},
  margin: {{ b: 60, t: 50 }},
}};

const plotConfig = {{ displayModeBar: true, responsive: true }};

// ── Render ────────────────────────────────────────────────────────────────────
function render(selectedDate) {{
  const actual = closestTradingDate(selectedDate);
  if (!actual) return;

  const note = document.getElementById('ref-note');
  note.textContent = actual !== selectedDate
    ? `Using ${{actual}} (last trading day before selected date)`
    : '';

  layout.title = `Relative Performance — Base: ${{actual}} = 1.0`;

  const traces = buildTraces(actual);

  if (!chartReady) {{
    Plotly.newPlot('chart', traces, layout, plotConfig);
    chartReady = true;
  }} else {{
    Plotly.react('chart', traces, layout, plotConfig);
  }}
}}

// ── Country toggle ────────────────────────────────────────────────────────────
function toggleCountry(code) {{
  if (selectedCountries.has(code)) {{
    selectedCountries.delete(code);
  }} else {{
    selectedCountries.add(code);
  }}
  const isOn = selectedCountries.has(code);
  document.getElementById('btn-' + code).classList.toggle('active', isOn);

  if (!chartReady) return;

  // Update only visibility — no full re-render needed
  const visArr = BANK_ORDER.map(name => selectedCountries.has(BANKS[name].country));
  Plotly.restyle('chart', {{ visible: visArr }});
}}

// ── Date input ────────────────────────────────────────────────────────────────
document.getElementById('ref-input').addEventListener('change', function () {{
  render(this.value);
}});

// ── Boot ──────────────────────────────────────────────────────────────────────
render('{DEFAULT_DATE}');
</script>
</body>
</html>"""


if __name__ == '__main__':
    generate_chart()
