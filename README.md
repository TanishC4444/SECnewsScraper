# SEC News Scraper

## Overview

SEC News Scraper is an automated Python application that monitors the SEC EDGAR system for critical corporate filings in real-time. The system aggregates multiple filing types into consolidated email reports with comprehensive financial analysis, stock charts, and intelligent signal detection for investment decision-making.

**Repository:** https://github.com/TanishC4444/SECnewsScraper  
**Language:** Python 100%  
**Total Commits:** 2,750+  
**Automation:** GitHub Actions (scheduled execution)

## Architecture

### Core Components

**main.py** - Central orchestration engine containing:
- Filing retrieval and parsing logic
- Email notification system with HTML rendering
- Stock data integration via yfinance
- Chart generation using matplotlib
- Log file management for duplicate prevention

### Monitored Filing Types

**Form 8-K** - Material corporate events requiring immediate disclosure:
- Item-based reporting (1.01-9.01) covering acquisitions, bankruptcy, leadership changes, financial restatements
- Intelligent signal classification: VERY BEARISH, BEARISH, WATCH, MAJOR WATCH, NEUTRAL
- Real-time sentiment analysis based on reported items

**Form 144** - Insider trading notices:
- Corporate insiders filing to sell restricted/control securities
- Tracks: insider identity, share quantity, market value, percentage of company
- Signal classification based on insider role and sale size
- Market impact assessment for institutional vs. officer sales

**S-1/S-1MEF** - IPO registration statements:
- Initial public offering documents and amendments
- MEF = Most Recent Effective Amendment (final IPO details)
- Tracks: company information, offering details, pricing updates

**EFFECT Filings** - Registration effectiveness notices:
- SEC approval allowing companies to legally sell registered securities
- Links to underlying form types (S-1, S-3, F-1, etc.)
- Critical timing signal for imminent market activity
- Filters out N-2 forms (closed-end funds)

**SD Filings** - Conflict minerals disclosure:
- Annual ESG compliance reporting for supply chain transparency
- Tracks: tin, tantalum, tungsten, gold sourcing
- DRC (Democratic Republic of Congo) conflict status assessment
- ESG risk signals: COMPLIANT, RISK, UNCLEAR, NO CONFLICT MINERALS

### Data Flow

```
SEC EDGAR RSS Feed → Parse XML → Filter by Form Type → 
Check Processed Logs → Extract Metadata → Fetch Full Filing → 
Parse Content → Get Stock Data → Generate Charts → 
Compile HTML Email → Send via SMTP → Update Logs
```

## Technical Implementation

### SEC EDGAR Integration

**Data Source:**
```python
url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type={form_type}&count={count}&output=atom"
headers = {"User-Agent": "SECscraper/1.0 (tanishc4444@gmail.com)"}
```

**Parsing Strategy:**
- XML/Atom feed parsing via ElementTree
- Extracts: title, link, updated timestamp
- Processes up to 5 most recent filings per form type
- RSS feed polled on scheduled intervals

**URL Construction:**
```python
# Convert index URL to raw text version
def convert_to_txt_link(index_url):
    return index_url.replace("-index.htm", ".txt")

# Build direct XML URL for EFFECT filings
effect_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/xslEFFECTX01/primary_doc.xml"
```

### Filing-Specific Parsers

**Form 8-K Parser:**
```python
def extract_items(text):
    """Extract Item sections using regex pattern matching"""
    pattern = r"(Item\s+\d+\.\d+.*?)(?=(Item\s+\d+\.\d+)|SIGNATURES)"
    matches = re.findall(pattern, text, flags=re.S | re.I)
    return [m[0].strip() for m in matches]

def summarize_items_enhanced(items):
    """Map items to predefined signals and descriptions"""
    # Item 1.01: Material Agreement → NEUTRAL
    # Item 1.03: Bankruptcy → VERY BEARISH
    # Item 2.02: Financial Results → WATCH
    # Item 4.02: Financial Restatement → VERY BEARISH
    # Item 5.02: Leadership Change → WATCH
```

