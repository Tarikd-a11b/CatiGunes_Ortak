import docx, sys
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
d=docx.Document('export.docx')
for s in d.sections:
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    for m in ('left_margin','right_margin','top_margin','bottom_margin'): setattr(s,m,Cm(2.5))
FONT='Times New Roman'
def setfont(style, size, bold=None, color=None):
    f=style.font; f.name=FONT; f.size=Pt(size)
    if bold is not None: f.bold=bold
    if color is not None: f.color.rgb=color
    rpr=style.element.get_or_add_rPr(); rf=rpr.find(qn('w:rFonts'))
    if rf is None: rf=OxmlElement('w:rFonts'); rpr.append(rf)
    for a in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): rf.set(qn(a),FONT)
black=RGBColor(0,0,0)
for name,size,b in [('Normal',9,None),('List Paragraph',9,None),('Heading 1',13,True),('Heading 2',10.5,True),('Heading 3',9.5,True)]:
    try:
        st=d.styles[name]; setfont(st,size,b,black)
        pf=st.paragraph_format; pf.line_spacing=1.15
        if name=='Normal' or name=='List Paragraph': pf.space_after=Pt(4); pf.space_before=Pt(0)
        else: pf.space_before=Pt(10 if name!='Heading 3' else 6); pf.space_after=Pt(4)
    except KeyError: pass
# strip run-level fonts/colors so styles apply
for p in d.paragraphs:
    for r in p.runs:
        r.font.name=None; r.font.color.rgb=None; r.font.size=None
        rpr=r._element.rPr
        if rpr is not None:
            rf=rpr.find(qn('w:rFonts'))
            if rf is not None: rpr.remove(rf)
    if p.style.name=='Normal': p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
# byline
by=d.paragraphs[1]
for r in by.runs[1:]: r._element.getparent().remove(r._element)
if by.runs: by.runs[0].text='İzmir Bakırçay Üniversitesi · Yönetim Bilişim Sistemleri · Ekim 2026'
else: by.add_run('İzmir Bakırçay Üniversitesi · Yönetim Bilişim Sistemleri · Ekim 2026')
by.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
# hyperlinks/mention leftovers in byline
for el in by._element.findall(qn('w:hyperlink')): by._element.remove(el)
d.paragraphs[0].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
# tables
def shade(cell,hexc):
    tcPr=cell._element.get_or_add_tcPr(); sh=OxmlElement('w:shd'); sh.set(qn('w:val'),'clear'); sh.set(qn('w:color'),'auto'); sh.set(qn('w:fill'),hexc); tcPr.append(sh)
for t in d.tables:
    t.style=d.styles['Table Grid'] if 'Table Grid' in [s.name for s in d.styles] else t.style
    for i,row in enumerate(t.rows):
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
                for r in p.runs:
                    r.font.size=Pt(8.5); r.font.name=FONT; r.font.color.rgb=None
                    if i==0: r.font.bold=True
            if i==0: shade(c,'E7E6E6')
# image width
for sh in d.inline_shapes:
    ratio=sh.height/sh.width; sh.width=Cm(16); sh.height=int(Cm(16)*ratio)
d.save(sys.argv[1]); print('saved')
