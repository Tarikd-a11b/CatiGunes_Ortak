import re
import docx, sys
from docx.shared import Cm, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
f=sys.argv[1]; d=docx.Document(f)
for t in d.tables:
    tblPr=t._element.tblPr
    old=tblPr.find(qn('w:tblBorders'))
    if old is not None: tblPr.remove(old)
    b=OxmlElement('w:tblBorders')
    for e in ('top','left','bottom','right','insideH','insideV'):
        x=OxmlElement('w:'+e); x.set(qn('w:val'),'single'); x.set(qn('w:sz'),'4'); x.set(qn('w:space'),'0'); x.set(qn('w:color'),'808080'); b.append(x)
    tblPr.append(b)
    nxt=t._element.getnext()
    if nxt is not None and nxt.tag==qn('w:p'):
        docx.text.paragraph.Paragraph(nxt,d._body).paragraph_format.space_before=Pt(8)
inbib=False
for p in d.paragraphs:
    if 'Skor}' in p.text:
        for r in p.runs[1:]: r._element.getparent().remove(r._element)
        p.runs[0].text='Skor = E × (1 + α × Ö + β × H)'
        p.runs[0].italic=True; p.runs[0].font.name='Times New Roman'; p.runs[0].font.size=Pt(10)
        p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
for p in d.paragraphs:
    if p.text.startswith('dönem planı'):
        for r in p.runs[1:]: r._element.getparent().remove(r._element)
        p.runs[0].text='Şekil 1. Dönem planı (Gantt şeması): 8 iş paketi, 2 kilometre taşı'
        p.runs[0].italic=True; p.runs[0].font.size=Pt(10)
        p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    if p.text.strip()=='Açıklamalı kaynakça': inbib=True; continue
    if inbib and p.style.name=='Normal':
        pf=p.paragraph_format; pf.alignment=WD_ALIGN_PARAGRAPH.LEFT
        pf.left_indent=Cm(1); pf.first_line_indent=Cm(-1); pf.space_after=Pt(3)
        for r in p.runs: r.font.size=Pt(8)
    if re.match(r'Tablo \d\.',p.text): p.paragraph_format.space_before=Pt(6); p.paragraph_format.keep_with_next=True
d.save(f); print('ok')