**Signal Classification System:**
```python
eight_k_items_info = {
    "1.01": ("📋 Material Agreement", "🟢", "NEUTRAL"),
    "1.03": ("💀 Bankruptcy/Receivership", "🔴", "VERY BEARISH"),
    "2.02": ("📊 Financial Results", "🟡", "WATCH"),
    "2.03": ("💸 New Debt/Obligation", "🔴", "BEARISH"),
    "4.02": ("⚠️ Financial Restatement", "🔴", "VERY BEARISH"),
    "5.01": ("👑 Control Change", "🟡", "MAJOR WATCH"),
    "5.02": ("👔 Leadership Change", "🟡", "WATCH"),
}
```

**Form 144 Parser:**
```python
def parse_form144(txt_url):
    """Extract XML tags from Form 144 text filing"""
    # Extract using regex: <tag>content</tag>
    company = extract("issuerName")
    issuer = extract("nameOfPersonForWhoseAccountTheSecuritiesAreToBeSold")
    relationship = extract("relationshipToIssuer")
    shares = extract("noOfUnitsSold")
    market_value = extract("aggregateMarketValue")
    outstanding = extract("noOfUnitsOutstanding")
    
    # Calculate percentage of company
    pct = (Decimal(shares) / Decimal(outstanding)) * 100
    return {
        "shares_sold": int(shares),
        "market_value": float(market_value),
        "pct_of_company": str(pct)
    }

def get_insider_signal(relationship, pct_sold):
    """Classify insider sale severity"""
    if "Officer" in relationship or "Director" in relationship:
        if float(pct_sold) > 1.0:
            return "🔴 MAJOR INSIDER SELLING", "#FF0000"
        elif float(pct_sold) > 0.1:
            return "🟠 INSIDER SELLING", "#FFA500"
        else:
            return "🟡 Minor Insider Sale", "#FFD700"
    else:
        return "🔵 Institutional Sale", "#007BFF"
```

**EFFECT Filing Parser:**
```python
def get_effect_text_and_type_enhanced(index_link):
    """Parse EFFECT XML and identify underlying form type"""
    # Extract CIK and accession number from URL
    match = re.search(r'/data/(\d+)/(\d{10,})/', index_link)
    cik, accession = match.groups()
    
    # Build direct XML URL
    effect_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/xslEFFECTX01/primary_doc.xml"
    
    # Parse XML for form type and effective date
    root = ET.fromstring(response.content)
    form_type = next((elem.text.strip() for elem in root.iter() 
                     if elem.tag.lower().endswith("formtype")), None)
    eff_date = next((elem.text.strip() for elem in root.iter() 
                    if elem.tag.lower().endswith("effectivedate")), None)
    
    # Get explanation for underlying form
    explanation = get_filing_explanation(form_type)
    return text_content, form_type, eff_date, explanation
```

**SD Filing Parser:**
```python
def parse_sd_filing(txt_url, index_url):
    """Parse conflict minerals disclosure"""
    content = requests.get(txt_url).text.lower()
    
    # Detect minerals mentioned
    minerals_mentioned = []
    if any(term in content for term in ['tin', 'cassiterite']):
        minerals_mentioned.append('Tin')
    if any(term in content for term in ['tantalum', 'columbite']):
        minerals_mentioned.append('Tantalum')
    if any(term in content for term in ['tungsten', 'wolframite']):
        minerals_mentioned.append('Tungsten')
    if 'gold' in content:
        minerals_mentioned.append('Gold')
    
    # Determine DRC conflict status
    if "drc conflict free" in content:
        drc_status = "DRC Conflict Free"
    elif "not found to be drc conflict free" in content:
        drc_status = "Not DRC Conflict Free"
    elif "undeterminable" in content:
        drc_status = "Undeterminable"
    elif "no conflict minerals" in content:
        drc_status = "No Conflict Minerals"
    
    return {
        "minerals": minerals_mentioned,
        "drc_status": drc_status,
        "smelter_audit": 'smelter' in content or 'refiner' in content
    }
```

### Stock Market Integration

**Ticker Symbol Resolution:**
```python
def get_ticker_from_name(company_name):
    """Query Yahoo Finance search API for ticker symbol"""
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": company_name, "quotesCount": 1, "newsCount": 0}
    response = requests.get(url, params=params)
    data = response.json()
    
    if "quotes" in data and data["quotes"]:
        return data["quotes"][0]["symbol"]
    return None
```

