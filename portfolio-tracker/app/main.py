import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal, init_db
from app.database.models import User, Portfolio, Transaction, TaxClass, TransactionType
from app.services.price_service import PriceService
from app.services.portfolio_service import PortfolioService
from app.services.user_service import UserService
from app.services.risk_service import RiskService
from app.services.optimization_service import OptimizationService
from app.services.tax_service import TaxService
from app.services.broker_service import ImportService

init_db()

SESSION_FILE = "data/session.json"

def save_session(user_id, username):
    with open(SESSION_FILE, 'w') as f:
        json.dump({"user_id": user_id, "username": username}, f)

def load_session():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return None

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide"
)

if "logged_in" not in st.session_state:
    saved = load_session()
    if saved:
        st.session_state.logged_in = True
        st.session_state.user_id = saved["user_id"]
        st.session_state.username = saved["username"]
    else:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

def show_login_page():
    st.title("📈 Portfolio Tracker")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login", key="login_btn"):
            if login_username and login_password:
                db = SessionLocal()
                service = UserService(db)
                user, message = service.login(login_username, login_password)
                db.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user.id
                    st.session_state.username = user.username
                    save_session(user.id, user.username)
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill all fields")
    
    with tab2:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_user")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_password2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
        
        if st.button("Register", key="register_btn"):
            if reg_username and reg_email and reg_password:
                if reg_password != reg_password2:
                    st.error("Passwords do not match")
                else:
                    db = SessionLocal()
                    service = UserService(db)
                    user, message = service.register(reg_username, reg_email, reg_password)
                    db.close()
                    
                    if user:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)
            else:
                st.error("Please fill all fields")

