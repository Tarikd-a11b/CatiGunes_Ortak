import sys, copy, docx
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
f = sys.argv[1]; d = docx.Document(f)
# 1) vurguyu yalniz [?] isaretine indir
for p in d.paragraphs:
    for r in list(p.runs):
        if r.font.highlight_color == WD_COLOR_INDEX.YELLOW and r.text != '[?]':
            parts = r.text.split('[?]'); r.font.highlight_color = None
            r.text = parts[0]; prev = r._element
            for k, part in enumerate(parts[1:]):
                for txt, hl in (('[?]', True), (part, False)):
                    if not txt: continue
                    e = copy.deepcopy(r._element); prev.addnext(e); prev = e
                    from docx.text.run import Run
                    nr = Run(e, p); nr.text = txt
                    nr.font.highlight_color = WD_COLOR_INDEX.YELLOW if hl else None
# 2) formuller
F = {'P_i = ': 'Pᵢ = min( Aᵢ × k_yer × p_panel ;  P_yasal )',
     'NPV_i = ': 'NPVᵢ = − C₀ · Pᵢ  +  Σₜ₌₁ᵀ  [ Eᵢ · (1 − d)ᵗ⁻¹ · cₜ − O&Mₜ ] / (1 + r)ᵗ'}
for p in d.paragraphs:
    for k, v in F.items():
        if p.text.startswith(k):
            for r in p.runs[1:]: r._element.getparent().remove(r._element)
            r = p.runs[0]; r.text = v; r.font.name = 'Cambria Math'; r.font.size = Pt(12); r.italic = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pPr = p._element.pPr
            if pPr is not None:
                for sh in pPr.findall('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd'): pPr.remove(sh)
d.save(f); print('ok')