**Comprehensive Stock Data Retrieval:**
```python
def get_stock_data_and_chart(ticker):
    """Fetch multi-period price history and fundamentals"""
    stock = yf.Ticker(ticker)
    
    # Historical data for different timeframes
    hist_5d = stock.history(period="5d", interval="1d")
    hist_1m = stock.history(period="1mo")
    hist_3m = stock.history(period="3mo")
    hist_1y = stock.history(period="1y")
    
    # Fundamental metrics from info dict
    info = stock.info
    metrics = {
        'currentPrice': hist_5d['Close'].iloc[-1],
        'previousClose': info.get('previousClose'),
        'marketCap': info.get('marketCap'),
        'volume': info.get('volume'),
        'peRatio': info.get('trailingPE'),
        'pbRatio': info.get('priceToBook'),
        'dividendYield': info.get('dividendYield'),
        'beta': info.get('beta'),
        'dayLow': info.get('dayLow'),
        'dayHigh': info.get('dayHigh'),
        'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
        'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh')
    }
    
    # Calculate performance metrics
    last_price = hist_5d['Close'].iloc[-1]
    prev_close = info.get('previousClose')
    pct_change = ((last_price - prev_close) / prev_close * 100)
    
    qtd_start = hist_3m['Close'].iloc[0]
    qtd_change = ((last_price - qtd_start) / qtd_start * 100)
    
    ytd_start = hist_1y['Close'].iloc[0]
    ytd_change = ((last_price - ytd_start) / ytd_start * 100)
    
    return chart_base64, stock_html
```

**Quarterly Earnings Data:**
```python
def get_quarterly_data_table(ticker):
    """Fetch and format quarterly financial statements"""
    stock = yf.Ticker(ticker)
    
    # Get quarterly income statement (last 4 quarters)
    quarterly_income = stock.quarterly_income_stmt
    recent_quarters = quarterly_income.iloc[:, :4]
    
    # Extract key metrics
    key_metrics = {
        'Total Revenue': 'Total Revenue',
        'Net Income': 'Net Income',
        'Gross Profit': 'Gross Profit',
        'Operating Income': 'Operating Income'
    }
    
    # Format values in millions/billions
    for metric_key in key_metrics:
        value = recent_quarters.loc[metric_key, quarter_date]
        if abs(value) >= 1e9:
            formatted = f"${value/1e9:.2f}B"
        elif abs(value) >= 1e6:
            formatted = f"${value/1e6:.1f}M"
    
    # Get next earnings date
    earnings_date = stock.info.get('earningsDate')
    
    return quarterly_html
```

### Chart Generation

**Matplotlib Configuration:**
```python
def get_stock_data_and_chart(ticker):
    """Generate professional dark-theme stock chart"""
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                   gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#1a1a1a')
    
    # Price line chart with gradient fill
    line_color = '#00ff88' if pct_change > 0 else '#ff4757'
    ax1.plot(hist_1m.index, hist_1m['Close'], 
            color=line_color, linewidth=3, alpha=0.9)
    ax1.fill_between(hist_1m.index, hist_1m['Close'], 
                     alpha=0.3, color=line_color)
    
    # Volume bar chart
    ax2.bar(hist_1m.index, hist_1m['Volume'], 
           alpha=0.6, color='#3c4043', width=0.8)
    
    # Styling with white text for readability
    ax1.set_title(f'{ticker} - 30 Day Performance & Volume', 
                 fontsize=20, fontweight='bold', color='white', pad=20)
    ax1.tick_params(colors='white', labelsize=12)
    ax2.tick_params(colors='white', labelsize=10)
    
    # Convert to base64 for email embedding
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', 
               facecolor='#1a1a1a', edgecolor='none')
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return chart_base64, stock_html
```

### Email System

**Batch Email Compilation:**
```python
def send_batch_email(all_filings, all_charts):
    """Consolidate multiple filings into single HTML email"""
    
    # Count filings by type for subject line
    filing_counts = {}
    for filing in all_filings:
        form_type = filing['form_type']
        filing_counts[form_type] = filing_counts.get(form_type, 0) + 1
    
    # Create subject: "📋 SEC Filings Update: 2 8-K, 1 S-1MEF, 1 EFFECT"
    summary = ', '.join([f"{count} {form}" for form, count in filing_counts.items()])
    subject = f"📋 SEC Filings Update: {summary}"
    
    # Build HTML with header
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 25px; border-radius: 15px;">
            <h1>📋 SEC Filings Summary</h1>
            <p>{len(all_filings)} new filing{'s' if len(all_filings) != 1 else ''}</p>
            <p>Run Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p ET')}</p>
        </div>
    """
    
    # Append each filing's HTML content
    for filing in all_filings:
        html_body += filing['html_content']
    
    html_body += "</body></html>"
    
    send_html_email_with_charts(subject, html_body, all_charts)
```

