"""
Options Opportunities Scanner - Streamlit UI
Find stocks with unusual options activity, IV expansion, and credit spread setups.
"""

import streamlit as st
import pandas as pd
from scanner import (
    scan_watchlist, 
    WATCHLIST, 
    find_unusual_activity, 
    find_iv_expansion,
    find_credit_spread_setup,
    get_stock_info
)
from datetime import datetime
import time

st.set_page_config(
    page_title="Options Scanner",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Options Opportunities Scanner")
st.markdown("Find stocks with unusual options activity, IV expansion, and credit spread setups.")

# Sidebar
st.sidebar.header("Settings")

scan_button = st.sidebar.button("🔄 Scan Now", type="primary")

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
    st.session_state.last_scan = None

if scan_button:
    with st.spinner("Scanning watchlist... (this may take a minute)"):
        try:
            st.session_state.results = scan_watchlist()
            st.session_state.last_scan = datetime.now()
            st.success("Scan complete!")
        except Exception as e:
            st.error(f"Scan failed: {e}")

# Show results
if st.session_state.results:
    results = st.session_state.results
    
    st.markdown(f"**Last scan:** {st.session_state.last_scan.strftime('%H:%M:%S')}")
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["🚨 Unusual Activity", "💥 IV Expansion", "📊 Credit Spreads"])
    
    with tab1:
        st.subheader("🚨 Unusual Options Activity")
        if results['unusual_activity']:
            df = pd.DataFrame(results['unusual_activity'])
            df = df.sort_values('unusual_calls', ascending=False)
            
            # Color coding
            def color_change(val):
                color = 'green' if val > 0 else 'red' if val < 0 else ''
                return f'color: {color}'
            
            st.dataframe(
                df.style.applymap(color_change, subset=['change_pct'])
                       .format({
                           'price': '${:.2f}',
                           'change_pct': '{:+.2f}%',
                           'put_call_ratio': '{:.2f}'
                       }),
                use_container_width=True
            )
            
            st.markdown("### Interpretation")
            st.info("""
            - **High volume/OpenInterest ratio** = unusual trading activity
            - **Put/Call ratio > 1** = more put buying (bearish)
            - **Put/Call ratio < 1** = more call buying (bullish)
            """)
        else:
            st.info("No unusual activity found.")
    
    with tab2:
        st.subheader("💥 IV Expansion")
        if results['iv_expansion']:
            df = pd.DataFrame(results['iv_expansion'])
            df = df.sort_values('iv_premium', ascending=False)
            
            def color_iv(val):
                return 'color: orange' if val > 50 else 'color: yellow' if val > 30 else ''
            
            st.dataframe(
                df.style.applymap(color_iv, subset=['iv_premium'])
                       .format({
                           'price': '${:.2f}',
                           'iv': '{:.1f}%',
                           'hv20': '{:.1f}%',
                           'iv_premium': '{:+.1f}%',
                           'change_pct': '{:+.2f}%'
                       }),
                use_container_width=True
            )
            
            st.markdown("### Interpretation")
            st.info("""
            - **IV > HV** = options are expensive relative to stock movement
            - **High IV Premium** = good for selling options (credit spreads, iron condors)
            - IV expansion often precedes big moves
            """)
        else:
            st.info("No significant IV expansion found.")
    
    with tab3:
        st.subheader("📊 Credit Spread Setups")
        if results['credit_spreads']:
            df = pd.DataFrame(results['credit_spreads'])
            df = df.sort_values('put_risk_reward', ascending=True)
            
            st.dataframe(
                df.style.format({
                    'price': '${:.2f}',
                    'put_credit': '${:.2f}',
                    'put_risk': '${:.2f}',
                    'put_risk_reward': '{:.2f}',
                    'call_credit': '${:.2f}',
                    'call_risk': '${:.2f}',
                    'call_risk_reward': '{:.2f}',
                }),
                use_container_width=True
            )
            
            st.markdown("### Interpretation")
            st.info("""
            - **Credit** = max profit per spread
            - **Risk** = max loss per spread
            - **Risk/Reward** = lower is better (1:1 or better preferred)
            - Put spreads = bullish, Call spreads = bearish
            """)
        else:
            st.info("No credit spread setups found with sufficient credit.")
    
    # Individual stock lookup
    st.divider()
    st.subheader("🔍 Individual Stock Lookup")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        lookup_ticker = st.text_input("Ticker", value="SPY").upper()
    with col2:
        lookup_button = st.button("Analyze")
    
    if lookup_button and lookup_ticker:
        with st.spinner(f"Analyzing {lookup_ticker}..."):
            # Get all data
            stock_info = get_stock_info(lookup_ticker)
            ua = find_unusual_activity(lookup_ticker)
            iv = find_iv_expansion(lookup_ticker)
            cs = find_credit_spread_setup(lookup_ticker)
            
            if stock_info:
                st.markdown(f"### {stock_info['name']} ({lookup_ticker})")
                st.markdown(f"**Price:** ${stock_info['price']:.2f} ({stock_info['change_pct']:+.2f}%)")
                st.markdown(f"**Sector:** {stock_info['sector']}")
                st.markdown(f"**Volume:** {stock_info['volume']:,}")
            
            if ua:
                st.markdown("#### 🚨 Unusual Activity")
                st.write(f"- Unusual calls: {ua['unusual_calls']}")
                st.write(f"- Unusual puts: {ua['unusual_puts']}")
                st.write(f"- Total call volume: {ua['total_call_volume']:,}")
                st.write(f"- Total put volume: {ua['total_put_volume']:,}")
                st.write(f"- Put/Call ratio: {ua['put_call_ratio']:.2f}")
            
            if iv:
                st.markdown("#### 💥 IV Analysis")
                st.write(f"- Implied Volatility: {iv['iv']:.1f}%")
                st.write(f"- Historical Volatility (20d): {iv['hv20']:.1f}%")
                st.write(f"- IV Premium: {iv['iv_premium']:+.1f}%")
            
            if cs:
                st.markdown("#### 📊 Credit Spread Setups")
                st.write(f"- Expiration: {cs['expiration']}")
                st.write(f"")
                st.write(f"**Put Credit Spread (Bullish):**")
                st.write(f"- Credit: ${cs['put_credit']:.2f}")
                st.write(f"- Risk: ${cs['put_risk']:.2f}")
                st.write(f"- Risk/Reward: {cs['put_risk_reward']:.2f}" if cs['put_risk_reward'] else "")
                st.write(f"")
                st.write(f"**Call Credit Spread (Bearish):**")
                st.write(f"- Credit: ${cs['call_credit']:.2f}")
                st.write(f"- Risk: ${cs['call_risk']:.2f}")
                st.write(f"- Risk/Reward: {cs['call_risk_reward']:.2f}" if cs['call_risk_reward'] else "")

else:
    # Initial state
    st.info("👈 Click 'Scan Now' in the sidebar to find opportunities!")
    
    st.markdown("""
    ### How It Works
    
    This scanner looks for three types of opportunities:
    
    1. **Unusual Activity** - Stocks with high volume relative to open interest
       - Could indicate insider activity or institutional positioning
    
    2. **IV Expansion** - Options IV significantly higher than historical volatility
       - Good for selling options (credit spreads, iron condors)
    
    3. **Credit Spread Setups** - Defined-risk setups near support/resistance
       - Bullish: Put credit spreads
       - Bearish: Call credit spreads
    
    ### Watchlist
    """)
    st.write(", ".join(WATCHLIST))
