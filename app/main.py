# Import required libraries

import os
import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from dotenv import load_dotenv
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import datetime


# ---------------------------------------------------------------------------------------------------------------------
# Settings
load_dotenv(override=True)
API_KEY = os.environ["ALPHAVANTAGE_API_KEY"]

stock_list = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
}

interval_list = [
    "Daily",
    "Weekly",
    "Monthly",
]

period_list = [
    "1 Month",
    "3 Months",
    "6 Months",
    "1 Year",
    "5 Years",
    "10 Years",
    "max",
]

# ---------------------------------------------------------------------------------------------------------------------
# WARNING: Disabled SSL
# Workaround for SSL not woking on home laptop
try:
    # Suppress insecure request warnings
    urllib3.disable_warnings(InsecureRequestWarning)
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

# Monkey-patch requests.Session.request to default to verify=False when not provided
_original_request = requests.Session.request


def _request_no_verify(self, method, url, **kwargs):
    if "verify" not in kwargs:
        kwargs["verify"] = False
    return _original_request(self, method, url, **kwargs)


requests.Session.request = _request_no_verify


# ---------------------------------------------------------------------------------------------------------------------
# Fetch stock data
def fetch_data(symbol, interval):

    # Get the symbol from the selected stock
    symbol = stock_list[selected_stock]

    try:
        # API Endpoint to retrieve Daily Time Series
        url_market_data = f"https://www.alphavantage.co/query?function=TIME_SERIES_{interval}&symbol={symbol}&apikey={API_KEY}"
        url_overview_data = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"

        # Request the data, parse JSON response and store it in Python variable
        r = requests.get(url_market_data, timeout=10)
        r.raise_for_status()  # Raise an exception for bad status codes
        data_market = r.json()
        # st.write(data_market)

        r = requests.get(url_overview_data, timeout=10)
        r.raise_for_status()  # Raise an exception for bad status codes
        data_overview = r.json()

        return {"data_market": data_market, "data_overview": data_overview}

    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None


# ---------------------------------------------------------------------------------------------------------------------
# Create candlestick chart
def create_candlestick_chart(data, symbol, interval, period):
    """Create candlestick chart for different time intervals and periods"""
    try:
        # Determine the correct time series key based on interval
        if interval.upper() == "DAILY":
            time_series_key = "Time Series (Daily)"
        elif interval.upper() == "WEEKLY":
            time_series_key = "Weekly Time Series"
        elif interval.upper() == "MONTHLY":
            time_series_key = "Monthly Time Series"
        else:
            time_series_key = "Time Series (Daily)"  # Default fallback

        # Extract time series data
        time_series = data[time_series_key]

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()  # Sort by date ascending

        # Rename columns to standard names (handle the numbered format)
        df.columns = ["Open", "High", "Low", "Close", "Volume"]

        # Convert to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col])

        # Filter data based on selected period
        if period != "max":
            today = pd.Timestamp.now()

            if period == "1 Month":
                start_date = today - pd.DateOffset(months=1)
            elif period == "3 Months":
                start_date = today - pd.DateOffset(months=3)
            elif period == "6 Months":
                start_date = today - pd.DateOffset(months=6)
            elif period == "1 Year":
                start_date = today - pd.DateOffset(years=1)
            elif period == "5 Years":
                start_date = today - pd.DateOffset(years=5)
            elif period == "10 Years":
                start_date = today - pd.DateOffset(years=10)
            else:
                start_date = df.index.min()  # Default to all data

            # Filter dataframe
            df = df[df.index >= start_date]

        # Create candlestick chart
        fig = go.Figure(
            data=go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name=symbol,
            )
        )

        # Update layout
        fig.update_layout(
            title=f"{symbol} Stock Price - {interval} - {period}",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            height=600,
            showlegend=False,
            xaxis_rangeslider_visible=False,
        )

        return fig

    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")
        return None


# ---------------------------------------------------------------------------------------------------------------------
# MAIN