**MIME Email Construction:**
```python
def send_html_email_with_charts(subject, html_body, charts_dict):
    """Send multipart email with embedded chart images"""
    msg = MIMEMultipart('related')
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    
    # Add HTML alternative
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText("HTML email not supported", 'plain'))
    msg_alternative.attach(MIMEText(html_body, 'html'))
    msg.attach(msg_alternative)
    
    # Attach all charts with unique Content-IDs
    for chart_id, chart_base64 in charts_dict.items():
        chart_data = base64.b64decode(chart_base64)
        chart_image = MIMEImage(chart_data)
        chart_image.add_header('Content-ID', f'<{chart_id}>')
        msg.attach(chart_image)
    
    # SMTP transmission
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
```

**HTML Template Structure:**
```python
def create_filing_info_section(updated_string, signal_type, description, color):
    """Generate consistent filing metadata section"""
    filing_date, filing_dt = format_sec_filing_date(updated_string)
    
    # Calculate time elapsed since filing
    now = datetime.now(pytz.timezone('US/Eastern'))
    diff = now - filing_dt
    if diff.days > 0:
        time_ago = f"({diff.days} day{'s' if diff.days != 1 else ''} ago)"
    else:
        hours = diff.seconds // 3600
        time_ago = f"({hours} hour{'s' if hours != 1 else ''} ago)"
    
    return f"""
    <div style="background: linear-gradient(135deg, {color}20, {color}10); 
                padding: 12px; border-radius: 6px; border-left: 3px solid {color};">
        <h3 style="color: {color};">📊 SIGNAL: {signal_type}</h3>
        <p>{description}</p>
        <div>{filing_date} {time_ago}</div>
    </div>
    """
```

### State Management

**Log File Architecture:**

All log files use pipe-delimited format for easy parsing:

```
# notified_log.txt - Master tracking of sent notifications
EFFECT-0001234567-0001234567890
S-1MEF-0001234567-0001234567890
8-k-0001234567-0001234567890

# eightk_log.txt - 8-K processing history
2024-12-21 10:30:00 | ACME Corp | 2024-12-20 | Item 2.02 | https://...

# form144_log.txt - Insider trading history
2024-12-21 10:30:00 | John Doe | Director | Shares: 50000 | Value: $2,500,000 | Percent: 0.25% | https://...

# s1mef_log.txt - IPO filing history
2024-12-21 10:30:00 | ACME Corp | BATCH EMAIL

# effect_filings_log.txt - Effectiveness tracking
[Currently uses notified_log.txt]

# sd_log.txt - Conflict minerals tracking
2024-12-21 10:30:00 | ACME Corp | DRC Status: DRC Conflict Free | Minerals: Tin, Gold | https://...
```

**Duplicate Prevention:**
```python
def load_notified():
    """Load processed filing IDs into memory set"""
    try:
        with open(NOTIFIED_LOG, "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

# Check before processing
notified = load_notified()
entry_id = f"{form}-{cik}-{accession}"

if entry_id in notified:
    print(f"Already notified for {entry_id}")
    continue

# After successful email send
def save_notified(entry_id):
    with open(NOTIFIED_LOG, "a") as f:
        f.write(entry_id + "\n")
```

### GitHub Actions Automation

**Workflow Configuration (.github/workflows/):**
```yaml
name: SEC Filing Scraper
on:
  schedule:
    # Run every 15 minutes during market hours (9:30 AM - 4:00 PM ET)
    - cron: '*/15 9-16 * * 1-5'
  workflow_dispatch:  # Manual trigger

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4 lxml yfinance matplotlib pandas pytz
      
      - name: Run scraper
        env:
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
        run: python main.py
      
      - name: Commit log updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add *.txt
          git commit -m "Update filing logs [skip ci]" || exit 0
          git push
```

