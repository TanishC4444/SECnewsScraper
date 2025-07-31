import requests
import xml.etree.ElementTree as ET
import re
from bs4 import BeautifulSoup
from datetime import datetime
from html import unescape
from decimal import Decimal
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import yfinance as yf
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import datetime
import pytz
import pandas as pd
import os

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "tanishchauhan4444@gmail.com"
# Replace the hardcoded password with environment variable
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'smgj lhbr xioz lqwu')
RECIPIENT_EMAIL = "tanishchauhan4444@gmail.com"

NOTIFIED_LOG = "notified_log.txt"
SD_LOG_FILE = "sd_log.txt"

def log_sd_filing(entry):
    with open(SD_LOG_FILE, "a") as f:
        f.write(f"{entry}\n")

# 4. Add SD parsing function (add this with your other parsing functions)
def parse_sd_filing(txt_url, index_url):
    """Parse SD filing to extract conflict minerals information"""
    try:
        resp = requests.get(txt_url, headers=headers)
        resp.raise_for_status()
        content = resp.text.lower()
        
        # Look for key conflict minerals indicators
        minerals_mentioned = []
        if any(term in content for term in ['tin', 'cassiterite']):
            minerals_mentioned.append('Tin')
        if any(term in content for term in ['tantalum', 'columbite']):
            minerals_mentioned.append('Tantalum')
        if any(term in content for term in ['tungsten', 'wolframite']):
            minerals_mentioned.append('Tungsten')
        if any(term in content for term in ['gold']):
            minerals_mentioned.append('Gold')
            
        # Determine DRC status
        drc_status = "Unknown"
        if "drc conflict free" in content:
            drc_status = "DRC Conflict Free"
        elif "not found to be drc conflict free" in content:
            drc_status = "Not DRC Conflict Free"
        elif "undeterminable" in content:
            drc_status = "Undeterminable"
        elif "no conflict minerals" in content:
            drc_status = "No Conflict Minerals"
            
        # Look for supply chain complexity indicators
        suppliers_mentioned = len(re.findall(r'supplier[s]?', content))
        smelter_mentioned = 'smelter' in content or 'refiner' in content
        
        return {
            "minerals": minerals_mentioned,
            "drc_status": drc_status,
            "suppliers_count": suppliers_mentioned,
            "smelter_audit": smelter_mentioned,
            "content_length": len(content)
        }
        
    except Exception as e:
        print(f"Error parsing SD filing: {e}")
        return None
    
def get_sd_signal(sd_data):
    """Determine ESG/compliance signal from SD filing"""
    if not sd_data:
        return "📋 SD Filing", "#8B4513"
        
    if sd_data['drc_status'] == "DRC Conflict Free":
        return "✅ ESG COMPLIANT", "#28A745"
    elif sd_data['drc_status'] == "Not DRC Conflict Free":
        return "⚠️ ESG RISK", "#FF6B6B"
    elif sd_data['drc_status'] == "No Conflict Minerals":
        return "✅ NO CONFLICT MINERALS", "#28A745"
    elif sd_data['drc_status'] == "Undeterminable":
        return "🔍 ESG UNCLEAR", "#FFA500"
    else:
        return "📋 ESG DISCLOSURE", "#8B4513"

def load_notified():
    try:
        with open(NOTIFIED_LOG, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_notified(entry_id):
    with open(NOTIFIED_LOG, "a") as f:
        f.write(entry_id + "\n")

headers = {"User-Agent": "SECscraper/1.0 (tanishc4444@gmail.com)"}

LOG_FILE = "s1mef_log.txt"
FORM144_LOG_FILE = "form144_log.txt"
EIGHTK_LOG_FILE = "eightk_log.txt"

def get_ticker_from_name(company_name):
    """Get ticker symbol from company name using Yahoo Finance search"""
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": company_name, "quotesCount": 1, "newsCount": 0}
        headers_yf = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers_yf, timeout=10)
        data = r.json()
        if "quotes" in data and data["quotes"]:
            return data["quotes"][0]["symbol"]
        return None
    except Exception as e:
        print(f"Error getting ticker for {company_name}: {e}")
        return None

