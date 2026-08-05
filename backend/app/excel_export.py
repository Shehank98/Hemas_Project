"""Generate the summary workbook for a category.

Layout matches the client's Asset_Update template:

  CATEGORY(sub) | CATEGORY | BRAND | COMMERCIAL | 2022/23 (Mont/Weekly Avg) |
  April … March | YTD

The full financial year (April→March) is always shown — no breaks. Each category
is themed in a different colour (brown, green, blue, …) so its export sheets are
visually distinct.
"""
import io

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Each palette: head (dark header), month (light month row), acd, mbtotal,
# total (pale Total-Spends row), cattotal (dark), sos (very light).
PALETTES = [
    {"name": "brown",  "head": "B44E10", "month": "FADAC6", "acd": "F09156",
     "mbtotal": "E8C4A0", "total": "F7E6D6", "cattotal": "7A3A0E", "sos": "FBEEE2"},
    {"name": "green",  "head": "2E7D32", "month": "DCEDC8", "acd": "8BC34A",
     "mbtotal": "C5E1A5", "total": "EAF4DD", "cattotal": "1B5E20", "sos": "F1F8E9"},
    {"name": "blue",   "head": "1F6FB2", "month": "D6E9F8", "acd": "6FA8DC",
     "mbtotal": "B6D4EF", "total": "E7F1FB", "cattotal": "154C7C", "sos": "EFF6FC"},
    {"name": "purple", "head": "6A3D9A", "month": "E5D8F0", "acd": "A97FC7",
     "mbtotal": "D2BDE6", "total": "F0E9F7", "cattotal": "48286B", "sos": "F5EFFA"},
    {"name": "teal",   "head": "0E8074", "month": "D2ECE9", "acd": "5FC9BC",
     "mbtotal": "A7DED7", "total": "E4F5F2", "cattotal": "0A544B", "sos": "EDF8F6"},
    {"name": "red",    "head": "B02418", "month": "F7D6D3", "acd": "E08A80",
     "mbtotal": "EFB6AF", "total": "FBE7E4", "cattotal": "7A1810", "sos": "FCEEEC"},
    {"name": "orange", "head": "D9701E", "month": "FCE1CC", "acd": "F0A860",
     "mbtotal": "F6C89B", "total": "FDF0E4", "cattotal": "8F4611", "sos": "FDF4EC"},
    {"name": "slate",  "head": "455A64", "month": "DDE3E7", "acd": "90A4AE",
     "mbtotal": "C0CBD1", "total": "EBEFF1", "cattotal": "273238", "sos": "F2F5F6"},
]

FMT_INT = '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)'
FMT_DEC = '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)'
FMT_PCT = "0%"

THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center")


def palette_for(color_index: int) -> dict:
    return PALETTES[color_index % len(PALETTES)]


def build_workbook(summaries: list[dict], color_index: int = 0) -> bytes:
    pal = palette_for(color_index)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for summ in summaries:
        _write_sheet(wb, summ, pal)
    if not wb.worksheets:
        wb.create_sheet("Summary")
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _fill(hexc):
    return PatternFill("solid", fgColor=hexc)