**Execution Flow:**
1. GitHub Actions triggers on schedule (every 15 minutes during market hours)
2. Checks out repository with existing log files
3. Installs Python dependencies (requests, BeautifulSoup, yfinance, matplotlib, pandas)
4. Executes main.py with EMAIL_PASSWORD from GitHub Secrets
5. Commits updated log files back to repository
6. Log files persist across runs, preventing duplicate notifications

**Environment Variables:**
```python
# Configured in GitHub repository secrets
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'fallback_value')

# SMTP credentials for Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "tanishchauhan4444@gmail.com"
RECIPIENT_EMAIL = "tanishchauhan4444@gmail.com"
```

## Processing Pipeline

**Main Execution Loop:**
```python
if __name__ == "__main__":
    form_types = ["EFFECT", "S-1MEF", "8-k", "144", "SD", "S-1", "S-1/A"]
    notified = load_notified()
    
    all_filings = []  # Accumulator for batch email
    all_charts = {}   # Chart storage with unique IDs
    chart_counter = 0
    
    for form in form_types:
        filings = get_filings(form, count=1)  # Get latest filing
        
        for f in filings:
            # Generate unique entry ID
            entry_id = f"{form}-{cik}-{accession}"
            
            # Skip if already processed
            if entry_id in notified:
                continue
            
            # Form-specific processing
            if form == "8-k":
                txt_url = convert_to_txt_link(f['link'])
                text = fetch_and_clean_txt(txt_url)
                items = extract_items(text)
                summaries, signal = summarize_items_enhanced(items)
                
                # Get ticker and stock data
                company_name = extract_company_name(f['title'])
                ticker = get_ticker_from_name(company_name)
                chart_base64, stock_html = get_stock_data_and_chart(ticker)
                
                # Assign unique chart ID
                chart_counter += 1
                chart_id = f"stock_chart_{chart_counter}"
                all_charts[chart_id] = chart_base64
                
                # Build HTML content
                html_content = f"""
                <div>
                    <h2>⚡ 8-K FILING: {company_name}</h2>
                    {stock_html}
                    {items_html}
                    {links_html}
                </div>
                """
                
                all_filings.append({
                    'form_type': '8-K',
                    'company': company_name,
                    'html_content': html_content,
                    'entry_id': entry_id
                })
            
            # Similar processing for other form types...
    
    # Send consolidated batch email
    if all_filings:
        send_batch_email(all_filings, all_charts)
        
        # Mark all as notified
        for filing in all_filings:
            save_notified(filing['entry_id'])
```

## Signal Intelligence

### Form 8-K Item Classification

**Item Severity Matrix:**

| Item | Description | Signal | Business Impact |
|------|-------------|--------|-----------------|
| 1.01 | Material Agreement | NEUTRAL | Routine business |
| 1.03 | Bankruptcy | VERY BEARISH | Company survival risk |
| 2.02 | Financial Results | WATCH | Earnings release |
| 2.03 | New Debt | BEARISH | Leverage increase |
| 4.02 | Financial Restatement | VERY BEARISH | Accounting issues |
| 5.01 | Control Change | MAJOR WATCH | M&A activity |
| 5.02 | Leadership Change | WATCH | Management turnover |

**Aggregate Signal Logic:**
```python
def summarize_items_enhanced(items):
    total_signal = "NEUTRAL"
    
    for item in items:
        signal = eight_k_items_info[item_num][2]
        
        # Priority escalation
        if signal == "VERY BEARISH":
            total_signal = "VERY BEARISH"  # Highest priority
        elif signal == "BEARISH" and total_signal not in ["VERY BEARISH"]:
            total_signal = "BEARISH"
        elif signal in ["WATCH", "MAJOR WATCH"] and total_signal == "NEUTRAL":
            total_signal = "WATCH"
    
    return summaries, total_signal
```

### Form 144 Signal Logic

**Classification Criteria:**
```python
Insider Role + Sale Size = Signal Severity

Officer/Director:
  > 1.0% of company → 🔴 MAJOR INSIDER SELLING
  > 0.1% of company → 🟠 INSIDER SELLING
  ≤ 0.1% of company → 🟡 Minor Insider Sale

Non-Officer/Director:
  Any percentage → 🔵 Institutional Sale
```

**Minimum Threshold:** Only processes sales > 5,000 shares

### SD Filing Signal Logic