def show_dashboard():
    import time as time_module
    
    # Şirket isimleri dictionary
    COMPANY_NAMES = {
        "ACHR": "Archer Aviation", "ACIC": "Archer Aviation", "AMD": "Advanced Micro Devices",
        "AMZN": "Amazon", "ARRY": "Array Technologies", "BABA": "Alibaba", "BIDU": "Baidu",
        "BITF": "Bitfarms", "BLK": "BlackRock", "BMRG": "Eose Energy", "CCCX": "Churchill Capital",
        "CCJ": "Cameco", "CLPT": "ClearPoint Neuro", "COIN": "Coinbase", "COST": "Costco",
        "CRCL": "Circle", "CRSP": "CRISPR Therapeutics", "CRWD": "CrowdStrike", "CRWV": "CoreWeave",
        "DMYI": "IonQ", "DMYQ": "Planet Labs", "DXYZ": "Destiny Tech100", "FB": "Meta Platforms",
        "FLY1": "Firefly Aerospace", "GNPK": "Redwire", "GOOGL": "Alphabet", "GS": "Goldman Sachs",
        "HOp": "Thales", "HOOD": "Robinhood", "IBM": "IBM", "IPAX": "Intuitive Machines",
        "IPOE": "SoFi", "IREN": "Iris Energy", "ISRG": "Intuitive Surgical", "JPM": "JPMorgan Chase",
        "KOZd": "Kongsberg Gruppen", "KTOS": "Kratos Defense", "LEU": "Centrus Energy",
        "MAR": "Marriott", "MSFT": "Microsoft", "MSTR": "MicroStrategy", "MTXd": "MTU Aero Engines",
        "NFLX": "Netflix", "NNN": "NNN REIT", "NVDA": "NVIDIA", "O": "Realty Income",
        "OHBd": "OHB SE", "ORCL": "Oracle", "PFE": "Pfizer", "PONY": "Pony AI",
        "R3NKd": "Renk Group", "RBLX": "Roblox", "RBRK": "Rubrik", "RCAT": "Red Cat",
        "RHMd": "Rheinmetall", "S": "SentinelOne", "SCCO": "Southern Copper", "TSLA": "Tesla",
        "UUUU": "Energy Fuels", "VACQ": "Rocket Lab", "VOYG": "Voyager", "WGLDd": "Gold ETC",
        "XIACY": "Xiaomi", "XPEV": "XPeng", "YNDX": "Nebius", "ZK": "ZEEKR"
    }
    
    SECTORS = {
        "Space": ["VACQ", "IPAX", "GNPK", "DMYQ", "FLY1", "VOYG", "OHBd", "DXYZ"],
        "Defence": ["RHMd", "R3NKd", "KOZd", "HOp", "MTXd"],
        "AI & Tech": ["AMD"],
        "MAG7": ["NVDA", "MSFT", "GOOGL", "AMZN"],
        "Quantum": ["DMYI", "IBM", "CCCX"],
        "Self-driving": ["BIDU", "PONY"],
        "Data Center": ["ORCL", "CRWV", "YNDX", "IREN", "BITF"],
        "Cyber Security": ["CRWD", "S", "RBRK"],
        "Robotic": ["XPEV", "TSLA", "ISRG"],
        "Battery": ["ZK", "BMRG", "ARRY"],
        "China Tech": ["BABA", "XIACY"],
        "Nuclear": ["LEU", "UUUU", "CCJ"],
        "Crypto": ["COIN", "MSTR", "HOOD", "CRCL"],
        "Finance": ["JPM", "GS", "BLK", "IPOE"],
        "Healthcare": ["PFE", "CRSP", "CLPT"],
        "Consumer": ["COST", "NFLX", "MAR"],
        "Game": ["RBLX"],
        "REIT": ["NNN", "O"],
        "Commodity": ["SCCO", "WGLDd"],
        "Drone": ["RCAT", "KTOS", "ACIC"],
        "Other": ["FB"]
    }
    
    # Sidebar
    st.sidebar.write(f"👤 Welcome, **{st.session_state.username}**")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh", key="refresh_btn"):
            st.session_state.cache_time = 0
            st.rerun()
    with col2:
        if st.button("Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            clear_session()
            st.rerun()
    
    st.sidebar.divider()
    
    # Sidebar: Stock Performance
    st.sidebar.header("📊 Stock Performance")
    
    sort_option = st.sidebar.selectbox(
        "Sort by:",
        ["Position Size ($)", "P/L Amount ($)", "P/L Percent (%)"],
        index=0,
        key="sort_option"
    )
    
    db_sidebar = SessionLocal()
    user_service_sidebar = UserService(db_sidebar)
    portfolio_sidebar = user_service_sidebar.get_user_portfolio(st.session_state.user_id)
    
    if portfolio_sidebar:
        from app.services.trading212_service import Trading212Service
        
        t212_sidebar = Trading212Service(db_sidebar)
        live_positions = t212_sidebar.get_portfolio()
        realized_by_symbol = t212_sidebar.get_realized_pnl_by_symbol(portfolio_sidebar.id)
        
        if live_positions:
            for pos in live_positions:
                ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                qty = pos.get('quantity', 0)
                current_price = pos.get('currentPrice', 0)
                avg_price = pos.get('averagePrice', 0)
                unrealized = pos.get('ppl', 0) or 0
                realized = realized_by_symbol.get(ticker, 0)
                
                pos['position_value'] = qty * current_price
                pos['total_pnl'] = unrealized + realized
                cost_basis = qty * avg_price
                pos['pnl_pct'] = (unrealized / cost_basis * 100) if cost_basis > 0 else 0
            
            if sort_option == "Position Size ($)":
                sorted_pos = sorted(live_positions, key=lambda x: x.get('position_value', 0), reverse=True)
            elif sort_option == "P/L Amount ($)":
                sorted_pos = sorted(live_positions, key=lambda x: x.get('total_pnl', 0), reverse=True)
            else:
                sorted_pos = sorted(live_positions, key=lambda x: x.get('pnl_pct', 0), reverse=True)
            
            for pos in sorted_pos:
                ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                qty = pos.get('quantity', 0)
                current_price = pos.get('currentPrice', 0)
                avg_price = pos.get('averagePrice', 0)
                unrealized = pos.get('ppl', 0) or 0
                pnl_pct = pos.get('pnl_pct', 0)
                position_value = pos.get('position_value', 0)
                total_pnl = pos.get('total_pnl', 0)
                
                if qty > 0.001:
                    realized = realized_by_symbol.get(ticker, 0)
                    cost_basis = qty * avg_price
                    u_pct = (unrealized / cost_basis * 100) if cost_basis > 0 else 0
                    total_pct = (total_pnl / cost_basis * 100) if cost_basis > 0 else 0
                    
                    company = COMPANY_NAMES.get(ticker, ticker)
                    
                    if sort_option == "Position Size ($)":
                        emoji = "💰"
                        header_text = f"{emoji} {company} (${position_value:,.0f})"
                    elif sort_option == "P/L Amount ($)":
                        emoji = "🟢" if total_pnl >= 0 else "🔴"
                        header_text = f"{emoji} {company} (${total_pnl:+,.0f})"
                    else:
                        emoji = "🟢" if pnl_pct >= 0 else "🔴"
                        header_text = f"{emoji} {company} ({pnl_pct:+.1f}%)"
                    
                    with st.sidebar.expander(header_text):
                        st.write(f"**Ticker:** {ticker}")
                        st.write(f"**Shares:** {qty:.4f}")
                        st.write(f"**Value:** ${position_value:,.2f}")
                        st.write(f"**Avg Price:** ${avg_price:.2f}")
                        st.write(f"**Current:** ${current_price:.2f}")
                        st.divider()
                        u_color = "🟢" if unrealized >= 0 else "🔴"
                        r_color = "🟢" if realized >= 0 else "🔴"
                        t_color = "🟢" if total_pnl >= 0 else "🔴"
                        st.write(f"**Unrealized:** {u_color} ${unrealized:,.2f} ({u_pct:+.1f}%)")
                        st.write(f"**Realized:** {r_color} ${realized:,.2f}")
                        st.write(f"**Total P/L:** {t_color} ${total_pnl:,.2f} ({total_pct:+.1f}%)")
        else:
            st.sidebar.info("Connect to Trading212 for live data")
    
    db_sidebar.close()
    
    st.title("📈 Portfolio Tracker")
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Dashboard", "📊 Sectors", "⚖️ Optimize",
        "🧾 Tax Calculator", "📥 Import", "⚙️ Settings", "📈 Risk Analysis", "🎯 Risk Management"
    ])
    
    db = SessionLocal()
    user_service = UserService(db)
    user = db.query(User).filter(User.id == st.session_state.user_id).first()
    portfolio = user_service.get_user_portfolio(st.session_state.user_id)
    
    if portfolio:
        service = PortfolioService(db)
        holdings = service.calculate_holdings(portfolio.id)
        
        price_service = PriceService()
        current_prices = {}
        
        for sym in holdings.keys():
            if holdings[sym]["quantity"] > 0:
                result = price_service.get_current_price(sym)
                if "error" not in result:
                    current_prices[sym] = result["price"]
        
        summary = service.get_portfolio_summary(portfolio.id, current_prices)
        active_symbols = [sym for sym, data in holdings.items() if data["quantity"] > 0]
        
        # Tab 1: Dashboard
        with tab1:
            from app.services.trading212_service import Trading212Service
            t212 = Trading212Service(db)
            
            api_data = None
            connection_test = t212.test_connection()
            if connection_test["success"]:
                api_data = connection_test["data"]
            
            if api_data:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Asset", f"${api_data.get('total', 0):,.2f}")
                with col2:
                    st.metric("Cash", f"${api_data.get('free', 0):,.2f}")
                with col3:
                    st.metric("Investment", f"${api_data.get('invested', 0):,.2f}")
                with col4:
                    st.metric("Pending Orders", f"${api_data.get('blocked', 0):,.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    ppl = api_data.get('ppl', 0)
                    st.metric("Unrealized P/L", f"${ppl:,.2f}", delta=f"{(ppl/api_data.get('invested', 1)*100):.2f}%" if api_data.get('invested', 0) > 0 else "0%")
                with col2:
                    result = api_data.get('result', 0)
                    st.metric("Realized P/L", f"${result:,.2f}")
                
                st.success("✅ Live data from Trading212 API")
            else:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Value", f"${summary['total_value']:,.2f}")
                with col2:
                    st.metric("Total Cost", f"${summary['total_cost']:,.2f}")
                with col3:
                    pnl_pct = (summary['total_unrealized_pnl']/summary['total_cost']*100) if summary['total_cost'] > 0 else 0
                    st.metric("Unrealized PnL", f"${summary['total_unrealized_pnl']:,.2f}", delta=f"{pnl_pct:.2f}%")
                with col4:
                    st.metric("Realized PnL", f"${summary['total_realized_pnl']:,.2f}")
                st.warning("⚠️ Offline mode - Using calculated values")
            
            st.divider()
            
            live_positions = t212.get_portfolio()
            
            st.subheader("📊 Daily Summary")
            
            if live_positions:
                from datetime import datetime, timedelta
                
                daily_unrealized = sum(pos.get('ppl', 0) or 0 for pos in live_positions)
                daily_fx_impact = sum(pos.get('fxPpl', 0) or 0 for pos in live_positions)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    yesterday = datetime.now() - timedelta(days=1)
                    recent_transactions = [tx for tx in service.get_portfolio_transactions(portfolio.id) 
                                          if tx.date and tx.date >= yesterday]
                    
                    st.write("**Last 24h Transactions:**")
                    if recent_transactions:
                        daily_buy_total = 0
                        daily_sell_total = 0
                        
                        for tx in recent_transactions[:10]:
                            tx_icon = "🟢" if tx.transaction_type.value == "buy" else "🔴"
                            tx_time = tx.date.strftime("%m-%d %H:%M") if tx.date else ""
                            tx_value = tx.quantity * tx.price
                            
                            if tx.transaction_type.value == "buy":
                                daily_buy_total += tx_value
                            else:
                                daily_sell_total += tx_value
                            
                            st.write(f"{tx_icon} {tx_time} | {tx.transaction_type.value.upper()} {tx.quantity:.2f} **{tx.symbol}** @ ${tx.price:.2f}")
                        
                        st.divider()
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Bought (24h)", f"${daily_buy_total:,.2f}")
                        with col_b:
                            st.metric("Sold (24h)", f"${daily_sell_total:,.2f}")
                    else:
                        st.info("No transactions in last 24 hours")
                
                with col2:
                    sorted_by_pnl = sorted(live_positions, key=lambda x: x.get('ppl', 0) or 0, reverse=True)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write("**Top Gainers:**")
                        for pos in sorted_by_pnl[:3]:
                            ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                            ppl = pos.get('ppl', 0) or 0
                            if ppl > 0:
                                company = COMPANY_NAMES.get(ticker, ticker)
                                st.write(f"🟢 **{company}**: +${ppl:.2f}")
                    
                    with col_b:
                        st.write("**Top Losers:**")
                        for pos in sorted_by_pnl[-3:]:
                            ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                            ppl = pos.get('ppl', 0) or 0
                            if ppl < 0:
                                company = COMPANY_NAMES.get(ticker, ticker)
                                st.write(f"🔴 **{company}**: ${ppl:.2f}")
                    
                    st.divider()
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Total Unrealized", f"${daily_unrealized:,.2f}")
                    with col_b:
                        st.metric("FX Impact", f"${daily_fx_impact:,.2f}")
            else:
                st.info("No positions data available")
            
            # Allocation Chart
            st.divider()
            if live_positions:
                st.subheader("📊 Portfolio Allocation")
                allocation_data = []
                for pos in live_positions:
                    ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                    value = pos.get('quantity', 0) * pos.get('currentPrice', 0)
                    if value > 10:
                        company = COMPANY_NAMES.get(ticker, ticker)
                        allocation_data.append({"Symbol": ticker, "Company": company, "Value": value})
                
                if allocation_data:
                    df_alloc = pd.DataFrame(allocation_data)
                    df_alloc = df_alloc.sort_values('Value', ascending=False)
                    
                    total_value = df_alloc['Value'].sum()
                    
                    top10 = df_alloc.head(10).copy()
                    other_value = df_alloc.iloc[10:]['Value'].sum() if len(df_alloc) > 10 else 0
                    
                    if other_value > 0:
                        other_row = pd.DataFrame([{"Symbol": "OTHER", "Company": "Other", "Value": other_value}])
                        chart_data = pd.concat([top10, other_row], ignore_index=True)
                    else:
                        chart_data = top10
                    
                    chart_data['Label'] = chart_data.apply(
                        lambda x: f"{x['Symbol']}<br>{x['Value']/total_value*100:.1f}%", axis=1
                    )
                    
                    fig = px.pie(
                        chart_data, 
                        values='Value', 
                        names='Label',
                        hole=0.3,
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    
                    fig.update_traces(
                        textposition='inside',
                        textinfo='label',
                        textfont_size=12,
                        insidetextorientation='horizontal'
                    )
                    
                    fig.update_layout(
                        showlegend=False,
                        height=500,
                        margin=dict(t=20, b=20, l=20, r=20)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        # Tab 2: Sectors
        with tab2:
            st.subheader("📊 My Stocks by Sector")
            
            from app.services.trading212_service import Trading212Service
            t212_sector = Trading212Service(db)
            
            sector_positions = t212_sector.get_portfolio()
            realized_pnl = t212_sector.get_realized_pnl_by_symbol(portfolio.id)
            
            if sector_positions and len(sector_positions) > 0:
                stocks_by_sector = {sector: [] for sector in SECTORS}
                
                for pos in sector_positions:
                    ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                    qty = pos.get('quantity', 0)
                    
                    if qty > 0.001:
                        found_sector = "Other"
                        for sector, symbols in SECTORS.items():
                            if ticker in symbols:
                                found_sector = sector
                                break
                        
                        stocks_by_sector[found_sector].append(pos)
                
                sector_tabs = [s for s in SECTORS.keys() if stocks_by_sector[s]]
                
                if sector_tabs:
                    sector_tab_objects = st.tabs(sector_tabs)
                    
                    for i, sector in enumerate(sector_tabs):
                        with sector_tab_objects[i]:
                            sector_stocks = stocks_by_sector[sector]
                            sector_total_value = 0
                            sector_total_pnl = 0
                            
                            for pos in sorted(sector_stocks, key=lambda x: x.get('quantity', 0) * x.get('currentPrice', 0), reverse=True):
                                full_ticker = pos.get('ticker', '')
                                ticker = full_ticker.replace('_US_EQ', '').replace('_EQ', '')
                                qty = pos.get('quantity', 0)
                                current_price = pos.get('currentPrice', 0)
                                avg_price = pos.get('averagePrice', 0)
                                unrealized = pos.get('ppl', 0) or 0
                                realized = realized_pnl.get(ticker, 0)
                                total_pnl = unrealized + realized
                                value = qty * current_price
                                cost_basis = qty * avg_price
                                
                                sector_total_value += value
                                sector_total_pnl += total_pnl
                                
                                change_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                                total_pct = (total_pnl / cost_basis * 100) if cost_basis > 0 else 0
                                
                                emoji = "🟢" if total_pnl >= 0 else "🔴"
                                price_emoji = "🟢" if change_pct >= 0 else "🔴"
                                company_name = COMPANY_NAMES.get(ticker, ticker)
                                
                                with st.expander(f"{emoji} **{company_name}** ({ticker}) | ${current_price:.2f} ({price_emoji} {change_pct:+.2f}%)"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write(f"**Shares:** {qty:.4f}")
                                        st.write(f"**Value:** ${value:,.2f}")
                                        st.write(f"**Avg Price:** ${avg_price:.2f}")
                                        st.write(f"**Current:** ${current_price:.2f}")
                                    
                                    with col2:
                                        u_color = "🟢" if unrealized >= 0 else "🔴"
                                        r_color = "🟢" if realized >= 0 else "🔴"
                                        
                                        u_pct = (unrealized / cost_basis * 100) if cost_basis > 0 else 0
                                        
                                        st.write(f"**Unrealized:** {u_color} ${unrealized:,.2f} ({u_pct:+.1f}%)")
                                        st.write(f"**Realized:** {r_color} ${realized:,.2f}")
                                        st.write(f"**Total P/L:** {emoji} **${total_pnl:,.2f}** ({total_pct:+.1f}%)")
                            
                            st.divider()
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(f"{sector} Total Value", f"${sector_total_value:,.2f}")
                            with col2:
                                st.metric(f"{sector} Total P/L", f"${sector_total_pnl:,.2f}")
                else:
                    st.info("No positions found in defined sectors")
            else:
                st.warning("Could not load portfolio. Please wait and refresh.")
        
        # Tab 3: Portfolio Optimization
        with tab3:
            st.subheader("⚖️ Portfolio Optimization")
            
            if len(active_symbols) >= 2:
                st.write("Optimize your portfolio allocation using Modern Portfolio Theory.")
                
                optimization_type = st.selectbox(
                    "Optimization Strategy",
                    ["Max Sharpe Ratio", "Min Volatility", "Target Return"],
                    key="opt_strategy"
                )
                
                target_return = None
                if optimization_type == "Target Return":
                    target_return = st.slider("Target Annual Return (%)", 5, 30, 15, key="target_return") / 100
                
                if st.button("Optimize Portfolio", key="optimize_btn"):
                    with st.spinner("Optimizing..."):
                        opt_service = OptimizationService()
                        
                        if optimization_type == "Max Sharpe Ratio":
                            result, error = opt_service.optimize_max_sharpe(active_symbols)
                        elif optimization_type == "Min Volatility":
                            result, error = opt_service.optimize_min_volatility(active_symbols)
                        else:
                            result, error = opt_service.optimize_target_return(active_symbols, target_return)
                        
                        if result:
                            st.success("Optimization complete!")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Expected Return", f"{result['expected_return']*100:.2f}%")
                            with col2:
                                st.metric("Volatility", f"{result['volatility']*100:.2f}%")
                            with col3:
                                st.metric("Sharpe Ratio", f"{result['sharpe_ratio']:.2f}")
                        else:
                            st.error(f"Optimization failed: {error}")
            else:
                st.info("Add at least 2 different holdings to use portfolio optimization.")
        
        # Tab 4: Tax Calculator
        with tab4:
            st.subheader("🧾 German Tax Calculator")
            
            tax_service = TaxService(user)
            tax_summary = tax_service.get_tax_summary()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tax-Free Allowance", f"€{tax_summary['sparerpauschbetrag']:,.0f}")
            with col2:
                st.metric("Remaining Allowance", f"€{tax_summary['remaining_allowance']:,.0f}")
            with col3:
                st.metric("Total Tax Rate", f"{tax_summary['total_tax_rate']:.2f}%")
        
        # Tab 5: Import Transactions
        with tab5:
            st.subheader("📥 Import Transactions")
            
            broker_choice = st.selectbox("Select Broker", ["Trading212", "Binance"], key="broker_choice")
            
            if broker_choice == "Trading212":
                st.write("### 🔄 Trading212 API Sync")
                from app.services.trading212_service import Trading212Service
                trading212 = Trading212Service(db)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔗 Test T212 Connection", key="test_t212"):
                        result = trading212.test_connection()
                        if result["success"]:
                            st.success("✅ Connected to Trading212!")
                        else:
                            st.error(f"❌ Connection failed: {result['error']}")
                
                with col2:
                    if st.button("🚀 Sync Transactions", type="primary", key="sync_t212"):
                        with st.spinner("Syncing..."):
                            result = trading212.sync_all_transactions(portfolio.id)
                            if result["success"]:
                                st.success(f"✅ Imported {result['imported']}, Skipped {result['skipped']}")
                            else:
                                st.error(f"❌ Failed: {result.get('error')}")
        
        # Tab 6: Settings
        with tab6:
            st.subheader("⚙️ Tax Profile Settings")
            st.write("Configure your tax settings here.")
        
        # Tab 7: Risk Analysis
        with tab7:
            st.subheader("📈 Risk Metrics")
            
            if active_symbols:
                if st.button("Calculate Risk Metrics", key="calc_risk"):
                    with st.spinner("Calculating..."):
                        risk_service = RiskService()
                        
                        total_value = summary['total_value']
                        weights = []
                        for sym in active_symbols:
                            sym_value = holdings[sym]["quantity"] * current_prices.get(sym, 0)
                            weights.append(sym_value / total_value if total_value > 0 else 0)
                        
                        metrics = risk_service.get_portfolio_risk_metrics(active_symbols, weights)
                        
                        if "portfolio" in metrics:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Volatility (Annual)", f"{metrics['portfolio']['volatility']*100:.2f}%")
                            with col2:
                                st.metric("Sharpe Ratio", f"{metrics['portfolio']['sharpe_ratio']:.2f}")
                            with col3:
                                st.metric("Max Drawdown", f"{metrics['portfolio']['max_drawdown']*100:.2f}%")
            else:
                st.info("Add holdings to see risk analysis.")
        
        # Tab 8: Risk Management
        # Tab 8: Risk Management
        with tab8:
            st.subheader("🎯 Risk Management")
            
            if live_positions and len(live_positions) > 0:
                import requests
                import time
                
                st.write("### Portfolio Beta Analysis")
                st.write("Beta measures your portfolio's volatility relative to S&P 500")
                
                TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY", "3d959483e5cf4418b1a125bc85909f31")
                
                portfolio_tickers = []
                portfolio_weights = []
                portfolio_values = []
                total_value = sum(pos.get('quantity', 0) * pos.get('currentPrice', 0) for pos in live_positions if pos.get('quantity', 0) > 0.001)
                
                for pos in live_positions:
                    ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                    qty = pos.get('quantity', 0)
                    price = pos.get('currentPrice', 0)
                    value = qty * price
                    
                    if qty > 0.001 and value > 10:
                        portfolio_tickers.append(ticker)
                        portfolio_weights.append(value / total_value)
                        portfolio_values.append(value)
                
                st.write(f"**Portfolio:** {len(portfolio_tickers)} stocks, ${total_value:,.2f} total value")
                
                if 'beta_cache' not in st.session_state:
                    st.session_state.beta_cache = {}
                if 'spy_returns_twelve' not in st.session_state:
                    st.session_state.spy_returns_twelve = None
                
                def get_daily_returns_twelve(symbol):
                    try:
                        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=100&apikey={TWELVE_DATA_KEY}"
                        r = requests.get(url, timeout=15)
                        data = r.json()
                        
                        if "values" in data:
                            prices = [float(v["close"]) for v in reversed(data["values"])]
                            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
                            return returns
                        else:
                            if "message" in data:
                                st.warning(f"{symbol}: {data['message']}")
                            return None
                    except Exception as e:
                        st.error(f"{symbol} error: {str(e)}")
                        return None
                
                def calculate_beta(stock_returns, market_returns):
                    if not stock_returns or not market_returns or len(stock_returns) < 20:
                        return None
                    min_len = min(len(stock_returns), len(market_returns))
                    cov = np.cov(stock_returns[-min_len:], market_returns[-min_len:])[0][1]
                    var = np.var(market_returns[-min_len:])
                    return cov / var if var > 0 else None
                
                calc_option = st.radio(
                    "Select calculation mode:",
                    ["Top 10 Holdings (~1 min)", "Top 25 Holdings (~2 min)", "All Holdings (~5 min)"],
                    index=0,
                    key="beta_calc_option"
                )
                
                num_stocks = 10 if "Top 10" in calc_option else 25 if "Top 25" in calc_option else len(portfolio_tickers)
                
                top_indices = sorted(range(len(portfolio_values)), key=lambda i: portfolio_values[i], reverse=True)[:num_stocks]
                top_tickers = [portfolio_tickers[i] for i in top_indices]
                top_weights = [portfolio_weights[i] for i in top_indices]
                top_values = [portfolio_values[i] for i in top_indices]
                
                total_top_weight = sum(top_weights)
                normalized_weights = [w / total_top_weight for w in top_weights]
                
                coverage = sum(top_values) / total_value * 100
                st.info(f"📊 Will analyze {len(top_tickers)} stocks covering {coverage:.1f}% of portfolio")
                
                cached_count = sum(1 for t in top_tickers if t in st.session_state.beta_cache)
                if cached_count > 0:
                    st.success(f"✅ {cached_count} stocks already cached (instant)")
                
                if st.button("📊 Calculate Portfolio Beta", type="primary", key="calc_beta"):
                    if st.session_state.spy_returns_twelve is None:
                        with st.spinner("Fetching S&P 500 data..."):
                            st.session_state.spy_returns_twelve = get_daily_returns_twelve("SPY")
                            time.sleep(1)
                    
                    spy_returns = st.session_state.spy_returns_twelve
                    
                    if spy_returns is None:
                        st.error("Could not fetch S&P 500 data.")
                    else:
                        st.success(f"✅ S&P 500: {len(spy_returns)} days of data")
                        
                        betas = {}
                        failed_tickers = []
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, ticker in enumerate(top_tickers):
                            status_text.text(f"Processing {ticker}... ({i+1}/{len(top_tickers)})")
                            
                            if ticker in st.session_state.beta_cache:
                                betas[ticker] = st.session_state.beta_cache[ticker]
                            else:
                                stock_returns = get_daily_returns_twelve(ticker)
                                
                                if stock_returns:
                                    beta = calculate_beta(stock_returns, spy_returns)
                                    if beta is not None:
                                        betas[ticker] = beta
                                        st.session_state.beta_cache[ticker] = beta
                                    else:
                                        failed_tickers.append(ticker)
                                else:
                                    failed_tickers.append(ticker)
                                
                                time.sleep(0.5)
                            
                            progress_bar.progress((i + 1) / len(top_tickers))
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if betas:
                            portfolio_beta = 0
                            total_weight_with_beta = 0
                            
                            for j, ticker in enumerate(top_tickers):
                                if ticker in betas:
                                    portfolio_beta += betas[ticker] * normalized_weights[j]
                                    total_weight_with_beta += normalized_weights[j]
                            
                            if total_weight_with_beta > 0:
                                portfolio_beta = portfolio_beta / total_weight_with_beta
                            
                            st.divider()
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if portfolio_beta < 0.8:
                                    st.metric("Portfolio Beta", f"{portfolio_beta:.2f}", delta="Low Risk", delta_color="normal")
                                elif portfolio_beta < 1.2:
                                    st.metric("Portfolio Beta", f"{portfolio_beta:.2f}", delta="Medium Risk", delta_color="off")
                                else:
                                    st.metric("Portfolio Beta", f"{portfolio_beta:.2f}", delta="High Risk", delta_color="inverse")
                            
                            with col2:
                                st.metric("Stocks Analyzed", f"{len(betas)}/{len(top_tickers)}")
                            
                            with col3:
                                if portfolio_beta > 1:
                                    diff = (portfolio_beta - 1) * 100
                                    st.metric("vs S&P 500", f"+{diff:.0f}% volatile")
                                else:
                                    diff = (1 - portfolio_beta) * 100
                                    st.metric("vs S&P 500", f"-{diff:.0f}% volatile")
                            
                            st.divider()
                            
                            st.write("### 📖 What does this mean?")
                            
                            if portfolio_beta < 0.8:
                                st.info(f"🛡️ **Defensive Portfolio** - If S&P 500 moves ±10%, your portfolio moves ~±{portfolio_beta * 10:.1f}%")
                            elif portfolio_beta < 1.2:
                                st.success(f"⚖️ **Balanced Portfolio** - If S&P 500 moves ±10%, your portfolio moves ~±{portfolio_beta * 10:.1f}%")
                            elif portfolio_beta < 1.5:
                                st.warning(f"📈 **Growth Portfolio** - If S&P 500 moves ±10%, your portfolio moves ~±{portfolio_beta * 10:.1f}%")
                            else:
                                st.error(f"🚀 **Aggressive Portfolio** - If S&P 500 moves ±10%, your portfolio moves ~±{portfolio_beta * 10:.1f}%")
                            
                            st.divider()
                            
                            st.write("### 📊 Individual Stock Betas")
                            
                            beta_data = []
                            for ticker, beta in sorted(betas.items(), key=lambda x: x[1], reverse=True):
                                company = COMPANY_NAMES.get(ticker, ticker)
                                idx = top_tickers.index(ticker)
                                value = top_values[idx]
                                weight = top_weights[idx] * 100
                                risk = "🔴 High" if beta > 1.5 else "🟡 Medium" if beta > 1 else "🟢 Low"
                                
                                beta_data.append({
                                    "Company": company,
                                    "Ticker": ticker,
                                    "Beta": f"{beta:.2f}",
                                    "Value": f"${value:,.0f}",
                                    "Weight": f"{weight:.1f}%",
                                    "Risk": risk
                                })
                            
                            st.dataframe(pd.DataFrame(beta_data), use_container_width=True, hide_index=True)
                            
                            if failed_tickers:
                                with st.expander(f"⚠️ Could not calculate beta for {len(failed_tickers)} stocks"):
                                    st.write(", ".join(failed_tickers))
                            
                            if portfolio_beta > 1.3:
                                st.divider()
                                st.write("### 💡 Risk Reduction Tips")
                                
                                high_beta = [(t, betas[t], top_values[top_tickers.index(t)]) 
                                            for t in top_tickers if t in betas and betas[t] > 1.5]
                                high_beta.sort(key=lambda x: x[1] * x[2], reverse=True)
                                
                                if high_beta:
                                    st.write("Consider reducing these high-beta positions:")
                                    for ticker, beta, value in high_beta[:5]:
                                        company = COMPANY_NAMES.get(ticker, ticker)
                                        st.write(f"- **{company}** ({ticker}): β={beta:.2f}, ${value:,.0f}")
                        else:
                            st.error("Could not calculate beta for any stocks.")
                
                if st.session_state.beta_cache:
                    if st.button("🗑️ Clear Beta Cache", key="clear_beta_cache"):
                        st.session_state.beta_cache = {}
                        st.session_state.spy_returns_twelve = None
                        st.success("Cache cleared!")
                        st.rerun()
            else:
                st.warning("No positions found. Connect to Trading212 first.")
    
    else:
        st.info("No portfolio found.")
    
    db.close()

if st.session_state.logged_in:
    show_dashboard()
else:
    show_login_page()