"""
Excel Export and Formatting Module for BharatQuant.

Handles:
1. Converting analytical results into a structured Pandas DataFrame.
2. Generating a professional Excel (.xlsx) file.
3. Applying color-coded conditional formatting for Bullish (Green) and Bearish (Red) signals.
4. Setting column widths and number formats (Currency, %, Multiples).
"""

import pandas as pd
import os
from datetime import datetime
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from .config import log, OUTPUT_FILE, HEADER_LABELS, WIDTH_MAP, FMT_MAP, TODAY

# Define Colors for UI Highlighting
GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")


def write_excel(rows: list):
    """
    Export the processed stock data to an Excel file with advanced formatting.
    Applies conditional colors:
    - 🟩 Green for high RS Scores, high F-Scores, and Strong Growth.
    - 🟥 Red for poor growth, high debt, or high share pledging.
    """
    if not rows:
        log.warning("No data rows to write to Excel.")
        return

    log.info(f"Generating professional report: {OUTPUT_FILE}...")
    df = pd.DataFrame(rows)

    # Ensure columns match the configuration order
    cols_to_use = [c for c in HEADER_LABELS if c in df.columns]
    df = df[cols_to_use]

    # Save to Excel
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Screener")
        ws = writer.sheets["Screener"]

        # Apply Formatting
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            for col_idx, (lbl, val) in enumerate(zip(df.columns, row), start=1):
                cell = ws.cell(row=row_idx, column=col_idx)

                # 1. Formatting Numbers (Currency, %, etc.)
                if lbl in FMT_MAP:
                    cell.number_format = FMT_MAP[lbl]

                # 2. Color Coding (The Visual 'Alpha')
                try:
                    # RS Score > 0 is bullish
                    if lbl == "RS Score" and val is not None:
                        if val > 0: cell.fill = GREEN_FILL
                        elif val < -20: cell.fill = RED_FILL
                    
                    # Piotroski F-Score (7-9 is great, 0-3 is weak)
                    if lbl == "F-Score" and val is not None:
                        if val >= 7: cell.fill = GREEN_FILL
                        elif val <= 3: cell.fill = RED_FILL
                    
                    # Growth %
                    if "Growth %" in lbl and val is not None:
                        if val > 20: cell.fill = GREEN_FILL
                        elif val < 0: cell.fill = RED_FILL
                    
                    # Trend Status
                    if lbl == "Trend" and val:
                        if "🚀" in str(val): cell.fill = GREEN_FILL
                        elif "📉" in str(val): cell.fill = RED_FILL

                    # ROE/ROCE Efficiency
                    if ("ROE" in lbl or "ROCE" in lbl) and val is not None:
                        if val > 20: cell.fill = GREEN_FILL
                        elif val < 10: cell.fill = RED_FILL
                    
                    # RSI Oversold/Overbought
                    if lbl == "RSI" and val is not None:
                        if val > 70: cell.fill = YELLOW_FILL
                        elif val < 30: cell.fill = YELLOW_FILL

                    # High Debt or High Pledging
                    if (lbl == "D/E" and val is not None and val > 2.0): cell.fill = RED_FILL
                    if (lbl == "Pledged %" and val is not None and val > 25): cell.fill = RED_FILL

                except: pass

        # 3. Final UI Adjustments (Header Freeze, Column Widths)
        ws.freeze_panes = "A2"
        for ci, lbl in enumerate(df.columns, start=1):
            width = WIDTH_MAP.get(lbl, 12)
            ws.column_dimensions[get_column_letter(ci)].width = width

    log.info(f"Report Successfully Generated! ✨ → {os.path.abspath(OUTPUT_FILE)}")