def get_quarterly_data_table(ticker):
    """Get quarterly earnings data and next earnings date with proper formatting"""
    try:
        ticker = ticker.strip().lstrip('$')
        stock = yf.Ticker(ticker)
        
        # Get quarterly data using the correct method
        quarterly_financials = stock.quarterly_financials
        quarterly_income = stock.quarterly_income_stmt  # Use this instead of deprecated earnings
        
        # Get next earnings date
        info = stock.info
        next_earnings_date = info.get('earningsDate')
        earnings_date_str = "TBD"
        
        if next_earnings_date:
            try:
                if isinstance(next_earnings_date, list) and len(next_earnings_date) > 0:
                    earnings_date_str = next_earnings_date[0].strftime('%b %d, %Y')
                elif hasattr(next_earnings_date, 'strftime'):
                    earnings_date_str = next_earnings_date.strftime('%b %d, %Y')
            except:
                earnings_date_str = "TBD"
        
        # Build quarterly table HTML
        quarterly_html = ""
        
        if not quarterly_income.empty and len(quarterly_income.columns) >= 2:
            try:
                # Get last 4 quarters of data
                recent_quarters = quarterly_income.iloc[:, :4]  # Get first 4 columns (most recent quarters)
                
                quarterly_html = f"""
                <div style="margin-top: 25px; background: rgba(255,255,255,0.05); padding: 25px; 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.1);">
                    <h4 style="margin: 0 0 20px 0; color: #ecf0f1; font-size: 20px; text-align: center;">
                        📊 Quarterly Financial Data - Last 4 Quarters
                    </h4>
                    
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                            <thead>
                                <tr style="background: rgba(255,255,255,0.1);">
                                    <th style="padding: 12px; text-align: left; color: #bdc3c7; font-size: 14px; 
                                              border-bottom: 2px solid rgba(255,255,255,0.2);">Metric</th>
                """
                
                # Add quarter headers
                for quarter_date in recent_quarters.columns:
                    quarter_str = quarter_date.strftime('%Q%y') if hasattr(quarter_date, 'strftime') else str(quarter_date)[:7]
                    quarterly_html += f"""
                    <th style="padding: 12px; text-align: center; color: #bdc3c7; font-size: 14px;
                              border-bottom: 2px solid rgba(255,255,255,0.2);">{quarter_str}</th>
                    """
                
                quarterly_html += """
                                </tr>
                            </thead>
                            <tbody>
                """
                
                # Key metrics to display
                key_metrics = {
                    'Total Revenue': 'Total Revenue',
                    'Net Income': 'Net Income',
                    'Gross Profit': 'Gross Profit',
                    'Operating Income': 'Operating Income'
                }
                
                for display_name, metric_key in key_metrics.items():
                    if metric_key in recent_quarters.index:
                        quarterly_html += f"""
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                            <td style="padding: 10px; color: white; font-weight: bold;">{display_name}</td>
                        """
                        
                        for quarter_date in recent_quarters.columns:
                            value = recent_quarters.loc[metric_key, quarter_date]
                            if pd.notna(value) and value != 0:
                                # Format in millions/billions
                                if abs(value) >= 1e9:
                                    formatted_value = f"${value/1e9:.2f}B"
                                elif abs(value) >= 1e6:
                                    formatted_value = f"${value/1e6:.1f}M"
                                else:
                                    formatted_value = f"${value:,.0f}"
                                
                                # Color code positive/negative
                                color = "#00ff88" if value > 0 else "#ff4757" if value < 0 else "white"
                            else:
                                formatted_value = "N/A"
                                color = "#8e9297"
                            
                            quarterly_html += f"""
                            <td style="padding: 10px; text-align: center; color: {color}; font-weight: bold;">
                                {formatted_value}
                            </td>
                            """
                        
                        quarterly_html += "</tr>"
                
                quarterly_html += """
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Next Earnings Date -->
                    <div style="text-align: center; padding: 15px; background: rgba(52, 152, 219, 0.2); 
                               border-radius: 10px; border: 2px solid rgba(52, 152, 219, 0.3);">
                        <p style="margin: 0; color: #bdc3c7; font-size: 14px; text-transform: uppercase;">
                            Next Earnings Report
                        </p>
                        <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: #3498db;">
                            {earnings_date_str}
                        </p>
                    </div>
                </div>
                """
                
            except Exception as e:
                print(f"Error processing quarterly data: {e}")
                quarterly_html = f"""
                <div style="margin-top: 25px; background: rgba(255,100,100,0.1); padding: 20px; 
                           border-radius: 12px; border: 2px solid rgba(255,100,100,0.3);">
                    <p style="color: #ff6b6b; text-align: center;">
                        📊 Quarterly data not available for {ticker}
                    </p>
                    <div style="text-align: center; padding: 15px; background: rgba(52, 152, 219, 0.2); 
                               border-radius: 10px; border: 2px solid rgba(52, 152, 219, 0.3); margin-top: 15px;">
                        <p style="margin: 0; color: #bdc3c7; font-size: 14px; text-transform: uppercase;">
                            Next Earnings Report
                        </p>
                        <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: #3498db;">
                            {earnings_date_str}
                        </p>
                    </div>
                </div>
                """
        else:
            quarterly_html = f"""
            <div style="margin-top: 25px; background: rgba(255,255,255,0.05); padding: 20px; 
                       border-radius: 12px; border: 2px solid rgba(255,255,255,0.1);">
                <p style="color: #bdc3c7; text-align: center;">
                    📊 Quarterly data not available for {ticker}
                </p>
                <div style="text-align: center; padding: 15px; background: rgba(52, 152, 219, 0.2); 
                           border-radius: 10px; border: 2px solid rgba(52, 152, 219, 0.3); margin-top: 15px;">
                    <p style="margin: 0; color: #bdc3c7; font-size: 14px; text-transform: uppercase;">
                        Next Earnings Report
                    </p>
                    <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: #3498db;">
                        {earnings_date_str}
                    </p>
                </div>
            </div>
            """
        
        return quarterly_html
        
    except Exception as e:
        print(f"Error getting quarterly data for {ticker}: {e}")
        return f"""
        <div style="margin-top: 25px; background: rgba(255,100,100,0.1); padding: 20px; 
                   border-radius: 12px; border: 2px solid rgba(255,100,100,0.3);">
            <p style="color: #ff6b6b; text-align: center;">
                📊 Unable to fetch quarterly data for {ticker}
            </p>
        </div>
        """

