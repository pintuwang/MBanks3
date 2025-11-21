import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. Define Banks by Country
tickers_my = {
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

tickers_sg = {
    'DBS': 'D05.SI',
    'OCBC': 'O39.SI',
    'UOB': 'U11.SI'
}

# Combine for downloading
all_tickers_map = {**tickers_my, **tickers_sg}

def generate_chart():
    print("Fetching data...")
    
    # 2. Fetch Data (auto_adjust=False to keep 'Adj Close')
    # We fetch a bit earlier to ensure we have data for the July 1st start
    data = yf.download(list(all_tickers_map.values()), start="2024-06-25", auto_adjust=False)['Adj Close']
    
    # Filter start date
    start_date = '2024-07-01'
    data = data[data.index >= start_date]
    data = data.ffill() # Fill missing data

    # 3. Calculate Relative Price (Rebase to 1.0)
    # Note: This works for cross-country comparison because it normalizes currency differences.
    # We look at % performance, not absolute price (MYR vs SGD).
    base_prices = data.iloc[0]
    relative_data = data.div(base_prices)

    # 4. Create Plotly Chart
    fig = go.Figure()

    # We need to track how many traces we add for each group to build the buttons later
    my_trace_count = 0
    sg_trace_count = 0

    # Add Malaysia Traces first
    for bank_name, ticker in tickers_my.items():
        if ticker in relative_data.columns:
            fig.add_trace(go.Scatter(
                x=relative_data.index,
                y=relative_data[ticker],
                mode='lines',
                name=f"{bank_name} (MY)",
                hovertemplate='%{y:.2f}x | %{text}<extra></extra>',
                text=[bank_name] * len(relative_data),
                visible=True # Default visible
            ))
            my_trace_count += 1

    # Add Singapore Traces second
    for bank_name, ticker in tickers_sg.items():
        if ticker in relative_data.columns:
            fig.add_trace(go.Scatter(
                x=relative_data.index,
                y=relative_data[ticker],
                mode='lines',
                name=f"{bank_name} (SG)",
                hovertemplate='%{y:.2f}x | %{text}<extra></extra>',
                text=[bank_name] * len(relative_data),
                visible=True # Default visible
            ))
            sg_trace_count += 1

    # 5. Create Buttons for Filter Logic
    # 'visible' accepts a list of booleans corresponding to the order of traces added
    
    # "All": Everyone is True
    mask_all = [True] * (my_trace_count + sg_trace_count)
    
    # "Malaysia": First N are True, rest False
    mask_my = [True] * my_trace_count + [False] * sg_trace_count
    
    # "Singapore": First N are False, rest True
    mask_sg = [False] * my_trace_count + [True] * sg_trace_count

    updatemenus = [
        dict(
            type="buttons",
            direction="left",
            x=0.5,
            y=-0.4, # Position below the slider (which is usually around -0.1 to -0.2)
            xanchor='center',
            yanchor='top',
            active=0,
            buttons=list([
                dict(label="All",
                     method="update",
                     args=[{"visible": mask_all},
                           {"title": f"Relative Performance: All Banks (Base: {start_date})"}]),
                dict(label="Malaysia",
                     method="update",
                     args=[{"visible": mask_my},
                           {"title": f"Relative Performance: Malaysia Banks (Base: {start_date})"}]),
                dict(label="Singapore",
                     method="update",
                     args=[{"visible": mask_sg},
                           {"title": f"Relative Performance: Singapore Banks (Base: {start_date})"}]),
            ]),
        )
    ]

    # 6. Final Styling
    fig.update_layout(
        title=f"Relative Performance of Banks (Base: {start_date} = 1.0)",
        xaxis_title="Date",
        yaxis_title="Relative Performance (1.0 = Base)",
        hovermode="x unified",
        template="plotly_white",
        legend_title="Banks",
        height=750,
        updatemenus=updatemenus,
        # Add extra bottom margin to fit the buttons
        margin=dict(b=150)
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

    print("Generating index.html...")
    fig.write_html("index.html")
    print("Done.")

if __name__ == "__main__":
    generate_chart()