**ESG Classification:**
```python
DRC Status → Signal

"DRC Conflict Free" → ✅ ESG COMPLIANT (#28A745)
"Not DRC Conflict Free" → ⚠️ ESG RISK (#FF6B6B)
"No Conflict Minerals" → ✅ NO CONFLICT MINERALS (#28A745)
"Undeterminable" → 🔍 ESG UNCLEAR (#FFA500)
Other → 📋 ESG DISCLOSURE (#8B4513)
```

## Dependencies

**Core Libraries:**
```txt
requests>=2.31.0          # HTTP client for SEC EDGAR
beautifulsoup4>=4.12.0    # HTML/XML parsing
lxml>=4.9.0               # XML parser backend
yfinance>=0.2.28          # Yahoo Finance API wrapper
matplotlib>=3.7.0         # Chart generation
pandas>=2.0.0             # Data manipulation
pytz>=2023.3              # Timezone handling
```

**Standard Library:**
```python
xml.etree.ElementTree  # XML parsing
re                     # Regex pattern matching
smtplib               # SMTP email transmission
email.mime.*          # MIME email construction
datetime              # Timestamp handling
decimal               # Precise financial calculations
html                  # HTML entity decoding
base64                # Image encoding
io                    # Binary stream handling
os                    # Environment variables
```

## Configuration

**Email Settings:**
```python
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "tanishchauhan4444@gmail.com"
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # GitHub Secret
RECIPIENT_EMAIL = "tanishchauhan4444@gmail.com"
```

**SEC EDGAR Headers:**
```python
headers = {
    "User-Agent": "SECscraper/1.0 (tanishc4444@gmail.com)"
}
```
*Required by SEC to identify automated requests*

**Monitored Forms:**
```python
form_types = ["EFFECT", "S-1MEF", "8-k", "144", "SD", "S-1", "S-1/A"]
```

**Retrieval Limit:**
```python
count = 1  # Latest filing only (prevents duplicate processing)
```

## Execution Model

**Scheduled Automation:**
- GitHub Actions CRON: `*/15 9-16 * * 1-5`
- Executes every 15 minutes during market hours (9:30 AM - 4:00 PM ET, Monday-Friday)
- Automatic log file persistence via git commit/push
- Manual trigger available via workflow_dispatch

**Processing Sequence:**
1. Load existing notification log
2. Query SEC EDGAR RSS feeds for each form type
3. Check each filing against notified set
4. Parse new filings with form-specific logic
5. Resolve company ticker symbols
6. Fetch stock data and generate charts
7. Build HTML email sections
8. Compile batch email with all charts
9. Send via SMTP with embedded images
10. Update notification log
11. Commit log files to repository

## Security

**Credential Management:**
- Email password stored in GitHub Secrets
- Never committed to repository
- Injected at runtime via environment variable

**SEC Compliance:**
- User-Agent header identifies scraper and contact email
- Respects SEC rate limits (no aggressive polling)
- Retrieves only public EDGAR data

**Email Security:**
- TLS encryption via STARTTLS
- Gmail App Password (not primary password)
- Single recipient (no mass distribution)

## Output Format

**Email Structure:**
<img width="678" height="1290" alt="image" src="https://github.com/user-attachments/assets/4c3c11b9-4b4c-4de2-80cc-6a78dc0493bd" />

**Visual Design:**
- Gradient headers with form-specific colors
- Dark theme charts with white text for readability
- Color-coded signals (green, yellow, orange, red)
- Responsive HTML layout for mobile compatibility
- Embedded charts with unique Content-IDs

## Use Cases

**Investment Research:**
- Monitor IPO pipeline via S-1/MEF and EFFECT filings
- Track insider sentiment through Form 144 analysis
- Identify material corporate events via 8-K alerts
- Assess ESG compliance through SD disclosures

**Compliance Monitoring:**
- Automated tracking of regulatory filings
- Real-time alerts for material events
- Historical audit trail via log files
- Supply chain transparency monitoring (conflict minerals)

**Competitive Intelligence:**
- Track competitor filings and corporate actions
- Monitor market entry (IPOs) and exits (bankruptcies)
- Leadership changes and strategic pivots
- Financial performance through 8-K earnings releases

## Performance Characteristics

