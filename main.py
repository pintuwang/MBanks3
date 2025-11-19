import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# 1. Define Top 10 KLSE Banks (Tickers usually end in .KL)
tickers = {
    'Maybank': '1155.KL',
    'Public Bank': '1295.KL',
    'CIMB': '1023.KL',
    'Hong Leong Bank': '5819.KL',
    'RHB Bank': '1066.KL',
    'Hong Leong FG': '1082.KL',
    'AmBank': '1015.KL',
    'Alliance Bank': '2488.KL',
    'Bank Islam': '5258.KL',
    'Affin Bank': '5185.KL'
}

def generate_chart():
    print("Fetching data...")
    
    # --- THE FIX IS HERE ---
    # We added 'auto_adjust=False' to ensure 'Adj Close' column exists
    data = yf.download(list(tickers.values()), start="2024-06-25", auto_adjust=False)['Adj Close']
    
    # Filter to start exactly from or after July 1, 2024
    start_date = '2024-07-01'
    data = data[data.index >= start_date]
    
    # Fill missing data (weekends/holidays) forward to maintain line continuity
    data = data.ffill()

    # 3. Calculate Relative Price (Rebase to 1.0 or 100%)
    # Formula: Current Price / Price on July 1st
    base_prices = data.iloc[0]
    relative_data = data.div(base_prices)

    # 4. Create Plotly Chart
    fig = go.Figure()

    for bank_name, ticker in tickers.items():
        if ticker in relative_data.columns:
            fig.add_trace(go.Scatter(
                x=relative_data.index,
                y=relative_data[ticker],
                mode='lines',
                name=bank_name,
                hovertemplate='%{y:.2f}x relative to base<extra></extra>'
            ))

    # 5. Styling & Interactivity
    fig.update_layout(
        title=f"Relative Performance of Top 10 KLSE Banks (Base: {start_date} = 1.0)",
        xaxis_title="Date",
        yaxis_title="Relative Price (1.0 = No Change)",
        hovermode="x unified", 
        template="plotly_white",
        legend_title="Click to Hide/Show",
        height=700
    )

    # Add Range Slider
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    # 6. Export to HTML
    print("Generating index.html...")
    fig.write_html("index.html")
    print("Done.")

if __name__ == "__main__":
    generate_chart()
