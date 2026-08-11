# SEC News Scraper

A Python automation pipeline that monitors SEC EDGAR filings, classifies filing signals, enriches results with market data, and sends consolidated email reports.

## Overview

The scraper monitors selected SEC filing types and turns new filings into structured reports. It combines EDGAR feeds, filing-specific parsers, market-data retrieval, chart generation, and SMTP email delivery.

## Features

- SEC EDGAR monitoring
- 8-K, Form 144, S-1/S-1MEF, EFFECT, and SD parsing
- Filing-specific signal classification
- Yahoo Finance market-data enrichment
- Matplotlib stock charts
- Consolidated HTML email reports
- Duplicate prevention through processed logs
- Scheduled GitHub Actions execution

## Prerequisites

- Python 3
- pip
- SMTP credentials for email delivery
- A descriptive SEC User-Agent containing contact information

## Installation

```bash
git clone https://github.com/TanishC4444/SECnewsScraper.git
cd SECnewsScraper
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Configuration

Store email credentials and other secrets in environment variables or GitHub Actions secrets. Do not hard-code credentials. When accessing SEC resources, use an appropriate User-Agent and respect SEC request limits.

## Quick Start

```bash
python main.py
```

## Data Flow

```text
SEC EDGAR → Parse filings → Deduplicate → Extract signals
          → Market data → Charts → HTML email → SMTP
```

## Automation

GitHub Actions can run the scraper on a schedule or manually. Test configuration changes manually before enabling scheduled execution.

## Testing

Use the repository's available test/development scripts with test credentials and configuration before production-style runs.

## Status

Active automation project.

## License

No separate license is currently specified in the repository.

## Support

Use GitHub Issues for bugs and feature requests.