**Execution Time:**
- Single form type query: 2-5 seconds
- Complete 7-form scan: 15-30 seconds
- Chart generation per ticker: 3-5 seconds
- Email compilation and send: 2-3 seconds
- Total runtime: 30-60 seconds per execution

**Rate Limiting:**
- SEC EDGAR: No enforced limits (respectful 15-minute polling)
- Yahoo Finance: No explicit limits for yfinance library
- SMTP Gmail: 500 emails per day limit (not approached)

**Data Volume:**
- Average email size: 500KB - 2MB (depends on number of charts)
- Log file growth: ~50-200 lines per day
- Annual log size: ~20,000-75,000 lines (~2-7 MB)

## Error Handling

**Network Failures:**
```python
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"Failed to fetch {url}: {e}")
    continue  # Skip this filing, continue with others
```

**Parsing Errors:**
```python
try:
    data = parse_form144(txt_url)
    if not data:
        print(f"Failed to parse Form 144: {txt_url}")
        continue
except Exception as e:
    print(f"Error parsing Form 144: {e}")
    continue
```

**Ticker Resolution Failures:**
```python
ticker = get_ticker_from_name(company_name)
if not ticker:
    print(f"Could not resolve ticker for {company_name}")
    # Continue without stock data
    stock_html = ""
    chart_base64 = None
```

**Chart Generation Failures:**
```python
try:
    chart_base64, stock_html = get_stock_data_and_chart(ticker)
except Exception as e:
    print(f"Error generating chart for {ticker}: {e}")
    chart_base64 = None
    stock_html = "<p>Stock data unavailable</p>"
```

**Graceful Degradation:**
- If stock data unavailable, filing still processed without charts
- If ticker resolution fails, proceeds with company name only
- If specific item parsing fails, other items still processed
- Email sent even if some components fail

## Logging and Debugging

**Console Output:**
```python
print(f"\nChecking filings for form type: {form.upper()}")
print(f"Already notified for {entry_id}")
print(f"Added {filing_data['form_type']} filing for {filing_data['company']}")
print(f"\nSending batch email with {len(all_filings)} filings...")
print("✅ Batch email sent successfully!")
```

**File-Based Logging:**
```python
# 8-K processing log
log_to_file8k(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {f['title']} | {f['updated']} | {txt_url}")

# Form 144 log with complete details
log_entry = (f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{data['issuer']} | {data['relationship']} | "
            f"Shares: {data['shares_sold']} | "
            f"Value: ${data['market_value']:,} | "
            f"Percent: {data['pct_of_company']}% | "
            f"Link: {txt_url}")
log_form144(log_entry)

# SD filing log
log_entry = (f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{company_name} | "
            f"DRC Status: {sd_data['drc_status']} | "
            f"Minerals: {', '.join(sd_data['minerals'])} | "
            f"Link: {txt_url}")
log_sd_filing(log_entry)
```

## Maintenance

**Log File Rotation:**
```bash
# Manual log cleanup (run periodically)
# Keep last 1000 lines of each log
tail -1000 notified_log.txt > notified_log.tmp && mv notified_log.tmp notified_log.txt
tail -1000 eightk_log.txt > eightk_log.tmp && mv eightk_log.tmp eightk_log.txt
tail -1000 form144_log.txt > form144_log.tmp && mv form144_log.tmp form144_log.txt
tail -1000 s1mef_log.txt > s1mef_log.tmp && mv s1mef_log.tmp s1mef_log.txt
tail -1000 sd_log.txt > sd_log.tmp && mv sd_log.tmp sd_log.txt
```

**Dependency Updates:**
```bash
# Update all dependencies to latest compatible versions
pip install --upgrade requests beautifulsoup4 lxml yfinance matplotlib pandas pytz

# Test after updates
python main.py
```

**GitHub Actions Monitoring:**
- Check Actions tab for failed runs
- Review logs for parsing errors or API failures
- Monitor email delivery success
- Verify log file commits are occurring

## Troubleshooting

**No emails received:**
1. Check GitHub Actions run logs for errors
2. Verify EMAIL_PASSWORD secret is set correctly
3. Confirm Gmail App Password is valid (not revoked)
4. Check spam/junk folder
5. Verify notified_log.txt isn't blocking all filings

**Duplicate notifications:**
1. Check if notified_log.txt was corrupted or reset
2. Verify entry_id format matches between runs
3. Ensure git commit/push is succeeding in workflow

