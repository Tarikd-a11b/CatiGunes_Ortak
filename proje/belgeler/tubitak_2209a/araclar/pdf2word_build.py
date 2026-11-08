import fitz, re, sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Kullanim: python pdf2word_build.py <kaynak.pdf> <cikti.docx>
# TYBS'nin urettigi 2209-A PDF'ine gore ayarli (tablo bolgeleri TABLES'ta sayfa/y ile sabit).
import os
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calisma")
os.makedirs(S, exist_ok=True)
OUT = sys.argv[2]
pdf = fitz.open(sys.argv[1])
FONT = "Arial"

# ---------- collect lines ----------
def page_lines(pg):
    res = []
    for b in pg.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            spans = [(sp["text"], "Bold" in sp["font"]) for sp in l["spans"]]
            txt = "".join(t for t, _ in spans)
            if not txt.strip():
                continue
            res.append(dict(x=l["bbox"][0], y=l["bbox"][1], size=round(l["spans"][0]["size"]),
                            text=txt, spans=spans))
    res.sort(key=lambda d: (round(d["y"]), d["x"]))
    return res

def page_images(pno):
    pg = pdf[pno]
    out = []
    for i, info in enumerate(pg.get_image_info(xrefs=True)):
        xref = info["xref"]
        pix = fitz.Pixmap(pdf, xref)
        if pix.n - pix.alpha >= 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        path = S + rf"\img_p{pno+1}_{i}.png"
        pix.save(path)
        bb = info["bbox"]
        out.append(dict(y=bb[1], path=path, w=bb[2] - bb[0]))
    return out

def box_segments(pg):
    segs = []
    for dr in pg.get_drawings():
        r = dr["rect"]
        if abs(r.x0 - 36) < 1.5 and r.width < 2 and r.height > 3:
            segs.append((r.y0, r.y1))
    return sorted(set(segs))

# table regions: (page index, y0, y1, kind)
TABLES = [(5, 505, 800, "plan"), (6, 30, 660, "plan"), (6, 685, 800, "risk"), (7, 30, 280, "risk"),
          (7, 308, 440, "fac"), (7, 476, 800, "out"), (8, 130, 305, "t1")]
COLS = {"plan": [167, 298, 428], "risk": [298], "fac": [298], "out": [298], "t1": [110, 180, 240]}

def table_of(p, y):
    for t in TABLES:
        if t[0] == p and t[1] <= y < t[2]:
            return t
    return None

def col_of(kind, x):
    c = 0
    for b in COLS[kind]:
        if x >= b - 4:
            c += 1
    return c

def join(lines):
    s = ""
    for t in lines:
        if not s:
            s = t
        elif s.endswith(" ") or t.startswith(" "):
            s += t
        elif s.endswith("-") and not s.endswith(" -"):
            s += t
        else:
            s += " " + t
    return re.sub(r"\s+", " ", s).strip()

def join_runs(lines):
    """lines: list of span lists -> merged runs list [(text,bold)]"""
    runs = []
    prev = ""
    for spans in lines:
        txt = "".join(t for t, _ in spans)
        if prev and not (prev.endswith(" ") or txt.startswith(" ") or (prev.endswith("-") and not prev.endswith(" -"))):
            spans = [(" ", False)] + spans
        for t, b in spans:
            if runs and runs[-1][1] == b:
                runs[-1] = (runs[-1][0] + t, b)
            else:
                runs.append((t, b))
        prev = txt
    runs = [(re.sub(r"\s+", " ", t), b) for t, b in runs]
    if runs:
        runs[0] = (runs[0][0].lstrip(), runs[0][1]); runs[-1] = (runs[-1][0].rstrip(), runs[-1][1])
    return [r for r in runs if r[0]]

# ---------- build element stream ----------
elements = []  # dicts: type in heading/para/table/image/pagebreak; box key
tables = {}    # kind -> state

