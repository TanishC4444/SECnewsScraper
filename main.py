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

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "tanishchauhan4444@gmail.com"
EMAIL_PASSWORD = "smgj lhbr xioz lqwu"
RECIPIENT_EMAIL = "tanishchauhan4444@gmail.com"

NOTIFIED_LOG = "notified_log.txt"

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
    """Get comprehensive stock stats and create professional chart"""
    try:
        ticker = ticker.strip().lstrip('$')
        stock = yf.Ticker(ticker)
        
        # Get comprehensive data
        info = stock.info
        hist_5d = stock.history(period="5d", interval="1d")
        hist_1m = stock.history(period="1mo")
        hist_3m = stock.history(period="3mo")
        hist_1y = stock.history(period="1y")
        
        # ADD THIS SECTION - Check for empty data
        if hist_5d.empty or hist_1m.empty:
            return None, None
            
        # ADD THIS SECTION - Calculate price changes
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
        
        # ADD THIS SECTION - Create the chart
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
        
        # Styling for price chart
        ax1.set_title(f'{ticker} - 30 Day Performance & Volume', 
                     fontsize=20, fontweight='bold', color='white', pad=20)
        ax1.set_ylabel('Price ($)', fontsize=14, color='#8e9297')
        ax1.grid(True, alpha=0.2, color='#5f6368')
        ax1.tick_params(colors='#8e9297', labelsize=12)
        
        # Styling for volume chart
        ax2.set_ylabel('Volume', fontsize=12, color='#8e9297')
        ax2.set_xlabel('Date', fontsize=14, color='#8e9297')
        ax2.grid(True, alpha=0.2, color='#5f6368')
        ax2.tick_params(colors='#8e9297', labelsize=10)
        
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
        
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', 
                   facecolor='#1a1a1a', edgecolor='none')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        plt.style.use('default')
        
        # Get quarterly HTML
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
        
        # Create comprehensive stock HTML
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
                    <h4 style="margin: 0; color: #bdc3c7; font-size: 13px; text-transform: uppercase;">Current Price</h4>
                    <p style="font-size: 24px; margin: 8px 0 0 0; font-weight: bold;">${last_price:.2f}</p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: #bdc3c7; font-size: 13px; text-transform: uppercase;">Daily Change</h4>
                    <p style="font-size: 20px; margin: 8px 0 0 0; font-weight: bold; color: {change_color};">
                        {change_arrow} {pct_change:.2f}%
                    </p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: #bdc3c7; font-size: 13px; text-transform: uppercase;">QTD Change</h4>
                    <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: {qtd_color};">
                        {f"{qtd_change:+.1f}%" if qtd_change else "N/A"}
                    </p>
                </div>
                <div style="text-align: center; padding: 18px; background: rgba(255,255,255,0.1); 
                           border-radius: 12px; border: 2px solid rgba(255,255,255,0.2);">
                    <h4 style="margin: 0; color: #bdc3c7; font-size: 13px; text-transform: uppercase;">YTD Change</h4>
                    <p style="font-size: 18px; margin: 8px 0 0 0; font-weight: bold; color: {ytd_color};">
                        {f"{ytd_change:+.1f}%" if ytd_change else "N/A"}
                    </p>
                </div>
            </div>
            
            <!-- Company Fundamentals -->
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0;">
                <h4 style="margin: 0 0 15px 0; color: #ecf0f1; font-size: 18px; text-align: center;">
                    🏢 Company Fundamentals
                </h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                    <div>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>Market Cap:</strong> 
                           {f"${market_cap/1e9:.1f}B" if market_cap else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>P/E Ratio:</strong> 
                           {f"{pe_ratio:.2f}" if pe_ratio else "N/A"}</p>
                    </div>
                    <div>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>P/B Ratio:</strong> 
                           {f"{pb_ratio:.2f}" if pb_ratio else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>Beta:</strong> 
                           {f"{beta:.2f}" if beta else "N/A"}</p>
                    </div>
                    <div>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>Dividend Yield:</strong> 
                           {f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A"}</p>
                        <p style="margin: 8px 0; font-size: 15px;"><strong>Volume:</strong> 
                           {f"{volume:,}" if volume else "N/A"}</p>
                    </div>
                </div>
            </div>
            
            <!-- Trading Ranges -->
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0;">
                <h4 style="margin: 0 0 15px 0; color: #ecf0f1; font-size: 18px; text-align: center;">
                    📊 Trading Ranges
                </h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px;">
                    <div style="text-align: center;">
                        <p style="margin: 0; color: #bdc3c7; font-size: 14px;">TODAY'S RANGE</p>
                        <p style="font-size: 18px; margin: 8px 0; font-weight: bold;">
                            ${info.get('dayLow', 'N/A')} - ${info.get('dayHigh', 'N/A')}
                        </p>
                    </div>
                    <div style="text-align: center;">
                        <p style="margin: 0; color: #bdc3c7; font-size: 14px;">52-WEEK RANGE</p>
                        <p style="font-size: 18px; margin: 8px 0; font-weight: bold;">
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

if __name__ == "__main__":
    form_types = ["EFFECT", "S-1MEF", "8-k", "144"]
    notified = load_notified()
    
    for form in form_types:
        print(f"\nLatest filings for form type: {form.upper()}")
        filings = get_filings(form, count=1)

        for f in filings:
            match = re.search(r"/data/(\d+)/(\d{10,})", f['link'])
            if match:
                entry_id = f"{form}-{match.group(1)}-{match.group(2)}"
            else:
                entry_id = f"{form}-{f['link']}"
            
            if entry_id in notified:
                continue

            elif form == "S-1MEF":
                company_name = extract_company_name(f['title'])
                
                # Get stock data
                ticker = get_ticker_from_name(company_name)
                chart_base64, stock_html = None, ""
                if ticker:
                    chart_base64, stock_html = get_stock_data_and_chart(ticker)
                
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; padding: 25px; border-radius: 10px; text-align: center;">
                        <h1 style="margin: 0; font-size: 28px;">📋 S-1MEF FILING</h1>
                        <h2 style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold;">{company_name}</h2>
                    </div>
                    
                    {create_filing_info_section(f['updated'], "IPO AMENDMENT FILED", 
                           "Company updated their IPO registration - possible pricing/timing changes", 
                           "#2196f3")}
                    
                    {stock_html}
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; 
                            border-left: 6px solid #2196f3;">
                        <p style="font-size: 16px; margin: 0;"><strong>📅 Filed:</strong> {f['updated']}</p>
                    </div>
                    {create_links_section(f['link'])}
                </body>
                </html>
                """
                
                send_html_email_with_chart(f"📋 S-1MEF: {company_name}", html_body, chart_base64)
                save_notified(entry_id)
                log_to_file(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {company_name} | {f['updated']} | {f['link']}")

            elif form == "EFFECT":
                text, underlying_form, eff_date = get_effect_text_and_type(f['link'])
                
                # Skip N-2 forms (mutual fund/closed-end fund registrations)
                if underlying_form and underlying_form.upper() == "N-2":
                    print(f"Skipping N-2 EFFECT filing: {f['title']}")
                    continue
                    
                company_name = extract_company_name(f['title'])
                
                # Get stock data
                ticker = get_ticker_from_name(company_name)
                chart_base64, stock_html = None, ""
                if ticker:
                    chart_base64, stock_html = get_stock_data_and_chart(ticker)
                
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 20px;">
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                                color: white; padding: 25px; border-radius: 10px; text-align: center;">
                        <h1 style="margin: 0; font-size: 28px;">✅ EFFECT FILING</h1>
                        <h2 style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold;">{company_name}</h2>
                    </div>
                    
                    {create_filing_info_section(f['updated'], "REGISTRATION EFFECTIVE", 
                           "Company can now legally sell securities to public", 
                           "#4caf50")}
                    
                    {stock_html}
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; 
                            border-left: 6px solid #4caf50;">
                        <p style="font-size: 16px; margin: 5px 0;"><strong>📋 Underlying Form:</strong> {underlying_form}</p>
                        <p style="font-size: 16px; margin: 5px 0;"><strong>✅ Effective Date:</strong> {eff_date}</p>
                        <p style="font-size: 16px; margin: 5px 0;"><strong>📅 Filed:</strong> {f['updated']}</p>
                    </div>
                    {create_links_section(f['link'])}
                </body>
                </html>
                """
                
                send_html_email_with_chart(f"✅ EFFECT: {company_name}", html_body, chart_base64)
                save_notified(entry_id)

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
                    if ticker:
                        chart_base64, stock_html = get_stock_data_and_chart(ticker)
                    
                    items_html = ""
                    for s in summaries:
                        items_html += f"""
                        <div style="margin: 15px 0; padding: 20px; background: white; 
                                    border-left: 6px solid {s['color']}; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h3 style="margin: 0 0 10px 0; color: {s['color']}; font-size: 20px;">
                                {s['emoji']} Item {s['item']}: {s['description']}
                            </h3>
                            <div style="color: #333; font-size: 15px; line-height: 1.5;">{s['text']}</div>
                        </div>
                        """
                    
                    html_body = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; margin: 20px;">
                        <div style="background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%); 
                                    color: white; padding: 25px; border-radius: 10px; text-align: center;">
                            <h1 style="margin: 0; font-size: 28px;">⚡ 8-K FILING</h1>
                            <h2 style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold;">{company_name}</h2>
                        </div>
                        
                        {create_filing_info_section(f['updated'], overall_signal, 
                           "Material corporate events reported - see details below", 
                           signal_color)}
                        
                        {stock_html}
                        
                        <div style="margin-top: 25px;">
                            <h3 style="font-size: 22px; margin-bottom: 20px;">📋 Events Reported:</h3>
                            {items_html}
                        </div>
                        
                        {create_links_section(f['link'], txt_url)}
                    </body>
                    </html>
                    """
                    
                    send_html_email_with_chart(f"⚡ 8-K {overall_signal}: {company_name}", html_body, chart_base64)
                    save_notified(entry_id)
                    log_to_file8k(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {f['title']} | {f['updated']} | {txt_url}")

                except Exception as e:
                    print(f"Failed to fetch {txt_url}: {e}")

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
                        if ticker:
                            chart_base64, stock_html = get_stock_data_and_chart(ticker)
                        
                        html_body = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif; margin: 20px;">
                            <div style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); 
                                        color: #333; padding: 25px; border-radius: 10px; text-align: center;">
                                <h1 style="margin: 0; font-size: 28px;">📉 FORM 144 FILING</h1>
                                <h2 style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold;">{company_name}</h2>
                            </div>
                            
                            {create_filing_info_section(f['updated'], signal_text.replace('🔴 ', '').replace('🟠 ', '').replace('🟡 ', '').replace('🔵 ', ''), 
                           "Insider stock sale reported - potential market impact", 
                           signal_color)}
                            
                            {stock_html}
                            
                            <div style="margin-top: 25px; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                                    <div>
                                        <h3 style="margin: 0 0 15px 0; color: #333; font-size: 20px;">👤 Seller</h3>
                                        <p style="font-size: 18px; margin: 5px 0;"><strong>Relationship:</strong> {data['relationship']}</p>
                                    </div>
                                    
                                    <div>
                                        <h3 style="margin: 0 0 15px 0; color: #333; font-size: 20px;">📊 Sale Details</h3>
                                        <p style="font-size: 18px; margin: 5px 0;"><strong>Shares Sold:</strong> {data['shares_sold']:,}</p>
                                        <p style="font-size: 18px; margin: 5px 0;"><strong>Market Value:</strong> ${data['market_value']:,.0f}</p>
                                        <p style="font-size: 18px; margin: 5px 0;"><strong>% of Company:</strong> {data['pct_of_company']}%</p>
                                    </div>
                                </div>
                            </div>
                            
                            {create_links_section(f['link'], txt_url)}
                        </body>
                        </html>
                        """
                        
                        send_html_email_with_chart(f"📉 FORM 144: {company_name} ({data['shares_sold']:,} shares)", html_body, chart_base64)
                        save_notified(entry_id)
                        
                        log_entry = (f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                                   f"{data['issuer']} | {data['relationship']} | "
                                   f"Shares: {data['shares_sold']} | "
                                   f"Value: ${data['market_value']:,} | "
                                   f"Percent: {data['pct_of_company']}% | "
                                   f"Link: {txt_url}")
                        log_form144(log_entry)

                except Exception as e:
                    print(f"Error parsing Form 144: {e}")