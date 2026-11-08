from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Ar", F + r"\arial.ttf"))
pdfmetrics.registerFont(TTFont("ArB", F + r"\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("ArI", F + r"\ariali.ttf"))
pdfmetrics.registerFont(TTFont("ArBI", F + r"\arialbi.ttf"))
pdfmetrics.registerFontFamily("Ar", normal="Ar", bold="ArB", italic="ArI", boldItalic="ArBI")

OUT = r"C:\Users\dmrta\Desktop\Projeler\CatiGunes\belgeler\Cati_Gunes_Model_Nasil_Calisir.pdf"
TEAL = colors.HexColor("#0E6B67"); INK = colors.HexColor("#1D2327"); MUTED = colors.HexColor("#5B6770")
LIGHT = colors.HexColor("#EEF4F3"); AMBER = colors.HexColor("#C77700"); WARN = colors.HexColor("#FFF4E0")

body = ParagraphStyle("b", fontName="Ar", fontSize=10, leading=14, textColor=INK, spaceAfter=4)
small = ParagraphStyle("s", parent=body, fontSize=9, leading=12.5)
h1 = ParagraphStyle("h1", fontName="ArB", fontSize=12.5, leading=16, textColor=TEAL, spaceBefore=9, spaceAfter=4)
num = ParagraphStyle("n", fontName="ArB", fontSize=15, leading=18, textColor=colors.white, alignment=1)


def P(t, s=body):
    return Paragraph(t, s)


def akis():
    adimlar = [("1", "Binayı bul", "OSM ayak izi"), ("2", "Görüntüyü al", "uydu karosu"),
               ("3", "Kaymayı düzelt", "gölge + eşleştirme"), ("4", "Çatıyı çiz", "SAM"),
               ("5", "Gölgeyi hesapla", "yükseklik + güneş"), ("6", "Üretimi hesapla", "PVGIS"),
               ("7", "Sırala", "teknik + ihtiyaç")]
    W, H = 17 * cm, 2.5 * cm
    d = Drawing(W, H)
    n = len(adimlar); gap = 0.3 * cm; bw = (W - gap * (n - 1)) / n; bh = 1.9 * cm; y = 0.3 * cm
    for i, (k, a, b) in enumerate(adimlar):
        x = i * (bw + gap)
        d.add(Rect(x, y, bw, bh, rx=4, ry=4, fillColor=TEAL if i in (3, 5) else LIGHT, strokeColor=TEAL, strokeWidth=0.8))
        fc = colors.white if i in (3, 5) else TEAL
        d.add(String(x + bw / 2, y + bh - 14, k, fontName="ArB", fontSize=12, fillColor=fc, textAnchor="middle"))
        d.add(String(x + bw / 2, y + bh - 29, a, fontName="ArB", fontSize=7.4, fillColor=colors.white if i in (3, 5) else INK, textAnchor="middle"))
        d.add(String(x + bw / 2, y + 7, b, fontName="Ar", fontSize=6.6, fillColor=colors.white if i in (3, 5) else MUTED, textAnchor="middle"))
        if i < n - 1:
            ax = x + bw + 1; ay = y + bh / 2
            d.add(Polygon([ax, ay + 3.5, ax, ay - 3.5, ax + gap - 2, ay], fillColor=AMBER, strokeColor=None))
    return d


def adim(k, baslik, metin):
    t = Table([[P(k, num), [P("<b>" + baslik + "</b>", ParagraphStyle("ab", parent=body, fontSize=11, textColor=TEAL, spaceAfter=2))] + [P(m) for m in metin]]],
              colWidths=[1.1 * cm, 15.9 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), TEAL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                           ("LEFTPADDING", (1, 0), (1, 0), 9), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LINEBELOW", (1, 0), (1, 0), 0.4, colors.HexColor("#C9D3D6"))]))
    return KeepTogether([t, Spacer(1, 5)])


def kutu(t, bg=WARN, bar=AMBER):
    x = Table([[P(t, small)]], colWidths=[17 * cm])
    x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return x


def sayfa(c, d):
    c.saveState(); c.setFont("Ar", 7.5); c.setFillColor(MUTED)
    c.drawString(2 * cm, 1.2 * cm, "Çatı Güneş Paneli — Model nasıl çalışır?")
    c.drawRightString(19 * cm, 1.2 * cm, str(d.page))
    c.setStrokeColor(TEAL); c.setLineWidth(2); c.line(2 * cm, 28.2 * cm, 19 * cm, 28.2 * cm); c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=1.8 * cm,
                      title="Çatı Güneş Paneli — Model Nasıl Çalışır?")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(2 * cm, 1.8 * cm, 17 * cm, 26 * cm)], onPage=sayfa)])