for p in range(1, len(pdf)):
    pg = pdf[p]
    segs = box_segments(pg)
    items = [("line", l["y"], l) for l in page_lines(pg)] + [("img", im["y"], im) for im in page_images(p)]
    items.sort(key=lambda it: (round(it[1]), it[2]["x"] if it[0] == "line" else 0))
    for kind, y, obj in items:
        t = table_of(p, y) if kind == "line" else None
        if t:
            tk = t[3]
            el = elements[-1] if elements and elements[-1]["type"] == "table" and elements[-1]["kind"] == tk else None
            if el is None:
                el = dict(type="table", kind=tk, lines=[], box=None)
                elements.append(el)
            el["lines"].append((p, obj))
            continue
        def seg_for(yy):
            for s in segs:
                if s[0] - 2 <= yy <= s[1] + 2:
                    return (p, s[0])
            return None
        if kind == "img":
            box = seg_for(y + 5)
            elements.append(dict(type="image", path=obj["path"], w=obj["w"], box=box))
            continue
        l = obj
        box = seg_for(l["y"] + 3)
        if l["x"] < 40 and box is None or (l["x"] < 40 and l["size"] >= 9 and p == 1 and l["y"] < 80):
            elements.append(dict(type="heading", text=l["text"].strip(), size=l["size"], y=l["y"], p=p))
            continue
        if l["x"] < 40:
            elements.append(dict(type="heading", text=l["text"].strip(), size=l["size"], y=l["y"], p=p))
            continue
        # page-2 form header lines (centered, no box)
        if box is None and p == 1 and l["y"] < 80:
            elements.append(dict(type="heading", text=l["text"].strip(), size=l["size"], center=True, y=l["y"], p=p))
            continue
        # bullet marker
        if 55 < l["x"] < 70:
            elements.append(dict(type="para", runs=[], lines=[], marker=l["text"].strip(), y=l["y"], p=p, box=box, bullet=True))
            continue
        last = elements[-1] if elements else None
        same = (last and last["type"] == "para" and last["box"] == box and last["p"] == p and
                0 < l["y"] - last["y"] < 16 and (l["x"] > 65) == bool(last.get("bullet")))
        if last and last["type"] == "para" and last.get("bullet") and not last["lines"] and abs(l["y"] - last["y"]) < 3:
            same = True
        # paragraph continuing across page break inside same continuing box
        if (not same and last and last["type"] == "para" and box and box[1] < 40 and last["p"] == p - 1
                and last["y"] > 740 and l["y"] < 60 and (l["x"] > 65) == bool(last.get("bullet"))):
            same = True
        if re.match(r"\[\d+\]", l["text"]):
            same = False
        if same:
            last["lines"].append(l["spans"]); last["y"] = l["y"]; last["p"] = p
        else:
            elements.append(dict(type="para", lines=[l["spans"]], y=l["y"], p=p, box=box,
                                 bullet=l["x"] > 65, marker=None, ref=bool(re.match(r"\[\d+\]", l["text"]))))

# box continuity across pages: a box starting at page top continues the previous box
# if the previous element was also boxed and nothing (heading/unboxed table) intervened.
prev_box = None
alias = {}
for el in elements:
    b = el.get("box")
    if b is None:
        prev_box = None
        continue
    b = alias.get(b, b)
    if prev_box and b != prev_box and b[1] < 40 and b[0] == prev_box[0] + 1:
        alias[el["box"]] = prev_box
        b = prev_box
    el["box"] = b
    prev_box = b

for k, el in enumerate(elements):
    if el["type"] == "para" and el.get("bullet"):
        nxt = elements[k + 1] if k + 1 < len(elements) else None
        el["last_bullet"] = not (nxt and nxt["type"] == "para" and nxt.get("bullet"))

# ---------- tables -> rows ----------
def build_rows(el):
    kind = el["kind"]
    ncol = len(COLS[kind]) + 1
    lines = el["lines"]
    rows = []
    if kind == "t1":
        groups = []
        for p, l in lines:
            if not l["text"].strip():
                continue
            if groups and abs(l["y"] - groups[-1][0]) < 4 or (groups and l["y"] < 155 and groups[-1][0] < 155):
                groups[-1][1].append(l)
            else:
                groups.append([l["y"], [l]])
        for _, ls in groups:
            cells = [[] for _ in range(ncol)]
            for l in sorted(ls, key=lambda d: d["y"]):
                cells[col_of(kind, l["x"])].append(l["spans"])
            rows.append(cells)
        return rows, True
    header_y = {"plan": [(5, 540), (6, 65)], "risk": [(6, 705), (7, 50)], "fac": [(7, 340)], "out": [(7, 495)]}[kind]
    header = [[] for _ in range(ncol)]
    body = []
    cur = None
    last_y = None; last_p = None
    for p, l in lines:
        hdr = any(p == hp and l["y"] < hy for hp, hy in header_y)
        if hdr:
            if p == lines[0][0]:
                header[col_of(kind, l["x"])].append(l["spans"])
            continue
        c = col_of(kind, l["x"])
        if kind == "plan":
            new = c == 0
        else:
            new = cur is None or p != last_p or l["y"] - last_y > 16
        if new:
            cur = [[] for _ in range(ncol)]; body.append(cur)
        cur[c].append(l["spans"])
        if not (kind == "plan" and c == 0):
            pass
        last_y = l["y"]; last_p = p
    # plan: lines of one row are interleaved by column; sort not needed since appended in y order per column
    return [header] + body, True

# ---------- docx helpers ----------
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Pt(595.3), Pt(841.9)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Pt(36))
sec.top_margin = Pt(36); sec.bottom_margin = Pt(36)
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(9)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(0)
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.line_spacing = 1.15

def set_borders(tbl, sz=4):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}")
        x.set(qn("w:val"), "single"); x.set(qn("w:sz"), str(sz)); x.set(qn("w:color"), "000000")
        b.append(x)
    tblPr.append(b)

def set_widths(tbl, widths_pt):
    tbl.autofit = False
    tblPr = tbl._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    for row in tbl.rows:
        for c, w in zip(row.cells, widths_pt):
            c.width = Pt(w)
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_pt):
        gc.set(qn("w:w"), str(int(w * 20)))

