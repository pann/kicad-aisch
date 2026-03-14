#!/usr/bin/env python3
"""Convert a markdown file to PDF using fpdf.

Usage:
    python3 scripts/md_to_pdf.py <input.md> [output.pdf] [--title TITLE] [--subtitle SUBTITLE] [--date DATE] [--header HEADER] [--skip-before MARKER]

If output.pdf is omitted, writes to <input>.pdf alongside the input file.

Supports: headers, bullets, numbered lists, tables, horizontal rules,
code blocks, and ~~~diagram blocks with boxes/arrows.
"""

import argparse
import math
import re
from datetime import date
from fpdf import FPDF
from pathlib import Path


# ---------------------------------------------------------------------------
# PDF subclass
# ---------------------------------------------------------------------------

class MarkdownPDF(FPDF):
    def __init__(self, header_text="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._header_text = header_text

    def header(self):
        if self._header_text:
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 5, sanitize_latin1(self._header_text), align="R")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def sanitize_latin1(text: str) -> str:
    """Replace Unicode chars that don't fit in latin-1."""
    replacements = {
        "\u2014": "-", "\u2013": "-",       # em/en dash
        "\u2019": "'", "\u2018": "'",        # single quotes
        "\u201c": '"', "\u201d": '"',        # double quotes
        "\u2026": "...",                       # ellipsis
        "\u2022": "-",                         # bullet
        "\u00a0": " ",                         # non-breaking space
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def clean_md_inline(text: str) -> str:
    """Remove markdown inline formatting for plain text output."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def write_rich_text(pdf: FPDF, text: str, w: float = 0):
    """Write text with markdown cleaned, using multi_cell for wrapping."""
    clean = sanitize_latin1(clean_md_inline(text))
    if w <= 0:
        w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(w, 5, clean)


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3


def is_separator_line(line: str) -> bool:
    stripped = line.strip()
    return bool(re.match(r"^\|[\s\-:|]+\|$", stripped))


def parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def render_table(pdf: MarkdownPDF, table_lines: list[str]):
    """Render a markdown table with borders and word wrapping."""
    rows = []
    for line in table_lines:
        if is_separator_line(line):
            continue
        rows.append(parse_table_row(line))

    if not rows:
        return

    num_cols = max(len(row) for row in rows)
    for row in rows:
        while len(row) < num_cols:
            row.append("")

    for row in rows:
        for i in range(len(row)):
            row[i] = sanitize_latin1(clean_md_inline(row[i]))

    table_w = pdf.w - pdf.l_margin - pdf.r_margin
    font_size = 7
    pdf.set_font("Helvetica", "", font_size)

    max_widths = [0.0] * num_cols
    for row in rows:
        for i, cell in enumerate(row):
            w = pdf.get_string_width(cell) + 3
            max_widths[i] = max(max_widths[i], w)

    total_natural = sum(max_widths)
    min_col_w = 8  # minimum column width in mm
    if total_natural > table_w:
        col_widths = [max(w * table_w / total_natural, min_col_w) for w in max_widths]
    else:
        col_widths = [max(w, min_col_w) for w in max_widths]

    line_h = font_size * 0.5

    def render_row(row: list[str], bold: bool = False):
        pdf.set_font("Helvetica", "B" if bold else "", font_size)
        max_lines = 1
        for i, cell in enumerate(row):
            cw = col_widths[i] - 2
            if cw <= 0:
                cw = 10
            text_w = pdf.get_string_width(cell)
            n_lines = max(1, int(text_w / cw) + 1)
            max_lines = max(max_lines, n_lines)

        row_h = max_lines * line_h + 2
        if pdf.get_y() + row_h > pdf.h - pdf.b_margin:
            pdf.add_page()

        y_start = pdf.get_y()
        x_start = pdf.l_margin

        for i, cell in enumerate(row):
            x = x_start + sum(col_widths[:i])
            pdf.rect(x, y_start, col_widths[i], row_h)
            pdf.set_xy(x + 1, y_start + 1)
            pdf.set_font("Helvetica", "B" if bold else "", font_size)
            pdf.multi_cell(col_widths[i] - 2, line_h, cell)

        pdf.set_y(y_start + row_h)

    if rows:
        render_row(rows[0], bold=True)
        for row in rows[1:]:
            render_row(row, bold=False)

    pdf.ln(3)


# ---------------------------------------------------------------------------
# Diagram rendering  (~~~diagram blocks)
# ---------------------------------------------------------------------------
#
# DSL format (one command per line, # comments ignored):
#
#   box <id> "<label>" <x%> <y%> [<w%> <h%>] [style=dashed]
#   arrow <from_id> <to_id> [<from_side> <to_side>] [label="text"]
#   label "<text>" <x%> <y%> [size=N] [bold] [italic] [align=left|center|right]
#   vline <x%> <y1%> <y2%> [style=dashed] [label="text"]
#   hline <y%> <x1%> <x2%> [style=dashed]
#   group "<title>" <x%> <y%> <w%> <h%> [fill=R,G,B]
#
# Coordinates are percentages of the diagram area (0-100).
# Sides: top, bottom, left, right  (default: auto based on relative position)
# ---------------------------------------------------------------------------

def render_diagram(pdf: MarkdownPDF, diagram_lines: list[str]):
    """Parse and render a ~~~diagram block."""
    # Diagram area
    margin_x = pdf.l_margin
    area_w = pdf.w - pdf.l_margin - pdf.r_margin
    area_h = 140  # mm, fixed height — adjust if needed

    # Check page break
    if pdf.get_y() + area_h + 5 > pdf.h - pdf.b_margin:
        pdf.add_page()

    origin_x = margin_x
    origin_y = pdf.get_y()

    def pct_to_mm(xp, yp):
        return origin_x + xp * area_w / 100, origin_y + yp * area_h / 100

    boxes = {}   # id -> {x, y, w, h, label, style}  all in mm
    groups = []
    labels_list = []
    arrows = []
    vlines = []
    hlines = []

    # Parse lines
    for raw_line in diagram_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # --- group ---
        m = re.match(
            r'group\s+"([^"]+)"\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
            r'(?:\s+fill=([\d,]+))?', line)
        if m:
            gx, gy = pct_to_mm(float(m.group(2)), float(m.group(3)))
            gw = float(m.group(4)) * area_w / 100
            gh = float(m.group(5)) * area_h / 100
            fill_str = m.group(6)
            fill = tuple(int(c) for c in fill_str.split(",")) if fill_str else (240, 245, 255)
            groups.append({"label": m.group(1), "x": gx, "y": gy, "w": gw, "h": gh, "fill": fill})
            continue

        # --- box ---
        m = re.match(
            r'box\s+(\S+)\s+"([^"]+)"\s+([\d.]+)\s+([\d.]+)'
            r'(?:\s+([\d.]+)\s+([\d.]+))?'
            r'(?:\s+style=(\w+))?', line)
        if m:
            bid = m.group(1)
            label = m.group(2)
            cx, cy = pct_to_mm(float(m.group(3)), float(m.group(4)))
            bw = float(m.group(5)) * area_w / 100 if m.group(5) else None
            bh = float(m.group(6)) * area_h / 100 if m.group(6) else None
            style = m.group(7) or "solid"

            # Auto-size if not specified
            pdf.set_font("Helvetica", "", 7)
            text_w = pdf.get_string_width(sanitize_latin1(label))
            if bw is None:
                bw = max(text_w + 6, 20)
            if bh is None:
                bh = 8

            # x,y is center of box
            boxes[bid] = {
                "x": cx - bw / 2, "y": cy - bh / 2,
                "w": bw, "h": bh,
                "cx": cx, "cy": cy,
                "label": label, "style": style
            }
            continue

        # --- arrow ---
        m = re.match(
            r'arrow\s+(\S+)\s+(\S+)'
            r'(?:\s+(top|bottom|left|right)\s+(top|bottom|left|right))?'
            r'(?:\s+label="([^"]*)")?', line)
        if m:
            arrows.append({
                "from": m.group(1), "to": m.group(2),
                "from_side": m.group(3), "to_side": m.group(4),
                "label": m.group(5) or ""
            })
            continue

        # --- label ---
        m = re.match(
            r'label\s+"([^"]+)"\s+([\d.]+)\s+([\d.]+)'
            r'((?:\s+\w+=?\S*)*)', line)
        if m:
            lx, ly = pct_to_mm(float(m.group(2)), float(m.group(3)))
            opts = m.group(4)
            size = 8
            bold = False
            italic = False
            align = "left"
            sm = re.search(r'size=(\d+)', opts)
            if sm:
                size = int(sm.group(1))
            if "bold" in opts:
                bold = True
            if "italic" in opts:
                italic = True
            sm = re.search(r'align=(\w+)', opts)
            if sm:
                align = sm.group(1)
            labels_list.append({"text": m.group(1), "x": lx, "y": ly,
                                "size": size, "bold": bold, "italic": italic, "align": align})
            continue

        # --- vline ---
        m = re.match(
            r'vline\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
            r'(?:\s+style=(\w+))?'
            r'(?:\s+label="([^"]*)")?', line)
        if m:
            vx, vy1 = pct_to_mm(float(m.group(1)), float(m.group(2)))
            _, vy2 = pct_to_mm(float(m.group(1)), float(m.group(3)))
            vlines.append({"x": vx, "y1": vy1, "y2": vy2,
                           "style": m.group(4) or "dashed",
                           "label": m.group(5) or ""})
            continue

        # --- hline ---
        m = re.match(
            r'hline\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
            r'(?:\s+style=(\w+))?', line)
        if m:
            _, hy = pct_to_mm(0, float(m.group(1)))
            hx1, _ = pct_to_mm(float(m.group(2)), 0)
            hx2, _ = pct_to_mm(float(m.group(3)), 0)
            hlines.append({"y": hy, "x1": hx1, "x2": hx2,
                           "style": m.group(4) or "dashed"})
            continue

    # --- Draw groups (background) ---
    for g in groups:
        r, gr, b = g["fill"]
        pdf.set_fill_color(r, gr, b)
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(g["x"], g["y"], g["w"], g["h"], style="DF")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.set_xy(g["x"] + 2, g["y"] + 1)
        pdf.cell(g["w"] - 4, 4, sanitize_latin1(g["label"]))
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)

    # --- Draw vlines ---
    for vl in vlines:
        if vl["style"] == "dashed":
            _draw_dashed_line(pdf, vl["x"], vl["y1"], vl["x"], vl["y2"])
        else:
            pdf.line(vl["x"], vl["y1"], vl["x"], vl["y2"])
        if vl["label"]:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 100, 100)
            lw = pdf.get_string_width(sanitize_latin1(vl["label"]))
            pdf.set_xy(vl["x"] - lw / 2, vl["y1"] - 4)
            pdf.cell(lw, 3, sanitize_latin1(vl["label"]))
            pdf.set_text_color(0, 0, 0)

    # --- Draw hlines ---
    for hl in hlines:
        if hl["style"] == "dashed":
            _draw_dashed_line(pdf, hl["x1"], hl["y"], hl["x2"], hl["y"])
        else:
            pdf.line(hl["x1"], hl["y"], hl["x2"], hl["y"])

    # --- Draw boxes ---
    for bid, b in boxes.items():
        pdf.set_draw_color(0, 0, 0)
        if b["style"] == "dashed":
            _draw_dashed_rect(pdf, b["x"], b["y"], b["w"], b["h"])
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(b["x"], b["y"], b["w"], b["h"], style="DF")
        pdf.set_font("Helvetica", "", 7)
        text = sanitize_latin1(b["label"])
        tw = pdf.get_string_width(text)
        # Center text in box
        tx = b["cx"] - tw / 2
        ty = b["cy"] - 1.5
        pdf.set_xy(tx, ty)
        pdf.cell(tw, 3, text)

    # --- Draw labels ---
    for lb in labels_list:
        style_str = ""
        if lb["bold"]:
            style_str += "B"
        if lb["italic"]:
            style_str += "I"
        pdf.set_font("Helvetica", style_str, lb["size"])
        text = sanitize_latin1(lb["text"])
        tw = pdf.get_string_width(text)
        if lb["align"] == "center":
            pdf.set_xy(lb["x"] - tw / 2, lb["y"])
        elif lb["align"] == "right":
            pdf.set_xy(lb["x"] - tw, lb["y"])
        else:
            pdf.set_xy(lb["x"], lb["y"])
        pdf.cell(tw, 3, text)

    # --- Draw arrows ---
    for a in arrows:
        if a["from"] not in boxes or a["to"] not in boxes:
            continue
        fb = boxes[a["from"]]
        tb = boxes[a["to"]]

        # Determine connection points
        from_side = a["from_side"]
        to_side = a["to_side"]

        if not from_side or not to_side:
            from_side, to_side = _auto_sides(fb, tb)

        x1, y1 = _side_point(fb, from_side)
        x2, y2 = _side_point(tb, to_side)

        # Draw line
        pdf.set_draw_color(0, 0, 0)
        pdf.line(x1, y1, x2, y2)

        # Draw arrowhead
        _draw_arrowhead(pdf, x1, y1, x2, y2)

        # Draw label at midpoint
        if a["label"]:
            pdf.set_font("Helvetica", "", 6)
            text = sanitize_latin1(a["label"])
            tw = pdf.get_string_width(text)
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            pdf.set_fill_color(255, 255, 255)
            pdf.set_xy(mx - tw / 2 - 1, my - 2)
            pdf.cell(tw + 2, 4, text, fill=True)

    pdf.set_y(origin_y + area_h + 3)


def _side_point(box, side):
    """Get the connection point on a side of a box."""
    if side == "top":
        return box["cx"], box["y"]
    elif side == "bottom":
        return box["cx"], box["y"] + box["h"]
    elif side == "left":
        return box["x"], box["cy"]
    elif side == "right":
        return box["x"] + box["w"], box["cy"]
    return box["cx"], box["cy"]


def _auto_sides(fb, tb):
    """Determine best sides to connect two boxes."""
    dx = tb["cx"] - fb["cx"]
    dy = tb["cy"] - fb["cy"]
    if abs(dy) > abs(dx):
        # Mostly vertical
        if dy > 0:
            return "bottom", "top"
        else:
            return "top", "bottom"
    else:
        # Mostly horizontal
        if dx > 0:
            return "right", "left"
        else:
            return "left", "right"


def _draw_arrowhead(pdf, x1, y1, x2, y2, size=1.5):
    """Draw a filled triangular arrowhead at (x2, y2)."""
    angle = math.atan2(y2 - y1, x2 - x1)
    a1 = angle + math.pi * 0.85
    a2 = angle - math.pi * 0.85
    ax1 = x2 + size * math.cos(a1)
    ay1 = y2 + size * math.sin(a1)
    ax2 = x2 + size * math.cos(a2)
    ay2 = y2 + size * math.sin(a2)
    pdf.set_fill_color(0, 0, 0)
    # Draw filled triangle using polygon (lines + fill)
    pdf.line(x2, y2, ax1, ay1)
    pdf.line(x2, y2, ax2, ay2)
    pdf.line(ax1, ay1, ax2, ay2)


def _draw_dashed_line(pdf, x1, y1, x2, y2, dash=2, gap=1.5):
    """Draw a dashed line."""
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    while pos < length:
        sx = x1 + ux * pos
        sy = y1 + uy * pos
        end = min(pos + dash, length)
        ex = x1 + ux * end
        ey = y1 + uy * end
        pdf.line(sx, sy, ex, ey)
        pos = end + gap


def _draw_dashed_rect(pdf, x, y, w, h):
    """Draw a dashed rectangle."""
    _draw_dashed_line(pdf, x, y, x + w, y)
    _draw_dashed_line(pdf, x + w, y, x + w, y + h)
    _draw_dashed_line(pdf, x + w, y + h, x, y + h)
    _draw_dashed_line(pdf, x, y + h, x, y)


# ---------------------------------------------------------------------------
# Code block rendering
# ---------------------------------------------------------------------------

def render_code_block(pdf: MarkdownPDF, code_lines: list[str]):
    """Render a code block with monospace font in a gray box."""
    pdf.set_font("Courier", "", 7)
    line_h = 3.5
    padding = 3

    # Calculate block height
    block_h = len(code_lines) * line_h + 2 * padding

    if pdf.get_y() + block_h > pdf.h - pdf.b_margin:
        pdf.add_page()

    x = pdf.l_margin
    y = pdf.get_y()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # Draw background
    pdf.set_fill_color(245, 245, 245)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(x, y, w, block_h, style="DF")

    # Draw text
    pdf.set_text_color(30, 30, 30)
    for i, code_line in enumerate(code_lines):
        pdf.set_xy(x + padding, y + padding + i * line_h)
        text = sanitize_latin1(code_line.rstrip())
        pdf.cell(w - 2 * padding, line_h, text)

    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_y(y + block_h + 3)


# ---------------------------------------------------------------------------
# Main markdown renderer
# ---------------------------------------------------------------------------

def render_md_to_pdf(md_text: str, pdf: MarkdownPDF):
    """Render markdown text into the PDF."""
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pdf.ln(3)
            i += 1
            continue

        # --- Diagram block: ~~~diagram ... ~~~ ---
        if stripped.startswith("~~~diagram"):
            i += 1
            diagram_lines = []
            while i < len(lines) and not lines[i].strip().startswith("~~~"):
                diagram_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing ~~~
            render_diagram(pdf, diagram_lines)
            continue

        # --- Code block: ``` ... ``` ---
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            render_code_block(pdf, code_lines)
            continue

        # --- Table ---
        if is_table_line(stripped):
            table_lines = []
            while i < len(lines) and is_table_line(lines[i].strip()):
                table_lines.append(lines[i])
                i += 1
            render_table(pdf, table_lines)
            continue

        # --- Horizontal rule ---
        if stripped.startswith("---"):
            pdf.ln(3)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(5)
            i += 1
            continue

        # --- Headers ---
        if stripped.startswith("#"):
            level = len(stripped.split()[0])
            text = stripped.lstrip("#").strip()
            sizes = {1: 18, 2: 15, 3: 13, 4: 11}
            size = sizes.get(level, 10)
            pdf.set_font("Helvetica", "B", size)
            pdf.multi_cell(0, size * 0.6, sanitize_latin1(clean_md_inline(text)))
            pdf.ln(2)
            i += 1
            continue

        # --- Bullet points ---
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            indent = (len(line) - len(line.lstrip())) // 2
            pdf.set_font("Helvetica", "", 10)
            x_offset = pdf.l_margin + indent * 6
            pdf.set_x(x_offset)
            pdf.cell(4, 5, "-")
            pdf.set_x(x_offset + 5)
            write_rich_text(pdf, text, w=pdf.w - pdf.r_margin - x_offset - 5)
            pdf.ln(1)
            i += 1
            continue

        # --- Numbered list items ---
        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            num, text = m.group(1), m.group(2)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(8, 5, f"{num}.")
            write_rich_text(pdf, text, w=pdf.w - pdf.r_margin - pdf.get_x())
            pdf.ln(1)
            i += 1
            continue

        # --- Regular paragraph ---
        pdf.set_font("Helvetica", "", 10)
        write_rich_text(pdf, stripped, w=pdf.w - pdf.l_margin - pdf.r_margin)
        pdf.ln(1)
        i += 1


# ---------------------------------------------------------------------------
# PDF generation entry point
# ---------------------------------------------------------------------------

def generate_pdf(src: Path, out: Path, title: str = "", subtitle: str = "",
                 date_str: str = "", header: str = "", skip_before: str = ""):
    """Generate a PDF from a markdown file."""
    md_text = src.read_text()

    if skip_before:
        idx = md_text.find(skip_before)
        if idx >= 0:
            md_text = md_text[idx:]

    pdf = MarkdownPDF(header_text=header)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    if title:
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 12, sanitize_latin1(title), align="C")
        pdf.ln(8)
    if subtitle:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 6, sanitize_latin1(subtitle), align="C")
        pdf.ln(4)
    if date_str:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, date_str, align="C")
        pdf.ln(12)
    elif title:
        pdf.ln(8)

    render_md_to_pdf(md_text, pdf)
    pdf.output(str(out))
    print(f"Generated: {out}")


def main():
    parser = argparse.ArgumentParser(description="Convert markdown to PDF")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("output", nargs="?", help="Output PDF file (default: same name as input)")
    parser.add_argument("--title", default="", help="Document title")
    parser.add_argument("--subtitle", default="", help="Document subtitle")
    parser.add_argument("--date", default=str(date.today()), help="Document date")
    parser.add_argument("--header", default="", help="Page header text (top-right)")
    parser.add_argument("--skip-before", default="", help="Skip content before this marker text")
    args = parser.parse_args()

    src = Path(args.input)
    out = Path(args.output) if args.output else src.with_suffix(".pdf")

    generate_pdf(src, out, title=args.title, subtitle=args.subtitle,
                 date_str=args.date, header=args.header, skip_before=args.skip_before)


if __name__ == "__main__":
    main()