def _write_sheet(wb, summ, pal):
    ws = wb.create_sheet(title=summ["fy"][:31])
    keys = summ["month_keys"]
    n = len(keys)
    FIRST_M = 7             # column G
    ytd_col = FIRST_M + n   # column S when 12 months

    f_head = _fill(pal["head"])
    f_month = _fill(pal["month"])
    f_acd = _fill(pal["acd"])
    f_mbt = _fill(pal["mbtotal"])
    f_total = _fill(pal["total"])
    f_cat = _fill(pal["cattotal"])
    f_sos = _fill(pal["sos"])
    head_font = Font(bold=True, size=10, color="FFFFFF")
    dark_font = Font(bold=True, size=10, color="FFFFFF")

    # ---------- header (rows 2-3) ----------
    def H(r, c, v):
        cell = ws.cell(row=r, column=c, value=v)
        cell.font = head_font
        cell.fill = f_head
        cell.alignment = CENTER
        cell.border = BORDER
        return cell

    H(2, 1, "CATEGORY"); ws.merge_cells("A2:A3")
    H(2, 2, "CATEGORY"); ws.merge_cells("B2:B3")
    H(2, 3, "BRAND"); ws.merge_cells("C2:C3")
    H(2, 4, "COMMERCIAL"); ws.merge_cells("D2:D3")
    H(2, 5, "2022/23")
    ws.merge_cells(start_row=2, start_column=5, end_row=2, end_column=6)
    H(2, FIRST_M, summ["fy"].replace("-", "/"))
    ws.merge_cells(start_row=2, start_column=FIRST_M, end_row=2, end_column=ytd_col - 1)
    H(2, ytd_col, "YTD"); ws.merge_cells(start_row=2, start_column=ytd_col,
                                         end_row=3, end_column=ytd_col)
    e = ws.cell(row=3, column=5, value="Mont Avg Spend"); e.font = head_font
    e.fill = f_head; e.alignment = CENTER; e.border = BORDER
    f = ws.cell(row=3, column=6, value="Weekly Avg Spend"); f.font = head_font
    f.fill = f_head; f.alignment = CENTER; f.border = BORDER
    for i, mm in enumerate(summ["months"]):
        cell = ws.cell(row=3, column=FIRST_M + i, value=mm["header"])
        cell.font = Font(bold=True, size=10)
        cell.fill = f_month
        cell.alignment = CENTER
        cell.border = BORDER

    row = 4
    data_start = row

    def months_row(r, data, *, fmt=FMT_INT, fill=None, bold=False, blank_zero=False,
                   pct=False, show_ytd=True):
        for i, k in enumerate(keys):
            v = data.get(k)
            if blank_zero and (v == 0 or v is None):
                v = None
            cc = ws.cell(row=r, column=FIRST_M + i, value=v)
            cc.number_format = FMT_PCT if pct else fmt
            cc.font = Font(bold=bold, size=10)
            if fill:
                cc.fill = fill
            cc.border = BORDER
        yv = data.get("ytd") if show_ytd else None
        if blank_zero and (yv == 0 or yv is None):
            yv = None
        yc = ws.cell(row=r, column=ytd_col, value=yv)
        yc.number_format = FMT_PCT if pct else fmt
        yc.font = Font(bold=bold, size=10)
        if fill:
            yc.fill = fill
        yc.border = BORDER

    def label(r, col, text, *, bold=False, fill=None):
        cell = ws.cell(row=r, column=col, value=text)
        cell.font = Font(bold=bold, size=10)
        cell.alignment = LEFT
        if fill:
            cell.fill = fill
        cell.border = BORDER

    def borders(r, upto):
        for c in range(1, upto):
            ws.cell(row=r, column=c).border = BORDER

    for g in summ["groups"]:
        group_start = row
        for b in g["brands"]:
            brand_start = row
            themes = b["themes"] if b["themes"] else [{"text": ""}]
            for i, t in enumerate(themes):
                label(row, 4, t.get("text", ""))
                borders(row, 4)
                if i == 0:
                    if b.get("mont_avg") is not None:
                        mc = ws.cell(row=row, column=5, value=b["mont_avg"])
                        mc.number_format = FMT_DEC
                    if b.get("weekly_avg") is not None:
                        wc = ws.cell(row=row, column=6, value=b["weekly_avg"])
                        wc.number_format = FMT_DEC
                months_row(row, t, blank_zero=True)
                row += 1
            label(row, 4, "Tag", bold=False); borders(row, 4)
            months_row(row, b["tag"], blank_zero=True); row += 1
            label(row, 4, "Value Adds", bold=False); borders(row, 4)
            months_row(row, b["value_adds"], blank_zero=True); row += 1
            label(row, 4, "Total Spends (000)", bold=True, fill=f_total); borders(row, 4)
            months_row(row, b["total"], bold=True, fill=f_total); row += 1
            label(row, 4, "ACD (Com Only)", bold=True, fill=f_acd); borders(row, 4)
            months_row(row, b["acd_com"], bold=True, fill=f_acd, show_ytd=False); row += 1
            label(row, 4, "ACD (All Exp)", bold=True, fill=f_acd); borders(row, 4)
            months_row(row, b["acd_all"], bold=True, fill=f_acd, show_ytd=False); row += 1
            # brand label merged down its block (column C)
            label(brand_start, 3, b["brand"], bold=True)
            if row - 1 > brand_start:
                ws.merge_cells(start_row=brand_start, start_column=3,
                               end_row=row - 1, end_column=3)
            ws.cell(row=brand_start, column=3).alignment = CENTER

        if g["show_total"]:
            label(row, 3, f"Total {g['mother_brand']}", bold=True, fill=f_mbt)
            ws.cell(row=row, column=3).alignment = CENTER
            for c in (1, 2, 4):
                ws.cell(row=row, column=c).fill = f_mbt
                ws.cell(row=row, column=c).border = BORDER
            if g["total"].get("mont_avg") is not None:
                mc = ws.cell(row=row, column=5, value=g["total"]["mont_avg"])
                mc.number_format = FMT_DEC; mc.fill = f_mbt
            if g["total"].get("weekly_avg") is not None:
                wc = ws.cell(row=row, column=6, value=g["total"]["weekly_avg"])
                wc.number_format = FMT_DEC; wc.fill = f_mbt
            months_row(row, g["total"], bold=True, fill=f_mbt); row += 1
            label(row, 3, f"Total {g['mother_brand']} - ACD", bold=True, fill=f_acd)
            for c in (1, 2, 4, 5, 6):
                ws.cell(row=row, column=c).fill = f_acd
                ws.cell(row=row, column=c).border = BORDER
            months_row(row, g["total_acd"], bold=True, fill=f_acd, show_ytd=False); row += 1

        # sub-category (column A) merged for the group
        if g.get("subcategory"):
            label(group_start, 1, g["subcategory"], bold=True)
            if row - 1 > group_start:
                ws.merge_cells(start_row=group_start, start_column=1,
                               end_row=row - 1, end_column=1)
            ws.cell(row=group_start, column=1).alignment = CENTER

    data_end = row - 1
    # category (column B) merged across the whole block
    if data_end >= data_start:
        label(data_start, 2, summ["category"], bold=True)
        ws.merge_cells(start_row=data_start, start_column=2, end_row=data_end, end_column=2)
        ws.cell(row=data_start, column=2).alignment = CENTER

    # ---------- TOTAL CATEGORY SPEND ----------
    tc = ws.cell(row=row, column=1, value="TOTAL CATEGORY SPEND")
    tc.font = dark_font; tc.alignment = CENTER
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    for c in range(1, ytd_col + 1):
        ws.cell(row=row, column=c).fill = f_cat
        ws.cell(row=row, column=c).border = BORDER
    months_row(row, summ["category_total"], bold=True, fill=f_cat)
    for i in range(n):
        ws.cell(row=row, column=FIRST_M + i).font = dark_font
    ws.cell(row=row, column=ytd_col).font = dark_font
    row += 1

    # ---------- SOS % ----------
    sos_start = row
    for s in summ["sos"]:
        label(row, 3, s["mother_brand"], bold=True, fill=f_sos)
        for c in (1, 2):
            ws.cell(row=row, column=c).fill = f_sos
            ws.cell(row=row, column=c).border = BORDER
        ws.cell(row=row, column=4).fill = f_sos
        ws.cell(row=row, column=4).border = BORDER
        months_row(row, s, pct=True, fill=f_sos)
        row += 1
    if row - 1 >= sos_start:
        lc = ws.cell(row=sos_start, column=4, value="SOS %")
        lc.font = Font(bold=True, size=10); lc.alignment = CENTER
        ws.merge_cells(start_row=sos_start, start_column=4, end_row=row - 1, end_column=4)
    total_pct = {k: (1.0 if any(s.get(k) for s in summ["sos"]) else None) for k in keys}
    total_pct["ytd"] = 1.0 if summ["sos"] else None
    for c in range(1, 5):
        ws.cell(row=row, column=c).fill = f_sos
        ws.cell(row=row, column=c).border = BORDER
    months_row(row, total_pct, pct=True, fill=f_sos)
    row += 1

    # ---------- widths / freeze ----------
    widths = {1: 14, 2: 14, 3: 22, 4: 60, 5: 12, 6: 12}
    for i in range(FIRST_M, ytd_col + 1):
        widths[i] = 10
    for i, w in widths.items():
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = f"{get_column_letter(FIRST_M)}4"