def add_runs(par, runs, size=9, force_bold=False):
    for t, b in runs:
        r = par.add_run(t)
        r.bold = True if force_bold else (b or None)
        r.font.size = Pt(size)

def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)

LABELS = ("Başvuru Sahibinin Adı Soyadı:", "Araştırma Önerisinin Başlığı:", "Akademik Danışmanın Adı Soyadı:",
          "Anahtar Kelimeler:")

def write_para(container, el, first):
    par = container.paragraphs[0] if first else container.add_paragraph()
    runs = join_runs(el["lines"])
    # bold form labels
    if runs and any(runs[0][0].startswith(lb) for lb in LABELS):
        lb = next(lb for lb in LABELS if runs[0][0].startswith(lb))
        rest = runs[0][0][len(lb):]
        runs = [(lb, True)] + ([(rest, False)] if rest else []) + runs[1:]
    if el.get("bullet"):
        pf = par.paragraph_format
        pf.left_indent = Pt(30); pf.first_line_indent = Pt(-11)
        pf.tab_stops.add_tab_stop(Pt(30))
        mk = el.get("marker") or ""
        if mk:
            add_runs(par, [(mk + "\t", False)])
        pf.space_after = Pt(2)
    else:
        par.paragraph_format.space_after = Pt(2 if el.get("ref") else 9)
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if el.get("bullet") and el.get("last_bullet"):
        par.paragraph_format.space_after = Pt(9)
    add_runs(par, runs)
    return par

def write_image(container, el, first):
    par = container.add_paragraph() if not first else container.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    w = min(el["w"], 505)
    par.add_run().add_picture(el["path"], width=Pt(w))
    par.paragraph_format.space_after = Pt(6)

def write_table(container, el):
    rows, has_header = build_rows(el)
    kind = el["kind"]
    ncol = len(rows[0])
    tbl = container.add_table(rows=len(rows), cols=ncol)
    set_borders(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    if kind == "plan":
        widths = [130.8] * 4
    elif kind == "t1":
        widths = [85, 75, 65, 75]
    else:
        widths = [261.5, 261.5]
    set_widths(tbl, widths)
    for ri, cells in enumerate(rows):
        for ci, lines in enumerate(cells):
            cell = tbl.cell(ri, ci)
            par = cell.paragraphs[0]
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.line_spacing = 1.15
            add_runs(par, join_runs(lines), force_bold=(ri == 0))
    if kind != "t1":
        repeat_header(tbl.rows[0])
    return tbl

# ---------- cover page ----------
cover_imgs = page_images(0)
for _ in range(1):
    doc.add_paragraph()
p0 = doc.paragraphs[0]
p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
p0.add_run().add_picture(cover_imgs[0]["path"], width=Pt(cover_imgs[0]["w"]))
def cover(text, size, before):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(before)
    r = p.add_run(text); r.bold = size >= 14; r.font.size = Pt(size)
cover("TÜBİTAK 2209-A ÜNİVERSİTE ÖĞRENCİLERİ ARAŞTIRMA", 14, 100)
cover("PROJELERİ DESTEKLEME PROGRAMI", 14, 4)
cover("ARAŞTIRMA ÖNERİSİ FORMU", 14, 130)
cover("2026 Yılı", 12, 210)
cover("1. Dönem Başvurusu", 12, 18)
doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)

# ---------- body ----------
i = 0
prev_heading_main = False
while i < len(elements):
    el = elements[i]
    if el["type"] == "heading":
        par = doc.add_paragraph()
        if el.get("center"):
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            par.paragraph_format.space_before = Pt(14 if el["size"] >= 10 else 8)
            par.paragraph_format.space_after = Pt(8)
        if el["text"].startswith("2026 Yılı"):
            par.paragraph_format.space_after = Pt(18)
        r = par.add_run(el["text"]); r.bold = True; r.font.size = Pt(el["size"])
        i += 1
        continue
    if el["type"] == "table" and el["box"] is None:
        write_table(doc, el)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        i += 1
        continue
    box = el["box"]
    group = []
    while i < len(elements) and elements[i]["type"] != "heading" and elements[i].get("box") == box and box is not None:
        group.append(elements[i]); i += 1
    if not group:
        # unboxed para
        write_para(doc, el, False); i += 1
        continue
    outer = doc.add_table(rows=1, cols=1)
    set_borders(outer)
    set_widths(outer, [523])
    cell = outer.cell(0, 0)
    first = True
    for g in group:
        if g["type"] == "para":
            write_para(cell, g, first)
        elif g["type"] == "image":
            write_image(cell, g, first)
        elif g["type"] == "table":
            if first:
                cell.paragraphs[0].text = ""
            write_table(cell, g)
            cell.add_paragraph()
        first = False
    # drop trailing space_after in box
    last = cell.paragraphs[-1]
    if last.text == "" and len(cell.paragraphs) > 1 and not last._p.findall(qn("w:r")):
        pass
    else:
        last.paragraph_format.space_after = Pt(0)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

doc.save(OUT)
print("saved", OUT, "elements", len(elements))
