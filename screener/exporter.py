from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from .config import log, OUTPUT_FILE, HEADER_LABELS, WIDTH_MAP, FMT_MAP

HEADER_BG = "1F3864"
NSE_BG = "EBF5FB"
BSE_BG = "FEF9E7"
G_FILL = PatternFill("solid", fgColor="C6EFCE")
R_FILL = PatternFill("solid", fgColor="FFC7CE")
Y_FILL = PatternFill("solid", fgColor="FFEB9C")
THIN = Border(
    left=Side(style="thin", color="D3D3D3"),
    right=Side(style="thin", color="D3D3D3"),
    bottom=Side(style="thin", color="D3D3D3"),
)

COLOUR_RULES = {
    **{
        c: [(lambda v: v > 0, G_FILL, "276221"), (lambda v: v < 0, R_FILL, "9C0006")]
        for c in [
            "1d Rt %",
            "1w Rt %",
            "1m Rt %",
            "3m Rt %",
            "1y Rt %",
            "3y Rt %",
            "5y Rt %",
            "RS Score",
        ]
    },
    "F-Score": [
        (lambda v: v >= 7, G_FILL, "276221"),
        (lambda v: v <= 3, R_FILL, "9C0006"),
    ],
    "Sales Growth % (YoY)": [
        (lambda v: v >= 20, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "Profit Growth % (YoY)": [
        (lambda v: v >= 20, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "Trend": [
        (lambda v: v == "Stage 2", G_FILL, "276221"),
        (lambda v: v == "Death Cross", R_FILL, "9C0006"),
    ],
    "RSI": [
        (lambda v: 40 <= v <= 60, G_FILL, "276221"),
        (lambda v: v > 70, R_FILL, "9C0006"),
        (lambda v: v < 30, Y_FILL, "7D5A00"),
    ],
    "P/E": [
        (lambda v: 0 < v <= 20, G_FILL, "276221"),
        (lambda v: v > 50, R_FILL, "9C0006"),
    ],
    "ROE 1y %": [
        (lambda v: v >= 15, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "ROE 3y %": [
        (lambda v: v >= 15, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "ROCE %": [
        (lambda v: v >= 15, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "D/E": [(lambda v: v < 1, G_FILL, "276221"), (lambda v: v > 3, R_FILL, "9C0006")],
    "OPM %": [
        (lambda v: v > 20, G_FILL, "276221"),
        (lambda v: v < 0, R_FILL, "9C0006"),
    ],
    "Pledged %": [(lambda v: v > 25, R_FILL, "9C0006")],
}

LEFT_COLS = {"Ticker", "Name", "Sector", "Industry", "Trend"}


def apply_colour(cell, col, val):
    for cond, fill, fc in COLOUR_RULES.get(col, []):
        try:
            if cond(val):
                cell.fill = fill
                cell.font = Font(name="Arial", size=8, color=fc)
                return
        except:
            pass


def write_excel(rows: list[dict]):
    if not rows:
        log.warning("No data to write.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Screener"
    ws.freeze_panes = "G2"

    # Header
    hfill = PatternFill("solid", fgColor=HEADER_BG)
    hfont = Font(bold=True, color="FFFFFF", name="Arial", size=9)
    for ci, lbl in enumerate(HEADER_LABELS, 1):
        c = ws.cell(row=1, column=ci, value=lbl)
        c.fill = hfill
        c.font = hfont
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = THIN
        ws.column_dimensions[get_column_letter(ci)].width = WIDTH_MAP.get(lbl, 12)
    ws.row_dimensions[1].height = 44

    # Data
    for ri, row in enumerate(rows, 2):
        ticker = row.get("Ticker", "")
        exch = "NSE" if ticker and ticker.endswith(".NS") else "BSE"
        row_bg = PatternFill("solid", fgColor=NSE_BG if exch == "NSE" else BSE_BG)

        for ci, lbl in enumerate(HEADER_LABELS, 1):
            val = row.get(lbl)
            c = ws.cell(row=ri, column=ci, value=val)
            c.fill = row_bg
            c.font = Font(name="Arial", size=8)
            c.border = THIN
            c.alignment = Alignment(
                horizontal="left" if lbl in LEFT_COLS else "center", vertical="center"
            )
            fmt = FMT_MAP.get(lbl)
            if fmt and fmt != "@":
                c.number_format = fmt
            if val is not None:
                apply_colour(c, lbl, val)

    last_col = get_column_letter(len(HEADER_LABELS))
    ws.auto_filter.ref = f"A1:{last_col}1"

    wb.save(OUTPUT_FILE)
    log.info(
        f"\n✅  Saved → {OUTPUT_FILE}  ({len(rows)} rows × {len(HEADER_LABELS)} cols)"
    )
