"""Generate the summary workbook (one sheet per financial year) for a category.

Consumes the dict from summary.build_summary so the file matches the on-screen
table exactly. Styling mirrors the client's Asset_Update sample.
"""
import io

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Colours lifted from the client's sample workbook.
FILL_MONTH = PatternFill("solid", fgColor="FADAC6")
FILL_ACD = PatternFill("solid", fgColor="F09156")
FILL_MBTOTAL = PatternFill("solid", fgColor="C2E49C")
FILL_CATTOTAL = PatternFill("solid", fgColor="B44E10")
FILL_HEADER = PatternFill("solid", fgColor="FADAC6")

FMT_INT = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
FMT_DEC = '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)'
FMT_PCT = "0%"

THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _months_span():
    return 12


def build_workbook(summaries: list[dict]) -> bytes:
    """`summaries` = list of build_summary() dicts (one per FY) for one category."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for summ in summaries:
        _write_sheet(wb, summ)
    if not wb.worksheets:
        wb.create_sheet("Summary")
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _write_sheet(wb, summ):
    ws = wb.create_sheet(title=summ["fy"])
    keys = summ["month_keys"]
    n = len(keys)
    first_m = 7  # column G
    ytd_col = first_m + n  # column after the 12 months

    def col(i):
        return get_column_letter(i)

    # ---- top header rows ----
    ws.cell(row=2, column=1, value="CATEGORY").font = Font(bold=True, size=10)
    ws.cell(row=2, column=2, value="CATEGORY").font = Font(bold=True, size=10)
    ws.cell(row=2, column=3, value="BRAND").font = Font(bold=True, size=10)
    ws.cell(row=2, column=4, value="COMMERCIAL").font = Font(bold=True, size=10)
    c = ws.cell(row=2, column=first_m, value=summ["fy"].replace("-", "/"))
    c.font = Font(bold=True, size=10)
    ws.merge_cells(start_row=2, start_column=first_m, end_row=2, end_column=ytd_col - 1)
    ws.cell(row=2, column=ytd_col, value="YTD").font = Font(bold=True, size=10)

    ws.cell(row=3, column=5, value="Mont Avg Spend").font = Font(bold=True, size=9)
    ws.cell(row=3, column=6, value="Weekly Avg Spend").font = Font(bold=True, size=9)
    for i, mm in enumerate(summ["months"]):
        cell = ws.cell(row=3, column=first_m + i, value=mm["header"])
        cell.font = Font(bold=True, size=10)
        cell.fill = FILL_MONTH
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    row = 4

    def set_months(r, rowdata, fmt=FMT_INT, fill=None, bold=False, pct=False):
        for i, k in enumerate(keys):
            v = rowdata.get(k)
            cell = ws.cell(row=r, column=first_m + i)
            cell.value = v
            cell.number_format = FMT_PCT if pct else fmt
            cell.font = Font(bold=bold, size=10)
            if fill:
                cell.fill = fill
        yc = ws.cell(row=r, column=ytd_col, value=rowdata.get("ytd"))
        yc.number_format = FMT_PCT if pct else fmt
        yc.font = Font(bold=bold, size=10)
        if fill:
            yc.fill = fill

    for g in summ["groups"]:
        group_start = row
        for b in g["brands"]:
            brand_start = row
            # brand label (col C) + subcategory (col A) + category (col B)
            bc = ws.cell(row=row, column=3, value=b["brand"])
            bc.font = Font(bold=True, size=10)
            ws.cell(row=row, column=1, value=g.get("subcategory") or None)
            ws.cell(row=row, column=2, value=summ["category"])
            if b.get("mont_avg") is not None:
                mc = ws.cell(row=row, column=5, value=b["mont_avg"])
                mc.number_format = FMT_DEC
            if b.get("weekly_avg") is not None:
                wc = ws.cell(row=row, column=6, value=b["weekly_avg"])
                wc.number_format = FMT_DEC

            # commercial theme rows
            for th in b["themes"]:
                ws.cell(row=row, column=4, value=th["text"]).font = Font(size=10)
                set_months(row, th, fmt=FMT_INT)
                row += 1
            if not b["themes"]:
                row += 1  # keep at least the brand anchor row

            # Tag row
            ws.cell(row=row, column=4, value="Tag").font = Font(bold=True, size=10)
            set_months(row, b["tag"], fmt=FMT_INT)
            row += 1
            # Value Adds row
            ws.cell(row=row, column=4, value="Value Adds").font = Font(bold=True, size=10)
            set_months(row, b["value_adds"], fmt=FMT_INT)
            row += 1
            # Total Spends
            tc = ws.cell(row=row, column=4, value="Total Spends (000)")
            tc.font = Font(bold=True, size=10)
            set_months(row, b["total"], fmt=FMT_INT, bold=True)
            row += 1
            # ACD Com Only
            ac = ws.cell(row=row, column=4, value="ACD (Com Only)")
            ac.font = Font(bold=True, size=10)
            ac.fill = FILL_ACD
            set_months(row, b["acd_com"], fmt=FMT_INT, fill=FILL_ACD, bold=True)
            row += 1
            # ACD All Exp
            ac2 = ws.cell(row=row, column=4, value="ACD (All Exp)")
            ac2.font = Font(bold=True, size=10)
            ac2.fill = FILL_ACD
            set_months(row, b["acd_all"], fmt=FMT_INT, fill=FILL_ACD, bold=True)
            row += 1

            if brand_start < row - 1 and len(b["themes"]) > 1:
                ws.merge_cells(start_row=brand_start, start_column=3,
                               end_row=brand_start, end_column=3)

        # mother-brand rollup
        if g["show_total"]:
            tc = ws.cell(row=row, column=3, value=f"Total {g['mother_brand']}")
            tc.font = Font(bold=True, size=10)
            tc.fill = FILL_MBTOTAL
            if g["total"].get("mont_avg") is not None:
                mc = ws.cell(row=row, column=5, value=g["total"]["mont_avg"])
                mc.number_format = FMT_DEC
                mc.fill = FILL_MBTOTAL
            if g["total"].get("weekly_avg") is not None:
                wc = ws.cell(row=row, column=6, value=g["total"]["weekly_avg"])
                wc.number_format = FMT_DEC
                wc.fill = FILL_MBTOTAL
            set_months(row, g["total"], fmt=FMT_INT, fill=FILL_MBTOTAL, bold=True)
            row += 1
            tac = ws.cell(row=row, column=3, value=f"Total {g['mother_brand']} - ACD")
            tac.font = Font(bold=True, size=10)
            tac.fill = FILL_ACD
            set_months(row, g["total_acd"], fmt=FMT_INT, fill=FILL_ACD, bold=True)
            row += 1

    # ---- TOTAL CATEGORY SPEND + SOS ----
    row += 1
    tcell = ws.cell(row=row, column=3, value="TOTAL CATEGORY SPEND")
    tcell.font = Font(bold=True, size=10, color="FFFFFF")
    tcell.fill = FILL_CATTOTAL
    set_months(row, summ["category_total"], fmt=FMT_INT, fill=FILL_CATTOTAL, bold=True)
    for i in range(1, ytd_col + 1):
        ws.cell(row=row, column=i).fill = FILL_CATTOTAL
    row += 1
    for s in summ["sos"]:
        ws.cell(row=row, column=3, value=s["mother_brand"]).font = Font(size=10)
        ws.cell(row=row, column=4, value="SOS %").font = Font(bold=True, size=10)
        set_months(row, s, pct=True, fill=FILL_HEADER)
        row += 1

    # ---- column widths ----
    widths = {1: 14, 2: 14, 3: 22, 4: 66, 5: 12, 6: 12}
    for i in range(first_m, ytd_col + 1):
        widths[i] = 10
    for i, w in widths.items():
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"{col(first_m)}4"
