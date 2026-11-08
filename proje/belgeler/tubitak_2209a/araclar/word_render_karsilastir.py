import sys, shutil
from pathlib import Path
sys.path.insert(0, r"C:\Users\dmrta\Desktop\Katip\bench")
from real_word import real_word
import pypdfium2 as p
from PIL import Image

# Kullanim: python word_render_karsilastir.py <cikti.docx> <kaynak.pdf>
# Gercek Word ile PDF'e basar, calisma\b<N>.png yan yana (sol kaynak, sag Word) uretir.
S = Path(__file__).resolve().parent / "calisma"
S.mkdir(exist_ok=True)
seed = S / "render_seed.docx"
shutil.copy(sys.argv[1], seed)
shutil.copy(sys.argv[2], S / "src.pdf")
with real_word(seed) as app:
    d = app.ActiveDocument
    d.ExportAsFixedFormat(str(S / "built.pdf"), 17)
    print("pages", d.ComputeStatistics(2))
    d.Close(0)
a = p.PdfDocument(str(S / "src.pdf")); b = p.PdfDocument(str(S / "built.pdf"))
for i in range(max(len(a), len(b))):
    ims = [d[i].render(scale=0.9).to_pil() if i < len(d) else Image.new("RGB", (536, 758), "white") for d in (a, b)]
    c = Image.new("RGB", (ims[0].width + ims[1].width + 10, max(x.height for x in ims)), "red")
    c.paste(ims[0], (0, 0)); c.paste(ims[1], (ims[0].width + 10, 0)); c.save(S / f"b{i+1}.png")
print("ok")
