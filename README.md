<div align="center">
  <h1>📈 BharatQuant</h1>
  <p><b>Professional NSE + BSE Quantitative Stock Screener</b></p>
</div>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity)

> [!IMPORTANT]
> **DISCLAIMER**: This tool is for **educational and research purposes only**. It does NOT constitute financial advice, investment recommendations, or an offer to buy/sell securities. The author is not responsible for any financial losses or damages resulting from the use of this software. Always verify data with official exchange sources before making investment decisions.

A professional-grade financial stock screener that aggregates data from **NSE** and **BSE** to generate a comprehensive analysis in Excel. It combines price momentum, quarterly growth, and fundamental quality into a single, color-coded report.

## 📊 Report Column Dictionary

The generated report at `data/nse_bse_screener.xlsx` contains the following metrics:

| Column | Description | Why it matters |
| :--- | :--- | :--- |
| **Ticker / Name** | Stock identifier and Company Name | Basic identification. |
| **Trend** | Technical stage (e.g., Stage 2, Golden Cross) | Identifies stocks in confirmed bullish uptrends. |
| **RS Score** | Relative Strength vs Nifty 50 | Shows outperformance. >0 means it's beating the market. |
| **F-Score** | Piotroski Health Score (0-9) | 7-9 indicates a strong, high-quality turnaround company. |
| **Sales Growth % (YoY)** | Revenue growth vs Same Quarter Last Year | Confirms if the business is actually expanding. |
| **Profit Growth % (YoY)** | Net Profit growth vs Same Quarter Last Year | Key driver for stock price breakouts. |
| **Price** | Current closing price | Latest market valuation. |
| **MCap (Cr)** | Market Capitalization in ₹ Crores | Filters for company size (e.g., >100 Cr). |
| **P/E / P/B** | Price-to-Earnings and Price-to-Book | Basic valuation multiples (cheap vs expensive). |
| **ROE (1y / 3y) %** | Return on Equity (Latest and 3y Average) | Measures how efficiently the company uses shareholder money. |
| **ROCE %** | Return on Capital Employed | Measures overall profitability of all capital used. |
| **D/E** | Debt-to-Equity Ratio | Leverage check. < 1.0 is generally healthy. |
| **OPM %** | Operating Profit Margin | Shows the efficiency of the core business operations. |
| **Pledged %** | % of Promoter shares pledged | Warning sign if high (>25%). |
| **RSI** | Relative Strength Index (14-day) | Shows if the stock is overbought (>70) or oversold (<30). |
| **Volatility** | 1-year annualized price swings | Higher % means more aggressive price movements. |
| **50 / 200 DMA** | Daily Moving Averages | Used to identify support floors and trend direction. |
| **1y / 3y / 5y Rt %** | Multi-year Total Returns | Shows historical track record of wealth creation. |
| **Holdings %** | Promoter, FII, and Public % | Shows "Smart Money" (FII) interest vs Retail (Public). |
| **Sector / Industry** | Business categorization | Helps group similar companies for comparison. |

## 🎨 Color Coding Legend

- 🟩 **Green**: Bullish/Strong (e.g., RS Score > 0, F-Score 7-9, Growth > 20%, ROE > 15%).
- 🟥 **Red**: Bearish/Weak (e.g., Negative Growth, F-Score < 4, Death Cross, High Pledging).
- 🟨 **Yellow**: Caution (e.g., RSI overbought/oversold levels).

## 🚀 How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Screener**:
   ```bash
   python main.py
   ```
3. **View Results**: Open `data/nse_bse_screener.xlsx`.

## 📁 Project Structure
```text
.
├── main.py                 # Primary entry point
├── screener/               # Core logic modules
├── config/                 # Configuration templates
└── README.md               # Documentation
```

## 📜 License

<details>
<summary><b>View MIT License</b></summary>

BharatQuant - MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
</details>