s = [P("Model Nasıl Çalışır?", ParagraphStyle("t", fontName="ArB", fontSize=19, leading=23, textColor=INK)),
     P("Çatı Güneş Paneli Uygunluk Analizi · Çiğli pilotu · adım adım çalışma mantığı", ParagraphStyle("st", parent=body, textColor=MUTED)),
     Spacer(1, 4),
     P("<b>Girdi:</b> bir binanın konumu ve uydu görüntüsü. <b>Çıktı:</b> o çatıya kaç kW panel sığdığı, yılda kaç kWh üreteceği ve "
       "mahallenin öncelik sırası. Her bina aynı yedi adımdan geçer:"),
     Spacer(1, 2), akis(), Spacer(1, 6)]

s.append(adim("1", "Binayı bul", [
    "OpenStreetMap'ten her binanın <b>taban poligonu</b> (ayak izi) alınır. Bu, binanın yerde nerede durduğunu söyler "
    "ama çatının şeklini ve ne kadarının kullanılabilir olduğunu söylemez."]))
s.append(adim("2", "Uydu görüntüsünü al", [
    "Binanın olduğu yerin uydu görüntüsü indirilir (piksel başına ~23 cm, yani bir piksel yaklaşık bir karo kiremit büyüklüğünde)."]))
s.append(adim("3", "Kaymayı düzelt", [
    "Uydu tam tepeden değil biraz <b>eğik</b> bakar. Bu yüzden görüntüde çatı, binanın tabanına göre birkaç metre kaymış görünür; "
    "yüksek binada daha çok.",
    "Model önce görüntüdeki <b>gölgeleri</b> bulur (koyu ve mavimsi pikseller). Gölgelerin hangi yöne düştüğünden güneşin "
    "o an nerede olduğunu hesaplar. Sonra taban poligonunu küçük adımlarla kaydırıp görüntüdeki çatıyla en iyi örtüştüğü yeri "
    "arar (±3,5–8 m). Bu işleme <b>oturtma</b> diyoruz."]))
s.append(adim("4", "Çatıyı çiz — SAM", [
    "Meta'nın <b>Segment Anything Model (SAM)</b> adlı hazır yapay zekâ modeli kullanılır. Modele görüntüyle birlikte "
    "<b>“bu kutunun içindeki nesneyi çiz”</b> diye bir kutu verilir; kutu, binanın ayak izinden hesaplanır. SAM kutunun içindeki "
    "çatının sınırını piksel piksel çıkarır.",
    "SAM'i biz eğitmedik; milyonlarca görüntüyle önceden eğitilmiş hâlini olduğu gibi kullanıyoruz (<i>zero-shot</i>). "
    "SAM bazen binanın yan duvarını da çatıya katar; bu yüzden son çatı = <b>SAM maskesi ∩ oturtulmuş ayak izi</b>.",
    "Son olarak çatının rengine bakılır: kiremit kırmızısı varsa <b>eğimli</b>, yoksa <b>düz/teras</b> sayılır."]))
s.append(adim("5", "Gölgeyi hesapla", [
    "Her binanın <b>yüksekliği</b>, düşürdüğü gölgenin boyundan bulunur (güneş açısı biliniyor, trigonometri).",
    "Sonra bütün Çiğli'nin bir yükseklik haritası kurulur ve yıl boyunca 279 farklı güneş konumu için "
    "“bu çatı noktası şu an komşu binanın gölgesinde mi?” sorusu GPU'da sorulur. Sonuç: her çatının yıllık "
    "<b>gölge kaybı yüzdesi</b> (Çiğli'de medyan %1,2)."]))
