import json, base64, sys, shutil, os
import docx
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
src, out = sys.argv[1], sys.argv[2]
j = json.load(open(src, encoding='utf-8'))
if os.path.exists(out):
    shutil.copy(out, out.replace('.docx', '_v1_kisa.docx'))
open(out, 'wb').write(base64.b64decode(j['data']['bytes_b64']))
d = docx.Document(out)
P = d.paragraphs
for p in P[:3]:
    p._element.getparent().remove(p._element)
P = d.paragraphs
def yaz(p, satirlar, bold=(), size=12):
    for r in list(p.runs): r._element.getparent().remove(r._element)
    for k, s in enumerate(satirlar):
        r = p.add_run(s); r.bold = k in bold; r.font.size = Pt(size)
        if k < len(satirlar) - 1: r.add_break()
i = next(k for k, p in enumerate(P) if p.text.startswith('1. Te'))
for p in P[:i]: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
yaz(P[0], ['İzmir Bakırçay Üniversitesi', 'Yönetim Bilişim Sistemleri Bölümü'], bold=(0,), size=14)
P[0].paragraph_format.space_before = Pt(60)
for r in P[1].runs: r.font.size = Pt(16)
P[1].paragraph_format.space_before = Pt(90); P[1].paragraph_format.space_after = Pt(30)
yaz(P[2], ['MIS412 Bitirme Projesi Ara Raporu', 'Kasım 2026'], size=13)
P[2].paragraph_format.space_after = Pt(60)
d.tables[0].alignment = 1
P[i].insert_paragraph_before().add_run().add_break(WD_BREAK.PAGE)
d.styles['Normal'].font.name = 'Times New Roman'; d.styles['Normal'].font.size = Pt(12)
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.text = r.text.replace('\u2753', '')
                    r.font.size = Pt(10)
silinecek = ('Veri hattı · 6 adım', 'PVGIS v5.3, 2005')
for p in list(d.paragraphs):
    t = p.text
    if t.startswith(silinecek):
        p._element.getparent().remove(p._element); continue
    if t.startswith('Dönem planı ·'):
        for r in p.runs[1:]: r.text = ''
        p.runs[0].text = 'Şekil 4. Dönem planı (tamamlanan ve kalan işler)'; p.runs[0].italic = True
    if t.startswith(('Tablo ', 'Şekil ', 'Dönem planı')) or p._element.xpath('.//w:drawing'):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:
        if '\u2753' in r.text:
            r.text = r.text.replace('\u2753', '[?]'); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
d.save(out)
print('ok', len(d.paragraphs), 'paragraf', len(d.tables), 'tablo', len(d.inline_shapes), 'gorsel')