def get_stock_data_and_chart(ticker):
    """Get comprehensive stock stats and create professional chart with white text"""
    try:
        ticker = ticker.strip().lstrip('$')
        stock = yf.Ticker(ticker)
        
        # Get comprehensive data
        info = stock.info
        hist_5d = stock.history(period="5d", interval="1d")
        hist_1m = stock.history(period="1mo")
        hist_3m = stock.history(period="3mo")
        hist_1y = stock.history(period="1y")
        
        # Check for empty data
        if hist_5d.empty or hist_1m.empty:
            return None, None
            
        # Calculate price changes
        last_price = hist_5d['Close'].iloc[-1]
        prev_close = info.get('previousClose')
        pct_change = ((last_price - prev_close) / prev_close * 100) if prev_close else None
        
        # Calculate quarterly performance
        qtd_change = None
        ytd_change = None
        if not hist_3m.empty:
            qtd_start = hist_3m['Close'].iloc[0]
            qtd_change = ((last_price - qtd_start) / qtd_start * 100)
        
        if not hist_1y.empty:
            ytd_start = hist_1y['Close'].iloc[0]
            ytd_change = ((last_price - ytd_start) / ytd_start * 100)
        
        # Create the chart with WHITE TEXT
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        fig.patch.set_facecolor('#1a1a1a')
        
        # Main price chart
        line_color = '#00ff88' if pct_change and pct_change > 0 else '#ff4757'
        ax1.plot(hist_1m.index, hist_1m['Close'], 
                color=line_color, linewidth=3, alpha=0.9)
        ax1.fill_between(hist_1m.index, hist_1m['Close'], 
                       alpha=0.3, color=line_color)
        
        # Volume chart
        volume_color = '#3c4043'
        ax2.bar(hist_1m.index, hist_1m['Volume'], 
               alpha=0.6, color=volume_color, width=0.8)
        
        # Styling for price chart - WHITE TEXT
        ax1.set_title(f'{ticker} - 30 Day Performance & Volume', 
                     fontsize=20, fontweight='bold', color='white', pad=20)
        ax1.set_ylabel('Price ($)', fontsize=14, color='white')  # Changed to white
        ax1.grid(True, alpha=0.2, color='#5f6368')
        ax1.tick_params(colors='white', labelsize=12)  # Changed to white
        
        # Styling for volume chart - WHITE TEXT
        ax2.set_ylabel('Volume', fontsize=12, color='white')  # Changed to white
        ax2.set_xlabel('Date', fontsize=14, color='white')    # Changed to white
        ax2.grid(True, alpha=0.2, color='#5f6368')
        ax2.tick_params(colors='white', labelsize=10)  # Changed to white
        
        # Add price annotation
        change_symbol = "▲" if pct_change and pct_change > 0 else "▼"
        price_text = f'${last_price:.2f} {change_symbol} {pct_change:.2f}%'
        ax1.text(0.02, 0.98, price_text, transform=ax1.transAxes, 
                fontsize=16, fontweight='bold', color=line_color,
                verticalalignment='top', 
                bbox=dict(boxstyle='round,pad=0.8', facecolor='#2d3436', alpha=0.9))
        
        # Format dates
        import matplotlib.dates as mdates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, color='white')  # Added white color
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', 
                   facecolor='#1a1a1a', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        plt.style.use('default')
        
        # Get quarterly HTML with WHITE TEXT
        quarterly_html = get_quarterly_data_table(ticker)
        
        # Enhanced metrics
        market_cap = info.get('marketCap')
        volume = info.get('volume')
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        dividend_yield = info.get('dividendYield')
        beta = info.get('beta')
        
        # Color coding for performance
        qtd_color = "#00ff88" if qtd_change and qtd_change > 0 else "#ff4757" if qtd_change else "#8e9297"
        ytd_color = "#00ff88" if ytd_change and ytd_change > 0 else "#ff4757" if ytd_change else "#8e9297"
        change_color = "#00ff88" if pct_change and pct_change > 0 else "#ff4757"
        change_arrow = "▲" if pct_change and pct_change > 0 else "▼"
        
        # Create comprehensive stock HTML with WHITE TEXT
        stock_html = f"""
        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
                    padding: 30px; border-radius: 15px; margin: 25px 0; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.4); color: white;">
            
            <h3 style="margin: 0 0 25px 0; color: white; font-size: 26px; text-align: center; 
                      text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
                📈 Financial Overview: {ticker}
            </h3>
            
            <!-- Key Performance Metrics -->
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px;">
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: white; font-size: 13px; text-transform: uppercase;">Current Price</h4>
                    <p style="font-size: 24px; margin: 8px 0 0 0; font-weight: bold; color: white;">${last_price:.2f}</p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: white; font-size: 13px; text-transform: uppercase;">Daily Change</h4>
                    <p style="font-size: 20px; margin: 8px 0 0 0; font-weight: bold; color: {change_color};">
                        {change_arrow} {pct_change:.2f}%
                    </p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: white; font-size: 13px; text-transform: uppercase;">QTD Change</h4>
                    <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: {qtd_color};">
                        {f"{qtd_change:+.1f}%" if qtd_change else "N/A"}
                    </p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: white; font-size: 13px; text-transform: uppercase;">YTD Change</h4>
                    <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: {ytd_color};">
                        {f"{ytd_change:+.1f}%" if ytd_change else "N/A"}
                    </p>
                </div>
            </div>
            
            <!-- Company Fundamentals -->
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0;">
                <h4 style="margin: 0 0 15px 0; color: white; font-size: 18px; text-align: center;">
                    🏢 Company Fundamentals
                </h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                    <div>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>Market Cap:</strong> 
                           {f"${market_cap/1e9:.1f}B" if market_cap else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>P/E Ratio:</strong> 
                           {f"{pe_ratio:.2f}" if pe_ratio else "N/A"}</p>
                    </div>
                    <div>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>P/B Ratio:</strong> 
                           {f"{pb_ratio:.2f}" if pb_ratio else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>Beta:</strong> 
                           {f"{beta:.2f}" if beta else "N/A"}</p>
                    </div>
                    <div>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>Dividend Yield:</strong> 
                           {f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px; color: white;"><strong>Volume:</strong> 
                           {f"{volume:,}" if volume else "N/A"}</p>
                    </div>
                </div>
            </div>
            
            <!-- Trading Ranges -->
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0;">
                <h4 style="margin: 0 0 15px 0; color: white; font-size: 18px; text-align: center;">
                    📊 Trading Ranges
                </h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px;">
                    <div style="text-align: center;">
                        <p style="margin: 0; color: white; font-size: 14px;">TODAY'S RANGE</p>
                        <p style="font-size: 18px; margin: 8px 0; font-weight: bold; color: white;">
                            ${info.get('dayLow', 'N/A')} - ${info.get('dayHigh', 'N/A')}
                        </p>
                    </div>
                    <div style="text-align: center;">
                        <p style="margin: 0; color: white; font-size: 14px;">52-WEEK RANGE</p>
                        <p style="font-size: 18px; margin: 8px 0; font-weight: bold; color: white;">
                            ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}
                        </p>
                    </div>
                </div>
            </div>
            
            {quarterly_html}
            
            <!-- Stock Chart -->
            <div style="margin-top: 25px; text-align: center;">
                <img src="cid:stock_chart" style="width: 100%; max-width: 800px; border-radius: 12px; 
                     box-shadow: 0 8px 25px rgba(0,0,0,0.4);">
            </div>
        </div>
        """
        
        return chart_base64, stock_html
        
    except Exception as e:
        print(f"Error getting comprehensive stock data for {ticker}: {e}")
        return None, None
    
def create_filing_info_section(updated_string, signal_type, signal_description, signal_color):
    """Create professional filing information section with larger emoji"""
    filing_date, filing_dt = format_sec_filing_date(updated_string)
    
    # Calculate time ago
    time_ago = ""
    if filing_dt:
        now = datetime.now(pytz.timezone('US/Eastern'))
        diff = now - filing_dt
        if diff.days > 0:
            time_ago = f"({diff.days} day{'s' if diff.days != 1 else ''} ago)"
        else:
            hours = diff.seconds // 3600
            if hours > 0:
                time_ago = f"({hours} hour{'s' if hours != 1 else ''} ago)"
            else:
                minutes = diff.seconds // 60
                time_ago = f"({minutes} minute{'s' if minutes != 1 else ''} ago)"
    
    return f"""
    <div style="background: linear-gradient(135deg, {signal_color}20, {signal_color}10); 
                padding: 12px; border-radius: 6px; margin: 10px 0; 
                border-left: 3px solid {signal_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="flex: 1; min-width: 250px;">
                <h3 style="margin: 0; color: {signal_color}; font-size: 14px; font-weight: bold;">
                    📊 SIGNAL: {signal_type}
                </h3>
                <p style="font-size: 12px; margin: 2px 0 0 0; color: #555;">
                    {signal_description}
                </p>
            </div>
            <div style="text-align: right; font-size: 11px; color: #666; white-space: nowrap; flex-shrink: 0;">
                <div style="font-weight: bold;">{filing_date}</div>
                <div style="color: #888;">{time_ago}</div>
            </div>
        </div>
    </div>
    """
    
