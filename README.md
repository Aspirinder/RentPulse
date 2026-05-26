# OLX & Otodom Real Estate Scraper 🏠🔍

An asynchronous Python scraper built with **Playwright** and **BeautifulSoup4** to extract real estate listings from **OLX.pl** and **Otodom.pl**.

## ✨ Key Features

- **Asynchronous Engine:** Powered by `asyncio` and `Playwright` for high-speed browser automation.
- **JSON Data Extraction:** Scrapes Otodom data directly from the hidden `__NEXT_DATA__` object, ensuring 100% accuracy and resilience to UI changes.
- **Smart Pagination:** - **OLX:** Detects the end of results via "0 listings found" messages or recommendation blocks.
  - **Otodom:** Monitors the "Next Page" button state (DOM attributes) to handle dynamic page limits.
- **Deep Data Mining:**
  - Extracts full technical specs (area, floor, building type, etc.).
  - Collects equipment lists (fridge, washing machine, dishwasher, etc.).
  - Tracks listing history (Creation Date vs. Last Update/Push-up Date).
- **Automated Export:** Cleans and saves all results directly into structured CSV files.

## 🛠 Tech Stack

- **Python 3.10+**
- **Playwright** (Browser automation)
- **BeautifulSoup4** (HTML parsing)
- **JSON & Regex** (Data processing)

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install playwright beautifulsoup4
   playwright install chromium