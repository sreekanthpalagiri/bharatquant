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
from .config import log, OUTPUT_FILE, HEADER_LABELS, WIDTH_MAP, FMT_MAP, TODAY, COLOR_RULES, LEGEND

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

        # Helper to evaluate config string conditions
        def check_cond(val, rule_str):
            if val is None: return False
            if "or" in rule_str:
                return any(check_cond(val, r.strip()) for r in rule_str.split("or"))
            if "-" in rule_str and not rule_str.startswith("-"):
                try:
                    p = rule_str.split("-")
                    return float(p[0]) <= float(val) <= float(p[1])
                except: return False
            op = ''.join([c for c in rule_str if c in '<=>'])
            try:
                num = float(rule_str.replace(op, "").strip())
                if op == ">": return float(val) > num
                if op == ">=": return float(val) >= num
                if op == "<": return float(val) < num
                if op == "<=": return float(val) <= num
            except: pass
            return False

        # Apply Formatting
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            row_dict = dict(zip(df.columns, row))
            
            # Determine Row Color
            row_fill = None
            is_red = False
            green_points = 0
            
            # 1. Check Red Flags (Immediate Red)
            for col, rule in COLOR_RULES.get("red", {}).items():
                if col == "Growth %":
                    if check_cond(row_dict.get("Sales Growth % (YoY)"), rule) or check_cond(row_dict.get("Profit Growth % (YoY)"), rule):
                        is_red = True
                elif col in row_dict and check_cond(row_dict.get(col), rule):
                    is_red = True
            
            if is_red:
                row_fill = RED_FILL
            else:
                # 2. Check Green Flags
                for col, rule in COLOR_RULES.get("green", {}).items():
                    if col == "Growth %":
                        if check_cond(row_dict.get("Sales Growth % (YoY)"), rule) and check_cond(row_dict.get("Profit Growth % (YoY)"), rule):
                            green_points += 1
                    elif col in row_dict and check_cond(row_dict.get(col), rule):
                        green_points += 1
                
                if green_points >= 4:  # If at least 4 bullish indicators are met
                    row_fill = GREEN_FILL
                else:
                    # 3. Check Yellow Flags
                    for col, rule in COLOR_RULES.get("yellow", {}).items():
                        if col in row_dict and check_cond(row_dict.get(col), rule):
                            row_fill = YELLOW_FILL

            # Apply formats to all cells in the row
            for col_idx, (lbl, val) in enumerate(zip(df.columns, row), start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                if lbl in FMT_MAP:
                    cell.number_format = FMT_MAP[lbl]
                if row_fill:
                    cell.fill = row_fill

        # 3. Final UI Adjustments (Header Freeze, Column Widths)
        ws.freeze_panes = "A2"
        for ci, lbl in enumerate(df.columns, start=1):
            width = WIDTH_MAP.get(lbl, 12)
            ws.column_dimensions[get_column_letter(ci)].width = width

        # 4. Add Legend Sheet
        df_legend = pd.DataFrame(LEGEND)
        df_legend.to_excel(writer, index=False, sheet_name="Legend")
        ws_legend = writer.sheets["Legend"]
        ws_legend.column_dimensions["A"].width = 25
        ws_legend.column_dimensions["B"].width = 45
        ws_legend.column_dimensions["C"].width = 45
        ws_legend.column_dimensions["D"].width = 30

    log.info(f"Report Successfully Generated! ✨ → {os.path.abspath(OUTPUT_FILE)}")