def create_links_section(htm_link, txt_link=None):
    """Create a professional links section with both HTM and TXT links"""
    links_html = f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; margin: 25px 0;">
        <h3 style="margin: 0 0 15px 0; color: white; font-size: 20px; text-align: center;">
            🔗 Filing Links
        </h3>
        <div style="display: grid; grid-template-columns: 1fr{' 1fr' if txt_link else ''}; gap: 15px;">
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); 
                        border-radius: 8px; border: 2px solid rgba(255,255,255,0.3);">
                <h4 style="margin: 0 0 10px 0; color: white; font-size: 16px;">📄 HTML View</h4>
                <a href="{htm_link}" style="color: #fff; text-decoration: none; font-weight: bold; 
                   font-size: 14px; padding: 8px 16px; background: rgba(255,255,255,0.2); 
                   border-radius: 5px; display: inline-block; transition: all 0.3s;">
                    View Original Filing
                </a>
            </div>
    """
    
    if txt_link:
        links_html += f"""
            <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.2); 
                        border-radius: 8px; border: 2px solid rgba(255,255,255,0.3);">
                <h4 style="margin: 0 0 10px 0; color: white; font-size: 16px;">📝 Text View</h4>
                <a href="{txt_link}" style="color: #fff; text-decoration: none; font-weight: bold; 
                   font-size: 14px; padding: 8px 16px; background: rgba(255,255,255,0.2); 
                   border-radius: 5px; display: inline-block; transition: all 0.3s;">
                    View Raw Text
                </a>
            </div>
        """
    
    links_html += """
        </div>
    </div>
    """
    return links_html

def send_html_email_with_chart(subject, html_body, chart_base64=None):
    """Send HTML email with optional embedded chart"""
    msg = MIMEMultipart('related')
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    
    # Add HTML content
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText("HTML email not supported", 'plain'))
    msg_alternative.attach(MIMEText(html_body, 'html'))
    msg.attach(msg_alternative)
    
    # Add chart if provided
    if chart_base64:
        chart_data = base64.b64decode(chart_base64)
        chart_image = MIMEImage(chart_data)
        chart_image.add_header('Content-ID', '<stock_chart>')
        msg.attach(chart_image)
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

def log_form144(entry):
    with open(FORM144_LOG_FILE, "a") as f:
        f.write(f"{entry}\n")

def log_to_file(entry):
    with open(LOG_FILE, "a") as f:
        f.write(f"{entry}\n")

def log_to_file8k(entry):
    with open(EIGHTK_LOG_FILE, "a") as f:
        f.write(f"{entry}\n")

# Enhanced 8-K items with clear signals
eight_k_items_info = {
    "1.01": ("📝 Material Agreement", "🟢", "NEUTRAL"),
    "1.02": ("❌ Agreement Terminated", "🔴", "BEARISH"),
    "1.03": ("💀 Bankruptcy/Receivership", "🔴", "VERY BEARISH"),
    "2.01": ("🏢 Asset Transaction", "🟡", "WATCH"),
    "2.02": ("📊 Financial Results", "🟡", "WATCH"),
    "2.03": ("💸 New Debt/Obligation", "🔴", "BEARISH"),
    "2.04": ("⚠️ Increased Obligations", "🔴", "BEARISH"),
    "2.05": ("🏭 Exit/Disposal Costs", "🔴", "BEARISH"),
    "2.06": ("📉 Asset Impairments", "🔴", "BEARISH"),
    "3.01": ("🚫 Delisting Risk", "🔴", "VERY BEARISH"),
    "3.02": ("🔓 Unregistered Stock Sale", "🔴", "BEARISH"),
    "3.03": ("⚖️ Rights Modified", "🟡", "WATCH"),
    "4.01": ("🔄 Auditor Change", "🔴", "BEARISH"),
    "4.02": ("❌ Financial Restatement", "🔴", "VERY BEARISH"),
    "5.01": ("👑 Control Change", "🟡", "MAJOR WATCH"),
    "5.02": ("👔 Leadership Change", "🟡", "WATCH"),
    "5.03": ("📋 Bylaws Amendment", "🟢", "NEUTRAL"),
    "5.04": ("⏸️ Trading Suspended", "🔴", "BEARISH"),
    "7.01": ("📢 Material Disclosure", "🟡", "WATCH"),
    "8.01": ("❓ Other Events", "🟡", "WATCH"),
    "9.01": ("📄 Financial Statements", "🟢", "NEUTRAL"),
}
filing_explanations = {
    "S-1": {
        "name": "Initial Public Offering Registration",
        "description": "Companies use this to register securities for their first public sale (IPO). It contains detailed business information, financials, and risk factors.",
        "signal": "🚀 IPO COMING",
        "color": "#4CAF50",
        "significance": "MAJOR - Company going public"
    },
    "S-1MEF": {
        "name": "S-1 Amendment (MEF = Most Recent Amendment)",
        "description": "Updates to the original S-1 filing, often includes pricing information, final share counts, or updated financials before IPO launch.",
        "signal": "📋 IPO UPDATE",
        "color": "#2196F3", 
        "significance": "HIGH - IPO details finalized"
    },
    "S-3": {
        "name": "Shelf Registration",
        "description": "Allows established companies to register securities they may sell over the next 3 years without filing new registration statements each time.",
        "signal": "📦 SHELF REGISTRATION",
        "color": "#FF9800",
        "significance": "MEDIUM - Future fundraising prepared"
    },
    "S-4": {
        "name": "Merger/Acquisition Registration",
        "description": "Used when companies issue securities in connection with mergers, acquisitions, or business combinations.",
        "signal": "🤝 M&A ACTIVITY",
        "color": "#9C27B0",
        "significance": "MAJOR - Corporate restructuring"
    },
    "S-8": {
        "name": "Employee Stock Plan Registration", 
        "description": "Registers securities offered to employees through stock option plans, employee stock purchase plans, or similar arrangements.",
        "signal": "👥 EMPLOYEE STOCK PLAN",
        "color": "#607D8B",
        "significance": "LOW - Routine employee benefits"
    },
    "S-11": {
        "name": "Real Estate Investment Trust (REIT) Registration",
        "description": "Specifically for real estate companies and REITs going public or issuing new securities.",
        "signal": "🏢 REIT OFFERING",
        "color": "#795548",
        "significance": "MEDIUM - Real estate investment"
    },
    "F-1": {
        "name": "Foreign Company IPO Registration",
        "description": "Similar to S-1 but for foreign companies seeking to list on US exchanges for the first time.",
        "signal": "🌍 FOREIGN IPO",
        "color": "#3F51B5",
        "significance": "MAJOR - International expansion"
    },
    "F-3": {
        "name": "Foreign Company Shelf Registration",
        "description": "Shelf registration for foreign companies that are already public in their home country.",
        "signal": "🌍 FOREIGN SHELF",
        "color": "#FF5722",
        "significance": "MEDIUM - International fundraising"
    },
    "EFFECT": {
        "name": "Registration Effectiveness Notice",
        "description": "SEC declares the registration statement effective, meaning the company can now legally sell securities to the public.",
        "signal": "✅ APPROVED TO SELL",
        "color": "#4CAF50",
        "significance": "CRITICAL - Trading can begin"
    },
    "SD": {
        "name": "Specialized Disclosure Report",
        "description": "Annual conflict minerals reporting required for companies that manufacture products containing tin, tantalum, tungsten, or gold. Companies must disclose whether these minerals originated from the Democratic Republic of Congo or adjoining countries.",
        "signal": "⛏️ CONFLICT MINERALS",
        "color": "#8B4513",
        "significance": "COMPLIANCE - ESG/Supply Chain"
    }
}


def extract_company_name(title):
    """Extract clean company name from filing title"""
    # Remove form type prefixes
    title = re.sub(r'^(S-1MEF|8-K|144|EFFECT)\s*-\s*', '', title, flags=re.IGNORECASE)
    # Take first part before additional dashes or parentheses
    company = title.split(' - ')[0].split(' (')[0].strip()
    return company

def get_filings(form_type, count=5):
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={form_type}&count={count}&output=atom"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    filings = []
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns).text
        link = entry.find('atom:link', ns).attrib['href']
        updated = entry.find('atom:updated', ns).text
        filings.append({
            "title": title,
            "link": link,
            "updated": updated
        })
    return filings

def get_filing_explanation(form_type):
    """Get detailed explanation for any filing type"""
    # Clean the form type (remove MEF suffix for lookup)
    clean_form = form_type.replace("MEF", "").strip()
    
    if clean_form in filing_explanations:
        return filing_explanations[clean_form]
    elif form_type in filing_explanations:  # Check exact match (for S-1MEF)
        return filing_explanations[form_type]
    else:
        return {
            "name": f"{form_type} Filing",
            "description": "SEC registration or disclosure document",
            "signal": "📄 SEC FILING",
            "color": "#6C757D",
            "significance": "UNKNOWN - Check filing details"
        }

def create_filing_explanation_section(form_type):
    """Create an explanation section for the filing type"""
    explanation = get_filing_explanation(form_type)
    
    return f"""
    <div style="background: linear-gradient(135deg, {explanation['color']}20, {explanation['color']}10); 
                padding: 20px; border-radius: 10px; margin: 20px 0; 
                border-left: 4px solid {explanation['color']};">
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <h3 style="margin: 0; color: {explanation['color']}; font-size: 20px; font-weight: bold;">
                {explanation['signal']} {explanation['name']}
            </h3>
            <span style="margin-left: auto; padding: 4px 12px; background: {explanation['color']}; 
                         color: white; border-radius: 20px; font-size: 12px; font-weight: bold;">
                {explanation['significance']}
            </span>
        </div>
        <p style="margin: 0; color: #333; font-size: 16px; line-height: 1.5;">
            💡 <strong>What this means:</strong> {explanation['description']}
        </p>
    </div>
    """

# Enhanced EFFECT processing to detect underlying form types
def get_effect_text_and_type_enhanced(index_link):
    """Enhanced version that detects and explains underlying form types"""
    match = re.search(r'/data/(\d+)/(\d{10,})/', index_link)
    if not match:
        return None, None, None, None
    
    cik, accession = match.groups()
    effect_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/xslEFFECTX01/primary_doc.xml"

    resp = requests.get(effect_url, headers=headers)
    if resp.status_code != 200:
        return None, None, None, None

    try:
        root = ET.fromstring(resp.content)
        text_content = " ".join([elem.text.strip() for elem in root.iter() if elem.text and elem.text.strip()])
        form_type = next((elem.text.strip() for elem in root.iter() if elem.tag.lower().endswith("formtype") and elem.text), None)
        eff_date = next((elem.text.strip() for elem in root.iter() if elem.tag.lower().endswith("effectivedate") and elem.text), None)
        
        # Get explanation for the underlying form
        explanation = get_filing_explanation(form_type) if form_type else None
        
        return text_content, form_type, eff_date, explanation
        
    except ET.ParseError:
        soup = BeautifulSoup(resp.content, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)
        form_type_match = re.search(r"Form:\s*([A-Z0-9\-]+)", text_content)
        date_match = re.search(r"Effectiveness Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", text_content)
        form_type = form_type_match.group(1) if form_type_match else None
        eff_date = date_match.group(1) if date_match else None
        
        # Get explanation for the underlying form
        explanation = get_filing_explanation(form_type) if form_type else None
        
        return text_content, form_type, eff_date, explanation


def convert_to_txt_link(index_url):
    return index_url.replace("-index.htm", ".txt")

def fetch_and_clean_txt(url):
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    raw = r.text
    text = re.sub(r"<.*?>", "", raw, flags=re.S)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text

def extract_items(text):
    pattern = r"(Item\s+\d+\.\d+.*?)(?=(Item\s+\d+\.\d+)|SIGNATURES)"
    matches = re.findall(pattern, text, flags=re.S | re.I)
    return [m[0].strip() for m in matches]

def get_signal_color(signal):
    colors = {
        "VERY BEARISH": "#FF0000",
        "BEARISH": "#FF6B6B", 
        "WATCH": "#FFA500",
        "MAJOR WATCH": "#FF8C00",
        "NEUTRAL": "#28A745"
    }
    return colors.get(signal, "#6C757D")

def summarize_items_enhanced(items):
    summaries = []
    total_signal = "NEUTRAL"
    
    for item in items:
        lines = item.split(". ")
        header = lines[0].strip()
        body = " ".join(lines[1:]).strip()
        
        # Skip if body is empty or too short (less than 10 characters)
        if not body or len(body) < 10:
            continue
            
        match = re.search(r"Item\s+(\d+\.\d+)", header)
        if match:
            item_num = match.group(1)
            if item_num in eight_k_items_info:
                description, emoji, signal = eight_k_items_info[item_num]
                color = get_signal_color(signal)
                
                # Update overall signal priority
                if signal == "VERY BEARISH":
                    total_signal = "VERY BEARISH"
                elif signal == "BEARISH" and total_signal not in ["VERY BEARISH"]:
                    total_signal = "BEARISH"
                elif signal in ["WATCH", "MAJOR WATCH"] and total_signal == "NEUTRAL":
                    total_signal = "WATCH"
                
                summary = {
                    'item': item_num,
                    'description': description,
                    'emoji': emoji,
                    'signal': signal,
                    'color': color,
                    'text': body
                }
                summaries.append(summary)
    
    return summaries, total_signal

def get_effect_text_and_type(index_link):
    match = re.search(r'/data/(\d+)/(\d{10,})/', index_link)
    if not match:
        return None, None, None
    cik, accession = match.groups()
    effect_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/xslEFFECTX01/primary_doc.xml"

    resp = requests.get(effect_url, headers=headers)
    if resp.status_code != 200:
        return None, None, None

    try:
        root = ET.fromstring(resp.content)
        text_content = " ".join([elem.text.strip() for elem in root.iter() if elem.text and elem.text.strip()])
        form_type = next((elem.text.strip() for elem in root.iter() if elem.tag.lower().endswith("formtype") and elem.text), None)
        eff_date = next((elem.text.strip() for elem in root.iter() if elem.tag.lower().endswith("effectivedate") and elem.text), None)
        return text_content, form_type, eff_date
    except ET.ParseError:
        soup = BeautifulSoup(resp.content, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)
        form_type_match = re.search(r"Form:\s*([A-Z0-9\-]+)", text_content)
        date_match = re.search(r"Effectiveness Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", text_content)
        form_type = form_type_match.group(1) if form_type_match else None
        eff_date = date_match.group(1) if date_match else None
        return text_content, form_type, eff_date

def parse_form144(txt_url):
    resp = requests.get(txt_url, headers=headers)
    resp.raise_for_status()
    content = resp.text

    def extract(tag):
        match = re.search(rf"<{tag}>(.*?)</{tag}>", content)
        return match.group(1).strip() if match else None

    issuer = extract("issuerName")
    relationship = extract("relationshipToIssuer")
    shares = extract("noOfUnitsSold")
    market_value = extract("aggregateMarketValue")
    outstanding = extract("noOfUnitsOutstanding")

    if not (shares and outstanding):
        return None

    pct = (Decimal(shares) / Decimal(outstanding)) * 100
    pct_str = f"{pct:.6f}"

    return {
        "issuer": issuer,
        "relationship": relationship,
        "shares_sold": int(shares),
        "market_value": float(market_value),
        "outstanding_shares": int(outstanding),
        "pct_of_company": pct_str
    }

def get_insider_signal(relationship, pct_sold):
    pct_float = float(pct_sold)
    if "Officer" in relationship or "Director" in relationship:
        if pct_float > 1.0:
            return "🔴 MAJOR INSIDER SELLING", "#FF0000"
        elif pct_float > 0.1:
            return "🟠 INSIDER SELLING", "#FFA500"
        else:
            return "🟡 Minor Insider Sale", "#FFD700"
    else:
        return "🔵 Institutional Sale", "#007BFF"

def format_sec_filing_date(updated_string):
    """Convert SEC updated string to readable format with timezone"""
    try:
        # Parse the ISO format: 2024-01-15T16:30:45-05:00
        dt = datetime.fromisoformat(updated_string.replace('Z', '+00:00'))
        # Convert to Eastern Time (SEC is based in DC)
        et = pytz.timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        
        # Format as readable string
        formatted = dt_et.strftime('%B %d, %Y at %I:%M %p ET')
        return formatted, dt_et
    except:
        return updated_string, None
    
def send_batch_email(all_filings, all_charts):
    """Send a single email with all new filings compiled together"""
    if not all_filings:
        print("No new filings to send")
        return
    
    # Count filings by type
    filing_counts = {}
    for filing in all_filings:
        form_type = filing['form_type']
        filing_counts[form_type] = filing_counts.get(form_type, 0) + 1
    
    # Create summary for subject line
    summary_parts = []
    for form_type, count in filing_counts.items():
        summary_parts.append(f"{count} {form_type}")
    
    subject = f"📋 SEC Filings Update: {', '.join(summary_parts)}"
    
    # Create email header
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 30px;">
            <h1 style="margin: 0; font-size: 32px;">📋 SEC Filings Summary</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">
                {len(all_filings)} new filing{'s' if len(all_filings) != 1 else ''} found
            </p>
            <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">
                Run Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p ET')}
            </p>
        </div>
    """
    
    # Add each filing section
    for i, filing in enumerate(all_filings):
        # Add separator between filings (except for first one)
        if i > 0:
            html_body += """
            <div style="height: 2px; background: linear-gradient(to right, transparent, #ddd, transparent); 
                        margin: 40px 0;"></div>
            """
        
        html_body += filing['html_content']
    
    # Close HTML
    html_body += """
    </body>
    </html>
    """
    
    # Send email with all charts
    send_html_email_with_charts(subject, html_body, all_charts)