s.append(adim("6", "Üretimi hesapla — PVGIS", [
    "<b>Kaç panel sığar?</b> Çatı alanının hepsi kullanılamaz: düz çatıda panel sıraları arasına boşluk gerekir (alanın %55'i), "
    "eğimli çatıda yüzeyin %70'i. Her 6 m² ≈ 1 kWp panel.",
    "<b>1 kWp yılda kaç kWh üretir?</b> Bunu Avrupa Komisyonu'nun <b>PVGIS</b> servisi söyler: konum, eğim ve yön verilince "
    "o noktanın uzun yıllık güneş verisinden yıllık üretimi hesaplar (Çiğli'de düz panel ≈ 1.372 kWh/kWp).",
    "<b>kWh = kWp × PVGIS verimi × (1 − gölge kaybı × 0,65)</b> — 0,65 çünkü gölge yalnız doğrudan güneşi keser, "
    "gökyüzünden gelen dağınık ışığı kesmez.",
    "Çatının gerçek eğimi ve yönü uydudan kesin ölçülemediği için tek sayı değil <b>alt–üst bant</b> verilir "
    "(düz çatıda alt: panel yatay, üst: 30° güneye eğik)."]))

# örnek hesap
ornek = [["Adım", "Değer"],
         ["Düz çatı alanı (SAM ∩ ayak izi)", "200 m²"],
         ["Kullanılabilir alan (× 0,55)", "110 m²"],
         ["Kurulu güç (÷ 6 m²/kWp)", "≈ 18,3 kWp"],
         ["Gölge kaybı (5. adım)", "%5 → çarpan 1 − 0,05 × 0,65 = 0,97"],
         ["Alt sınır (yatay panel, 1.372 kWh/kWp)", "18,3 × 1.372 × 0,97 ≈ <b>24.300 kWh/yıl</b>"],
         ["Üst sınır (30° güneye, ~1.575 kWh/kWp)", "18,3 × 1.575 × 0,97 ≈ <b>27.900 kWh/yıl</b>"],
         ["Kaç haneye yeter? (hane ≈ 2.965 kWh/yıl)", "≈ 8–9 hane"]]
cs = ParagraphStyle("c", parent=body, fontSize=9, leading=12, spaceAfter=0)
t = Table([[P(c, ParagraphStyle("h", parent=cs, fontName="ArB", textColor=colors.white)) for c in ornek[0]]] +
          [[P(c, cs) for c in r] for r in ornek[1:]], colWidths=[7.5 * cm, 9.5 * cm])
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3D6")),
                       ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)] +
                      [("BACKGROUND", (0, i), (-1, i), LIGHT) for i in range(2, len(ornek), 2)]))
s.append(KeepTogether([P("Örnek: tek bir düz çatı", h1), t,
                       P("Rakamlar yuvarlatılmış bir örnektir; üst sınırdaki PVGIS değeri yaklaşıktır.", ParagraphStyle("k", parent=small, textColor=MUTED))]))
s.append(Spacer(1, 4))

s.append(adim("7", "Mahalleleri sırala", [
    "Çatı sonuçları mahalle bazında toplanır. Her mahalle üç eksende puanlanır ve ağırlıklı toplamla sıralanır:",
    "<b>Teknik (%50)</b> ne kadar elektrik üretebilir · <b>İhtiyaç (%35)</b> askıda fatura başvurusu, düşük su tüketimi, düşük "
    "sosyo-ekonomik statü · <b>Erişim (%15)</b> kamu binası (okul, sağlık ocağı) çatı alanı.",
    "Puanlar sıra yüzdeliğine çevrilir; böylece tek bir dev bina bütün ölçeği ele geçiremez. "
    "Yalnız teknik sıralama ile bu sıralama belirgin biçimde farklı çıkıyor: toplumsal katman sonucu gerçekten değiştiriyor."]))

s.append(P("Model kendi hatasını nasıl yakalıyor?", h1))
s.append(P("Oturtma adımında çatı ile ayak izinin ne kadar örtüştüğü bir <b>oturtma oranı</b> olarak kaydedilir. Oran 0,4'ün "
           "altındaysa model “bu çatıyı büyük ihtimalle yanlış yere oturttum” der. Örneklem denetiminde bu çatıların yalnız %17'si "
           "doğru çıktı, geri kalanlarda doğruluk %88'di. Bu yüzden 0,4 altındaki çatılar (%11) toplamlara katılmaz, ayrıca gösterilir."))
s.append(Spacer(1, 4))
s.append(kutu("<b>Tek cümlede:</b> OSM binanın <i>nerede</i> olduğunu, SAM çatının <i>şeklini</i>, gölgeler güneşin <i>yönünü</i> ve "
              "binanın <i>yüksekliğini</i>, PVGIS de o çatının <i>ne kadar güneş aldığını</i> söyler; model bunları birleştirip "
              "çatı başına üretim bandı çıkarır ve toplumsal ihtiyaçla birlikte sıralar.", bg=LIGHT, bar=TEAL))

doc.build(s)
print("ok")