st.set_page_config(
    page_title="LAC Exchange",
    page_icon=":material/stacked_line_chart:",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------
# sidebar
with st.sidebar:

    selected_stock = st.selectbox(
        label="Select Stock",
        options=list(stock_list.keys()),
        index=0,
        help="Choose a stock to display",
    )

    selected_interval = st.selectbox(
        label="Interval",
        options=interval_list,
        index=0,
        placeholder="Select interval...",
    )

    selected_period = st.selectbox(
        label="Period",
        options=period_list,
        index=0,
        placeholder="Select period...",
    )

    st.write("")
    st.write("")
    st.write("")
    refresh_btn = st.button("Refresh Data")

    # Initialize session state
    if "last_refresh_time" not in st.session_state:
        st.session_state.last_refresh_time = None

    # Create a placeholder for the last refresh time that will be updated later
    refresh_placeholder = st.empty()

# Main content area
st.html(
    f"<p style='text-align:center;font-size:35px;font-weight:900'>📈 Stock Data Dashboard 📉</p>"
)


# ---------------------------------------------
# Main Content
with st.spinner(f"Fetching data for {selected_stock}..."):

    result = fetch_data(selected_stock, selected_interval)

    if result:
        data_market = result["data_market"]
        data_overview = result["data_overview"]

        st.session_state.last_refresh_time = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        with refresh_placeholder:
            if st.session_state.last_refresh_time:
                st.text(f"Last Refresh: {st.session_state.last_refresh_time}")
            else:
                st.text("Last Refresh: Never")

        # ---------------------------------------------
        # Stock Information
        st.title(f"{selected_stock}")
        st.subheader(f"Symbol: {data_overview['Symbol']}")

        with st.expander("More Info"):
            col1, col2 = st.columns([0.3, 0.7], gap="small")
            with col1:
                st.write(f"AssetType: **{data_overview['AssetType']}**")
                st.write(f"Exchange: **{data_overview['Exchange']}**")
                st.write(f"Currency: **{data_overview['Currency']}**")
                st.write(f"Country: **{data_overview['Country']}**")
                st.write(f"Sector: **{data_overview['Sector']}**")
                st.write(f"WebSite: **{data_overview['OfficialSite']}**")
            with col2:
                st.write(f"Asset Type: {data_overview['Description']}")

        # ---------------------------------------------
        # Candle Stick Chart
        fig = create_candlestick_chart(
            data_market, data_overview["Symbol"], selected_interval, selected_period
        )
        if fig:
            st.plotly_chart(fig, use_container_width=True)

            # Display recent data table
            # Determine the correct time series key based on interval
            if selected_interval.upper() == "DAILY":
                time_series_key = "Time Series (Daily)"
            elif selected_interval.upper() == "WEEKLY":
                time_series_key = "Weekly Time Series"
            elif selected_interval.upper() == "MONTHLY":
                time_series_key = "Monthly Time Series"
            else:
                time_series_key = "Time Series (Daily)"

            time_series = data_market[time_series_key]
            df = pd.DataFrame.from_dict(time_series, orient="index")
            df.index = pd.to_datetime(df.index)
            df = df.sort_index(ascending=False)  # Most recent first
            df.columns = ["Open", "High", "Low", "Close", "Volume"]

            # Convert to numeric and format
            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(df[col]).round(2)
            df["Volume"] = pd.to_numeric(df["Volume"]).astype(int)

            # Filter table data based on selected period
            if selected_period != "max":
                today = pd.Timestamp.now()

                if selected_period == "1 Month":
                    start_date = today - pd.DateOffset(months=1)
                elif selected_period == "3 Months":
                    start_date = today - pd.DateOffset(months=3)
                elif selected_period == "6 Months":
                    start_date = today - pd.DateOffset(months=6)
                elif selected_period == "1 Year":
                    start_date = today - pd.DateOffset(years=1)
                elif selected_period == "5 Years":
                    start_date = today - pd.DateOffset(years=5)
                elif selected_period == "10 Years":
                    start_date = today - pd.DateOffset(years=10)
                else:
                    start_date = df.index.min()

                df = df[df.index >= start_date]

            st.write(f"### Recent {selected_interval} Trading Data - {selected_period}")
            st.dataframe(df.head(10), use_container_width=True)