def send_html_email_with_charts(subject, html_body, charts_dict):
    """Send HTML email with multiple embedded charts"""
    msg = MIMEMultipart('related')
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    
    # Add HTML content
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText("HTML email not supported", 'plain'))
    msg_alternative.attach(MIMEText(html_body, 'html'))
    msg.attach(msg_alternative)
    
    # Add all charts
    for chart_id, chart_base64 in charts_dict.items():
        if chart_base64:
            chart_data = base64.b64decode(chart_base64)
            chart_image = MIMEImage(chart_data)
            chart_image.add_header('Content-ID', f'<{chart_id}>')
            msg.attach(chart_image)
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    form_types = ["EFFECT", "S-1MEF", "8-k", "144", "SD"]
    notified = load_notified()
    
    # Collect all new filings
    all_filings = []
    all_charts = {}
    chart_counter = 0
    
    for form in form_types:
        print(f"\nChecking filings for form type: {form.upper()}")
        filings = get_filings(form, count=1)

        for f in filings:
            match = re.search(r"/data/(\d+)/(\d{10,})", f['link'])
            if match:
                entry_id = f"{form}-{match.group(1)}-{match.group(2)}"
            else:
                entry_id = f"{form}-{f['link']}"
            
            if entry_id in notified:
                print(f"Already notified for {entry_id}")
                continue

            filing_data = None
            
            if form == "S-1MEF":
                company_name = extract_company_name(f['title'])
                
                # Get stock data
                ticker = get_ticker_from_name(company_name)
                chart_base64, stock_html = None, ""
                chart_id = None
                
                if ticker:
                    chart_base64, stock_html = get_stock_data_and_chart(ticker)
                    if chart_base64:
                        chart_counter += 1
                        chart_id = f"stock_chart_{chart_counter}"
                        all_charts[chart_id] = chart_base64
                        # Update the stock_html to use the unique chart ID
                        stock_html = stock_html.replace('cid:stock_chart', f'cid:{chart_id}')

                explanation_html = create_filing_explanation_section("S-1MEF")
    
                html_content = f"""
                <div style="background: white; padding: 25px; border-radius: 15px; margin: 20px 0; 
                            box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                        <h2 style="margin: 0; font-size: 24px;">📋 S-1MEF FILING</h2>
                        <h3 style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold;">{company_name}</h3>
                    </div>
                    
                    {explanation_html}
                    
                    {create_filing_info_section(f['updated'], "IPO AMENDMENT FILED", 
                        "Company updated their IPO registration - possible pricing/timing changes", 
                        "#2196f3")}
                    
                    {stock_html}
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; 
                            border-left: 6px solid #2196f3;">
                        <p style="font-size: 16px; margin: 0; color: #333;"><strong>📅 Filed:</strong> {f['updated']}</p>
                    </div>
                    {create_links_section(f['link'])}
                </div>
                """
                
                filing_data = {
                    'form_type': 'S-1MEF',
                    'company': company_name,
                    'html_content': html_content,
                    'entry_id': entry_id
                }

            elif form == "EFFECT":
                # Use the enhanced function instead
                text, underlying_form, eff_date, form_explanation = get_effect_text_and_type_enhanced(f['link'])
                
                # Skip N-2 forms
                if underlying_form and underlying_form.upper() == "N-2":
                    print(f"Skipping N-2 EFFECT filing: {f['title']}")
                    continue
                    
                company_name = extract_company_name(f['title'])
                
                # Get stock data
                ticker = get_ticker_from_name(company_name)
                chart_base64, stock_html = None, ""
                chart_id = None
                
                if ticker:
                    chart_base64, stock_html = get_stock_data_and_chart(ticker)
                    if chart_base64:
                        chart_counter += 1
                        chart_id = f"stock_chart_{chart_counter}"
                        all_charts[chart_id] = chart_base64
                        stock_html = stock_html.replace('cid:stock_chart', f'cid:{chart_id}')
                
                # Create explanation section for the underlying form
                explanation_html = ""
                if form_explanation:
                    explanation_html = f"""
                    <div style="background: linear-gradient(135deg, {form_explanation['color']}20, {form_explanation['color']}10); 
                                padding: 20px; border-radius: 10px; margin: 20px 0; 
                                border-left: 4px solid {form_explanation['color']};">
                        <div style="display: flex; align-items: center; margin-bottom: 15px; flex-wrap: wrap;">
                            <h3 style="margin: 0; color: {form_explanation['color']}; font-size: 18px; font-weight: bold;">
                                {form_explanation['signal']} {form_explanation['name']} - NOW EFFECTIVE
                            </h3>
                            <span style="margin-left: auto; padding: 4px 12px; background: {form_explanation['color']}; 
                                        color: white; border-radius: 20px; font-size: 12px; font-weight: bold;">
                                {form_explanation['significance']}
                            </span>
                        </div>
                        <p style="margin: 0; color: #333; font-size: 15px; line-height: 1.5;">
                            💡 <strong>What this means:</strong> {form_explanation['description']} 
                            <strong>The SEC has now approved this registration, allowing the company to proceed with their offering.</strong>
                        </p>
                    </div>
                    """
                
                html_content = f"""
                <div style="background: white; padding: 25px; border-radius: 15px; margin: 20px 0; 
                            box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                                color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                        <h2 style="margin: 0; font-size: 24px;">✅ EFFECT FILING</h2>
                        <h3 style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold;">{company_name}</h3>
                    </div>
                    
                    {explanation_html}
                    
                    {create_filing_info_section(f['updated'], "REGISTRATION EFFECTIVE", 
                        "Company can now legally sell securities to public", 
                        "#4caf50")}
                    
                    {stock_html}
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; 
                            border-left: 6px solid #4caf50;">
                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>📋 Underlying Form:</strong> {underlying_form}</p>
                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>✅ Effective Date:</strong> {eff_date}</p>
                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>📅 Filed:</strong> {f['updated']}</p>
                    </div>
                    {create_links_section(f['link'])}
                </div>
                """
                
                filing_data = {
                    'form_type': 'EFFECT',
                    'company': company_name,
                    'html_content': html_content,
                    'entry_id': entry_id
                }

            elif form == "8-k":
                txt_url = convert_to_txt_link(f['link'])
                try:
                    text = fetch_and_clean_txt(txt_url)
                    items = extract_items(text)
                    summaries, overall_signal = summarize_items_enhanced(items)
                    
                    if not summaries:
                        continue
                    
                    company_name = extract_company_name(f['title'])
                    signal_color = get_signal_color(overall_signal)
                    
                    # Get stock data
                    ticker = get_ticker_from_name(company_name)
                    chart_base64, stock_html = None, ""
                    chart_id = None
                    
                    if ticker:
                        chart_base64, stock_html = get_stock_data_and_chart(ticker)
                        if chart_base64:
                            chart_counter += 1
                            chart_id = f"stock_chart_{chart_counter}"
                            all_charts[chart_id] = chart_base64
                            stock_html = stock_html.replace('cid:stock_chart', f'cid:{chart_id}')
                    
                    items_html = ""
                    for s in summaries:
                        items_html += f"""
                        <div style="margin: 15px 0; padding: 20px; background: #f8f9fa; 
                                    border-left: 6px solid {s['color']}; border-radius: 5px;">
                            <h4 style="margin: 0 0 10px 0; color: {s['color']}; font-size: 18px;">
                                {s['emoji']} Item {s['item']}: {s['description']}
                            </h4>
                            <div style="color: #333; font-size: 14px; line-height: 1.5;">{s['text']}</div>
                        </div>
                        """
                    
                    html_content = f"""
                    <div style="background: white; padding: 25px; border-radius: 15px; margin: 20px 0; 
                                box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <div style="background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%); 
                                    color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0; font-size: 24px;">⚡ 8-K FILING</h2>
                            <h3 style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold;">{company_name}</h3>
                        </div>
                        
                        {create_filing_info_section(f['updated'], overall_signal, 
                           "Material corporate events reported - see details below", 
                           signal_color)}
                        
                        {stock_html}
                        
                        <div style="margin-top: 25px;">
                            <h4 style="font-size: 20px; margin-bottom: 15px; color: #333;">📋 Events Reported:</h4>
                            {items_html}
                        </div>
                        
                        {create_links_section(f['link'], txt_url)}
                    </div>
                    """
                    
                    filing_data = {
                        'form_type': '8-K',
                        'company': company_name,
                        'html_content': html_content,
                        'entry_id': entry_id
                    }
                    
                    log_to_file8k(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {f['title']} | {f['updated']} | {txt_url}")

                except Exception as e:
                    print(f"Failed to process 8-K {txt_url}: {e}")

            elif form == "144":
                txt_url = convert_to_txt_link(f['link'])
                try:
                    data = parse_form144(txt_url)
                    if data and data['shares_sold'] > 5000:
                        company_name = data['issuer']
                        signal_text, signal_color = get_insider_signal(data['relationship'], data['pct_of_company'])
                        
                        # Get stock data
                        ticker = get_ticker_from_name(company_name)
                        chart_base64, stock_html = None, ""
                        chart_id = None
                        
                        if ticker:
                            chart_base64, stock_html = get_stock_data_and_chart(ticker)
                            if chart_base64:
                                chart_counter += 1
                                chart_id = f"stock_chart_{chart_counter}"
                                all_charts[chart_id] = chart_base64
                                stock_html = stock_html.replace('cid:stock_chart', f'cid:{chart_id}')
                        
                        # Add Form 144 explanation
                        form144_explanation = """
                        <div style="background: linear-gradient(135deg, #ff9a9e20, #ff9a9e10); 
                                    padding: 20px; border-radius: 10px; margin: 20px 0; 
                                    border-left: 4px solid #ff9a9e;">
                            <div style="display: flex; align-items: center; margin-bottom: 15px; flex-wrap: wrap;">
                                <h3 style="margin: 0; color: #ff9a9e; font-size: 18px; font-weight: bold;">
                                    📉 INSIDER TRADING NOTICE Form 144
                                </h3>
                                <span style="margin-left: auto; padding: 4px 12px; background: #ff9a9e; 
                                            color: white; border-radius: 20px; font-size: 12px; font-weight: bold;">
                                    MARKET IMPACT
                                </span>
                            </div>
                            <p style="margin: 0; color: #333; font-size: 15px; line-height: 1.5;">
                                💡 <strong>What this means:</strong> Corporate insiders (executives, directors, or large shareholders) 
                                must file Form 144 before selling restricted or control securities. Large sales can indicate 
                                insider sentiment about the company's prospects and may impact stock price through increased supply.
                            </p>
                        </div>
                        """
                        
                        html_content = f"""
                        <div style="background: white; padding: 25px; border-radius: 15px; margin: 20px 0; 
                                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                            <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                                        color: #333; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                                <h2 style="margin: 0; font-size: 24px;">📉 FORM 144 FILING</h2>
                                <h3 style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold;">{company_name}</h3>
                            </div>
                            
                            {form144_explanation}
                            
                            {create_filing_info_section(f['updated'], signal_text.replace('🔴 ', '').replace('🟠 ', '').replace('🟡 ', '').replace('🔵 ', ''), 
                        "Insider stock sale reported - potential market impact", 
                        signal_color)}
                            
                            {stock_html}
                            
                            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px;">
                                    <div>
                                        <h4 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">👤 Seller</h4>
                                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>Relationship:</strong> {data['relationship']}</p>
                                    </div>
                                    
                                    <div>
                                        <h4 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">📊 Sale Details</h4>
                                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>Shares Sold:</strong> {data['shares_sold']:,}</p>
                                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>Market Value:</strong> ${data['market_value']:,.0f}</p>
                                        <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>% of Company:</strong> {data['pct_of_company']}%</p>
                                    </div>
                                </div>
                            </div>
                            
                            {create_links_section(f['link'], txt_url)}
                        </div>
                        """
                        
                        filing_data = {
                            'form_type': '144',
                            'company': company_name,
                            'html_content': html_content,
                            'entry_id': entry_id
                        }
                        
                        log_entry = (f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                                f"{data['issuer']} | {data['relationship']} | "
                                f"Shares: {data['shares_sold']} | "
                                f"Value: ${data['market_value']:,} | "
                                f"Percent: {data['pct_of_company']}% | "
                                f"Link: {txt_url}")
                        log_form144(log_entry)

                except Exception as e:
                    print(f"Error parsing Form 144: {e}")
            
            elif form == "SD":
                txt_url = convert_to_txt_link(f['link'])
                try:
                    sd_data = parse_sd_filing(txt_url, f['link'])
                    company_name = extract_company_name(f['title'])
                    signal_text, signal_color = get_sd_signal(sd_data)
                    
                    # Get stock data
                    ticker = get_ticker_from_name(company_name)
                    chart_base64, stock_html = None, ""
                    chart_id = None
                    
                    if ticker:
                        chart_base64, stock_html = get_stock_data_and_chart(ticker)
                        if chart_base64:
                            chart_counter += 1
                            chart_id = f"stock_chart_{chart_counter}"
                            all_charts[chart_id] = chart_base64
                            stock_html = stock_html.replace('cid:stock_chart', f'cid:{chart_id}')
                    
                    # Create SD explanation section
                    sd_explanation = """
                    <div style="background: linear-gradient(135deg, #8B451320, #8B451310); 
                                padding: 20px; border-radius: 10px; margin: 20px 0; 
                                border-left: 4px solid #8B4513;">
                        <div style="display: flex; align-items: center; margin-bottom: 15px; flex-wrap: wrap;">
                            <h3 style="margin: 0; color: #8B4513; font-size: 18px; font-weight: bold;">
                                ⛏️ CONFLICT MINERALS DISCLOSURE (Form SD)
                            </h3>
                            <span style="margin-left: auto; padding: 4px 12px; background: #8B4513; 
                                        color: white; border-radius: 20px; font-size: 12px; font-weight: bold;">
                                ESG COMPLIANCE
                            </span>
                        </div>
                        <p style="margin: 0; color: #333; font-size: 15px; line-height: 1.5;">
                            💡 <strong>What this means:</strong> Companies must annually disclose whether their products contain 
                            conflict minerals (tin, tantalum, tungsten, gold) and if so, whether these minerals originated from 
                            the Democratic Republic of Congo or adjoining countries. This helps investors assess ESG risks and 
                            supply chain responsibility.
                        </p>
                    </div>
                    """
                    
                    # Build minerals details
                    minerals_html = ""
                    if sd_data and sd_data['minerals']:
                        minerals_list = ", ".join(sd_data['minerals'])
                        minerals_html = f"""
                        <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0; 
                                    border-left: 4px solid #4682B4;">
                            <h4 style="margin: 0 0 10px 0; color: #4682B4; font-size: 16px;">⛏️ Minerals Reported</h4>
                            <p style="margin: 0; color: #333; font-size: 14px;"><strong>Contains:</strong> {minerals_list}</p>
                            <p style="margin: 5px 0 0 0; color: #333; font-size: 14px;"><strong>DRC Status:</strong> {sd_data['drc_status']}</p>
                            {f'<p style="margin: 5px 0 0 0; color: #333; font-size: 14px;"><strong>Supply Chain Audit:</strong> {"Yes" if sd_data["smelter_audit"] else "Not Mentioned"}</p>' if sd_data['smelter_audit'] is not None else ''}
                        </div>
                        """
                    elif sd_data:
                        minerals_html = f"""
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                            <p style="margin: 0; color: #666; font-size: 14px; text-align: center;">
                                Status: {sd_data['drc_status']}
                            </p>
                        </div>
                        """
                    
                    html_content = f"""
                    <div style="background: white; padding: 25px; border-radius: 15px; margin: 20px 0; 
                                box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        <div style="background: linear-gradient(135deg, #8B4513 0%, #D2691E 100%); 
                                    color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0; font-size: 24px;">⛏️ SD FILING</h2>
                            <h3 style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold;">{company_name}</h3>
                        </div>
                        
                        {sd_explanation}
                        
                        {create_filing_info_section(f['updated'], signal_text.replace('✅ ', '').replace('⚠️ ', '').replace('🔍 ', '').replace('📋 ', ''), 
                            "Annual conflict minerals disclosure - ESG compliance reporting", 
                            signal_color)}
                        
                        {stock_html}
                        
                        {minerals_html}
                        
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; 
                                border-left: 6px solid #8B4513;">
                            <h4 style="margin: 0 0 10px 0; color: #333; font-size: 18px;">📋 Filing Details</h4>
                            <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>📅 Filed:</strong> {f['updated']}</p>
                            <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>📄 Form Type:</strong> Specialized Disclosure (SD)</p>
                            <p style="font-size: 16px; margin: 5px 0; color: #333;"><strong>🎯 Purpose:</strong> Conflict Minerals Compliance</p>
                        </div>
                        
                        {create_links_section(f['link'], txt_url)}
                    </div>
                    """
                    
                    filing_data = {
                        'form_type': 'SD',
                        'company': company_name,
                        'html_content': html_content,
                        'entry_id': entry_id
                    }
                    
                    # Log SD filing
                    log_entry = (f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"{company_name} | "
                            f"DRC Status: {sd_data['drc_status'] if sd_data else 'Unknown'} | "
                            f"Minerals: {', '.join(sd_data['minerals']) if sd_data and sd_data['minerals'] else 'None'} | "
                            f"Link: {txt_url}")
                    log_sd_filing(log_entry)

                except Exception as e:
                    print(f"Error processing SD filing: {e}")

            # Add filing to batch if we have data
            if filing_data:
                all_filings.append(filing_data)
                print(f"Added {filing_data['form_type']} filing for {filing_data['company']}")
    
    # Send batch email if we have new filings
    if all_filings:
        print(f"\nSending batch email with {len(all_filings)} filings...")
        send_batch_email(all_filings, all_charts)
        
        # Mark all as notified after successful email send
        for filing in all_filings:
            save_notified(filing['entry_id'])
            
        # Log S-1MEF entries
        for filing in all_filings:
            if filing['form_type'] == 'S-1MEF':
                log_to_file(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {filing['company']} | BATCH EMAIL")
                
        print("✅ Batch email sent successfully!")
    else:
        print("No new filings found.")