**Missing stock data:**
1. Yahoo Finance API may be rate limiting
2. Ticker resolution failing for company name
3. Company may not be publicly traded
4. Check yfinance library for deprecation warnings

**Chart rendering issues:**
1. Verify matplotlib backend is non-interactive (Agg)
2. Check DPI and figure size settings
3. Ensure white text color is applied to all labels
4. Verify base64 encoding is correct

**EFFECT filings showing N-2:**
```python
# Already filtered in code
if underlying_form and underlying_form.upper() == "N-2":
    print(f"Skipping N-2 EFFECT filing: {f['title']}")
    continue
```

## Future Enhancements

**Potential Features:**
- **SMS Alerts**: Twilio integration for critical filings (VERY BEARISH signals)
- **Database Storage**: Migrate from log files to SQLite/PostgreSQL for better querying
- **Web Dashboard**: Flask/Django interface for viewing filing history and analytics
- **Sentiment Analysis**: NLP on 8-K item descriptions for deeper signal detection
- **Options Flow**: Integrate unusual options activity correlated with filings
- **Slack/Discord Webhooks**: Team notifications via popular messaging platforms
- **Custom Filters**: User-defined watchlists for specific companies or sectors
- **Historical Analysis**: Backfill historical filings for trend analysis
- **Machine Learning**: Predict stock price impact based on filing patterns
- **Portfolio Integration**: Connect with brokerage APIs for automated trading signals

**Technical Improvements:**
- Async HTTP requests for faster parallel processing
- Redis caching for ticker resolution and stock data
- Docker containerization for consistent execution environment
- Comprehensive test suite with mock SEC responses
- CI/CD pipeline with automated testing
- Structured logging with log levels and rotation
- Prometheus metrics for monitoring and alerting

## Legal and Compliance

**SEC Data Usage:**
- All data sourced from public SEC EDGAR system
- No authentication required for public filings
- User-Agent header identifies scraper per SEC guidelines
- Respectful polling intervals to avoid overloading SEC servers

**Email Disclaimer:**
- Data provided for informational purposes only
- Not investment advice or recommendation to buy/sell securities
- Users should conduct independent research and consult financial advisors
- Past performance does not guarantee future results

**Data Accuracy:**
- Stock data from Yahoo Finance may have delays or errors
- Ticker resolution may fail for newly public companies
- Parsing logic may not capture all nuances of complex filings
- Users should verify critical information with primary sources

## Repository Statistics

**Commit History:**
- 2,750+ commits (mostly automated log updates)
- Single contributor
- Active development and maintenance
- Regular GitHub Actions executions during market hours

**File Structure:**
```
SECnewsScraper/
├── .github/
│   └── workflows/
│       └── scraper.yml           # GitHub Actions workflow
├── main.py                        # Core application logic (2000+ lines)
├── notified_log.txt              # Master notification tracking
├── eightk_log.txt                # 8-K processing history
├── form144_log.txt               # Form 144 processing history
├── s1mef_log.txt                 # S-1/MEF processing history
├── sd_log.txt                    # SD processing history
├── effect_filings_log.txt        # EFFECT processing history
├── EIGHTK_LOG_FILE               # Legacy log file
└── README.md                     # This documentation
```

## Development Setup

**Local Execution:**
```bash
# Clone repository
git clone https://github.com/TanishC4444/SECnewsScraper.git
cd SECnewsScraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install requests beautifulsoup4 lxml yfinance matplotlib pandas pytz

# Set environment variable
export EMAIL_PASSWORD="your_gmail_app_password"

# Run scraper
python main.py
```

**Testing Without Email:**
```python
# Comment out email sending in main.py
if all_filings:
    print(f"\nWould send batch email with {len(all_filings)} filings")
    # send_batch_email(all_filings, all_charts)
    
    # Still mark as notified for testing
    for filing in all_filings:
        save_notified(filing['entry_id'])
```

## Contact and Support

**Developer:** TanishC4444  
**Email:** tanishchauhan4444@gmail.com  
**Repository:** https://github.com/TanishC4444/SECnewsScraper

For issues, feature requests, or questions, please open a GitHub issue or contact the developer directly.

---

**Last Updated:** December 2024  
**Python Version:** 3.11+  
**License:** Not specified (personal project)
