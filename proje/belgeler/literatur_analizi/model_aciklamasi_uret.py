from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether, PageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Ar", F + r"\arial.ttf"))
pdfmetrics.registerFont(TTFont("ArB", F + r"\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("ArI", F + r"\ariali.ttf"))
pdfmetrics.registerFont(TTFont("ArBI", F + r"\arialbi.ttf"))
pdfmetrics.registerFontFamily("Ar", normal="Ar", bold="ArB", italic="ArI", boldItalic="ArBI")

OUT = r"C:\Users\dmrta\Desktop\Projeler\CatiGunes\belgeler\Cati_Gunes_Model_Aciklamasi.pdf"

TEAL = colors.HexColor("#0E6B67")
AMBER = colors.HexColor("#C77700")
INK = colors.HexColor("#1D2327")
MUTED = colors.HexColor("#5B6770")
LIGHT = colors.HexColor("#EEF4F3")
WARN_BG = colors.HexColor("#FFF4E0")
LINE = colors.HexColor("#C9D3D6")

body = ParagraphStyle("b", fontName="Ar", fontSize=9.3, leading=12.6, textColor=INK, spaceAfter=4)
small = ParagraphStyle("s", parent=body, fontSize=8.6, leading=11.4)
cell = ParagraphStyle("c", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
cellh = ParagraphStyle("ch", parent=cell, fontName="ArB", textColor=colors.white)
h1 = ParagraphStyle("h1", fontName="ArB", fontSize=13.5, leading=17, textColor=TEAL, spaceBefore=8, spaceAfter=5)
h2 = ParagraphStyle("h2", fontName="ArB", fontSize=10.8, leading=14, textColor=INK, spaceBefore=6, spaceAfter=3)
bullet = ParagraphStyle("bl", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=2)
q = ParagraphStyle("q", parent=body, fontName="ArB", textColor=TEAL, spaceBefore=5, spaceAfter=1)


def P(t, s=body):
    return Paragraph(t, s)


def B(items):
    return [Paragraph(t, bullet, bulletText="•") for t in items]


def tablo(rows, widths, first_bold=False):
    data = [[P(c, cellh) for c in rows[0]]] + [[P(c, cell) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), TEAL),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(st))
    return t


def kutu(t, bg=WARN_BG, bar=AMBER):
    x = Table([[P(t, small)]], colWidths=[17 * cm])
    x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return x


def sayfa(c, d):
    c.saveState()
    c.setFont("Ar", 7.5)
    c.setFillColor(MUTED)
    c.drawString(2 * cm, 1.2 * cm, "Çatı Güneş Paneli Uygunluk Analizi ve Toplumsal Öncelik KDS — Model Açıklaması")
    c.drawRightString(19 * cm, 1.2 * cm, f"{d.page}")
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    c.line(2 * cm, 28.2 * cm, 19 * cm, 28.2 * cm)
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      bottomMargin=1.8 * cm, title="Çatı Güneş Paneli — Model Açıklaması",
                      author="Çatı Güneş Paneli Proje Ekibi")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(2 * cm, 1.8 * cm, 17 * cm, 26 * cm, id="f")],
                                   onPage=sayfa)])

s = []
s.append(P("Çatı Güneş Paneli Uygunluk Analizi ve<br/>Toplumsal Öncelik Karar Destek Sistemi",
           ParagraphStyle("t", fontName="ArB", fontSize=18, leading=23, textColor=INK)))
s.append(Spacer(1, 4))
s.append(P("Model açıklaması, kaynaklar ve olası sorular · Danışman toplantısı hazırlık notu · 30 Eylül 2026 · Pilot: İzmir / Çiğli",
           ParagraphStyle("st", parent=body, textColor=MUTED)))
s.append(Spacer(1, 8))

# özet kartları
kart = [["18.064", "5,53 km²", "383–504 MWp", "526–749 GWh/yıl"],
        ["güvenilir çatı", "çatı alanı", "kurulu güç bandı", "yıllık üretim bandı"]]
kt = Table(kart, colWidths=[4.25 * cm] * 4)
kt.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "ArB", 14), ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
                        ("FONT", (0, 1), (-1, 1), "Ar", 8), ("TEXTCOLOR", (0, 1), (-1, 1), MUTED),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                        ("LINEAFTER", (0, 0), (2, -1), 1, colors.white),
                        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
s.append(kt)
s.append(Spacer(1, 4))
s.append(P("Kaynak: 17–18 Eylül 2026 tam Çiğli koşusu (Colab, T4 GPU). Sayılar yalnız oturtma oranı ≥ 0,4 olan güvenilir çatılardan hesaplanmıştır.", small))

s.append(P("1. Projenin özü", h1))
s.append(P("Uydu görüntüsünden Çiğli'deki çatıları çıkarıyor, her çatının yıllık güneş elektriği üretim potansiyelini hesaplıyor ve mahalleleri yalnız teknik verime göre değil, <b>toplumsal ihtiyaç</b> ve <b>kamu binası erişimine</b> göre de sıralıyoruz. Ayırt edici iddia: güneş yatırımları genellikle en kârlı çatıya yönelir; bu sistem teknik uygunluğu enerji adaleti boyutuyla birleştirir."))
s.append(P("<b>Pilot bölge:</b> Çiğli'nin 26 mahallesi ve Atatürk OSB — 131,4 km², 20.294 bina. <b>Politika dayanağı:</b> İzmir Bölge Planı 2024–2028, Tedbir 1.4.1 (çatı GES pilotu, prosumer desteği)."))

s.append(P("2. Uçtan uca boru hattı", h1))
s.append(tablo([
    ["#", "Adım", "Ne yapıyor", "Araç / kaynak"],
    ["1", "Birimler", "Mahalle ve OSB sınırlarını alır", "OpenStreetMap (admin_level)"],
    ["2", "Bina ayak izleri", "Her binanın taban poligonu", "OSM / Overpass API"],
    ["3", "Uydu çekimleri", "Her bölgenin hangi uydu çekiminden geldiğini belirler (4 çekim)", "Esri World Imagery + Wayback meta verisi"],
    ["4", "Karolar", "9.846 görüntü karosu indirilir", "0,234 m/piksel"],
    ["5", "Güneş geometrisi", "Gölgelerden güneş yönü <b>ölçülür</b>, çatının tabana göre kayması bulunur", "OpenCV, Otsu eşiği"],
    ["6–7", "<b>Segmentasyon</b>", "OSM ayak izinden <b>kutu istemi</b> verilir, SAM çatı maskesini çıkarır", "Meta SAM ViT-B"],
    ["8", "Maske ve tip", "SAM maskesi ∩ oturtulmuş ayak izi; kiremit / düz / karma ayrımı", "Lab renk uzayı, matchTemplate"],
    ["9", "Bina yüksekliği", "Gölge boyundan yükseklik", "Trigonometri"],
    ["10", "Komşu gölgesi", "Yıl boyunca 279 güneş konumunda ışın izleme (2 m ızgara)", "PyTorch (GPU)"],
    ["11", "Üretim", "Çatı başına kWp ve kWh bandı", "PVGIS API (81 sorgu)"],
    ["12–13", "Özet, dışa aktarım", "Mahalle toplamları, eski modelle karşılaştırma; GeoJSON/CSV", "pandas"],
    ["14", "Kamu eşleştirme", "Okul, sağlık, idari binalar çatılarla eşleşir (166 tesis)", "OSM, shapely"],
    ["15", "İnteraktif harita", "Renkli çatılar, bilgi kutusu", "Folium / Leaflet"],
    ["16", "Sınırlılıklar", "Varsayımlar açıkça listelenir", "—"],
], [1.3 * cm, 3.1 * cm, 7.4 * cm, 5.2 * cm]))

s.append(P("3. Kullanılan modeller", h1))
s.append(P("3.1 Segment Anything Model (SAM) — Meta AI, 2023", h2))
s += B([
    "<b>Varyant:</b> ViT-B (Vision Transformer Base), ~91 milyon parametre, ağırlık <i>sam_vit_b_01ec64.pth</i>.",
    "<b>Meta'nın eğitim verisi:</b> SA-1B — 11 milyon görüntü, 1,1 milyar maske.",
    "<b>Biz yeniden eğitmedik (zero-shot).</b> Türkiye için etiketli çatı verisi yok; SAM genel amaçlı ve istemle çalışıyor.",
    "<b>İstem türü: kutu (box prompt).</b> Her binanın OSM ayak izinin çevreleyen kutusu SAM'e verilir.",
    "<b>Neden kutu?</b> SolarSAM (2024) metin istemi kullanıyor ve IoU'su yalnız %28,6–36,2. SAM makalesi metinden maskeyi “keşifsel, tam güvenilir değil” sayıyor, kutuyu birinci sınıf istem kabul ediyor. Tez cümlesi: <i>“SolarSAM'ı taklit etmedik, zayıf halkasını değiştirdik.”</i>",
    "<b>Süre:</b> T4 GPU'da 1.334 kare ≈ 14 dk; tüm boru hattı ≈ 40 dk.",
])
s.append(P("3.2 PVGIS — Avrupa Komisyonu Ortak Araştırma Merkezi (JRC)", h2))
s += B([
    "Ücretsiz, anahtarsız güneş ışınımı ve PV üretim servisi.",
    "Parametreler: <i>peakpower=1</i> (kWp başına özgül verim), <i>loss=14</i> (%14 sistem kaybı), eğim, azimut.",
    "Çiğli merkezinde düz çatı verimi <b>1.372 kWh/kWp</b>; her mahalleye 0,977–1,017 ölçek katsayısı uygulanır.",
    "Dikkat: PVGIS'te azimut 0 = güney, pvlib/Google'da 0 = kuzey. Karışırsa sonuca sessizce 180° hata girer.",
])
s.append(P("3.3 Kendi yazdığımız kural tabanlı görüntü işleme", h2))
s += B([
    "<b>Gölge tespiti:</b> parlaklık Otsu eşiğinin altında ve mavilik B/(R+G+B) &gt; 0,30 ise, ya da parlaklık &lt; 62 ise gölge.",
    "<b>Güneş yönü:</b> ayak izleri her yöne kaydırılır, gölgeyle en çok çakışan yön seçilir. Güvenilirlik: tepe yönü / tam ters yön ≥ 2,0. Binaların %97,3'ü güvenilir çekimde.",
    "<b>Çatı oturtma:</b> uydu eğik baktığı için çatı tabana göre birkaç metre kayar. OpenCV <i>matchTemplate</i> ile bulunur; arama yarıçapı bina boyutuna göre ±3,5–8 m.",
    "<b>Çatı tipi:</b> Lab renk uzayında kırmızılık (a* &gt; 8, b* &gt; 5) ile kiremit payı → eğimli, karma, muhtemelen eğimli, düz/teras. Çiğli'de çatıların ~%52'si düz/teras.",
    "<b>Yükseklik:</b> gölge boyu ve güneş yükseklik açısından (medyan: &lt;150 m² binada 8 m, 300 m² üstünde 17,7 m).",
])

s.append(P("4. Üretim formülü", h1))
s.append(tablo([
    ["Çatı tipi", "Kurulu güç", "Verim bandı"],
    ["Düz / teras", "alan × <b>0,55</b> / 6 m²", "alt sınır 0° (yatay), üst sınır 30° güneye"],
    ["Eğimli", "yüz alanı × <b>0,70</b> / 6 m²", "eğim 17–33°; alt: yalnız güney yüz, üst: güney + doğu + batı yüzleri"],
], [3.2 * cm, 5 * cm, 8.8 * cm]))
s.append(Spacer(1, 6))
fx = Table([[P("<b>kWh = kWp × PVGIS özgül verimi × mahalle ölçeği × (1 − gölge kaybı × 0,65)</b>",
               ParagraphStyle("fx", parent=body, alignment=1, textColor=TEAL, fontSize=10.5))]], colWidths=[17 * cm])
fx.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, TEAL), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
s.append(fx)
s.append(Spacer(1, 4))
s += B([
    "<b>6 m²/kWp:</b> ~%20 verimli modül ve sıra aralıkları.",
    "<b>0,55:</b> düz çatıda sıra aralığı ve kenar boşlukları düşülünce kalan kullanılabilir oran.",
    "<b>0,65:</b> gölge yalnız doğrudan ışınımı keser; bu da yıllık ışınımın ~%65'i.",
    "<b>Neden bant?</b> Eğim ve yön tek uydu görüntüsünden kesin çıkarılamaz. Belirsizliği gizlemek yerine ölçüp bant olarak veriyoruz.",
])

s.append(P("5. Sonuçlar", h1))
s.append(tablo([
    ["Gösterge", "Değer"],
    ["Güvenilir çatı / alan", "18.064 çatı · 5,53 km²"],
    ["Kurulu güç", "383–504 MWp"],
    ["Yıllık üretim", "<b>526,3–749,2 GWh/yıl</b> (bant 1,42×)"],
    ["Ayrı tutulan şüpheli çatı", "2.227 çatı (%11) · 0,31 km² — toplamlara katılmaz"],
    ["Atatürk OSB", "217,8–278,6 GWh/yıl (~%37) — sanayi, mahalle sıralamasından ayrı raporlanır"],
    ["Kamu binaları", "156/166 tesis eşleşti · 173 güvenilir çatı · 18,2–26,3 GWh/yıl"],
    ["Yıllık komşu gölgesi", "medyan %1,2 · ortalama %6,2 · aralık-ocak ~%7–8, haziran ~%2"],
    ["Eski modele göre", "Ayak izi modeli 3,2× bant → segmentasyon <b>1,5×</b>; yeni sonuç eski bandın içinde"],
    ["İlk mahalleler", "Ataşehir, Sasalı Merkez, Balatçık, Kaklıç, Küçük Çiğli"],
], [5 * cm, 12 * cm]))
s.append(Spacer(1, 5))
s.append(kutu("<b>Uyarı:</b> Sasalı Merkez doğal sit alanında, Kaklıç askerî havaalanı yakınında — ikisinde de plan kısıtı var, sıralamada bu belirtilmeli."))

s.append(P("6. Doğrulama", h1))
s.append(P("<b>a) PVGIS gerçek tesislerle.</b> İzmir BB'nin 26 GES tesisinden gerçek üretim verisi olan 12'sinin medyanı <b>1.453 kWh/kWp</b>. PVGIS bandı 1.375–1.579; 12 tesisin 8'i bandın içinde. Yan bulgu: belediyenin planlamada kullandığı 1.600 kWh/kWp kabulü iyimser."))
s.append(P("<b>b) Segmentasyon doğruluğu.</b> 109 çatılık tabakalı örneklem (çekim × alan sınıfı × oturtma bandı) görsel olarak denetlendi. Tabaka ağırlıklı doğruluk: belirsizler hata sayılırsa <b>%82,3</b>, belirsizler hariç <b>%90,6</b>."))
s.append(tablo([
    ["Alt grup", "Doğruluk", "Yorum"],
    ["Oturtma oranı ≥ 0,4", "%87,9", "Toplamlar bu gruptan hesaplanır"],
    ["Oturtma oranı < 0,4", "%17,1", "Filtre gerçekten çalışıyor → dışlanır"],
    ["Kiremit çatı", "%95,9", "Güçlü"],
    ["Düz / teras", "%61,5", "Zayıf halka — ayırt edilemeyen düz parseller"],
    ["&lt;150 m² bina", "%72,6", "Küçük binada oturtma hassas"],
], [5 * cm, 2.6 * cm, 9.4 * cm]))
s.append(Spacer(1, 5))
s.append(kutu("<b>Dürüst sunum:</b> Bu örneklem insan değil model destekli bir denetimle notlandırıldı. Toplantıda “ön doğrulama” olarak sunulmalı. Bağımsız notlandırma düzeneği hazır: <i>notebooks/dogrulama/</i> altındaki 10 sayfa, <i>ornek.csv</i>'deki not sütunu doldurulup metrik betiği yeniden koşulur."))

s.append(P("7. Toplumsal önceliklendirme", h1))
s.append(tablo([
    ["Eksen", "Ağırlık", "İçerik"],
    ["Teknik", "0,50", "Mahallenin üretim potansiyeli"],
    ["İhtiyaç", "0,35", "Askıda fatura başvurusu (0,40) · kişi başı su tüketiminin tersi (0,40) · TÜİK SES 2023'ün tersi (0,20)"],
    ["Erişim", "0,15", "Kamu binası çatı alanı"],
], [3 * cm, 2 * cm, 12 * cm]))
s.append(Spacer(1, 4))
s += B([
    "<b>Sıra tabanlı yüzdelik</b> normalizasyon: min-max'te tek bir dev bina tüm skalayı ele geçiriyordu.",
    "<b>Duyarlılık:</b> 4 ağırlık seti (yalnız teknik, AHP benzeri, ihtiyaç ağırlıklı, eşit). Yalnız teknik ↔ AHP sıralaması Kendall tau <b>−0,11</b> — toplumsal katman sıralamayı gerçekten değiştiriyor. Örnek: Sasalı Merkez yalnız teknikte 1., AHP ile 10.",
    "<b>Kamu binası ayrı eksende:</b> askıda fatura ↔ kamu binası yoğunluğu Spearman ρ = −0,47; aynı terimde olsaydı yatırımı ihtiyaçlı mahalleden uzaklaştırırdı.",
])
s.append(kutu("<b>Bilinen açık:</b> Ağırlıklar şu an “AHP benzeri”; uzman ikili karşılaştırma matrisinden türetilmedi ve tutarlılık oranı (CR) hesaplanmadı (n=4 için RI = 0,90, hedef CR ≤ 0,08). Danışmana “ikili karşılaştırmayı sizinle / uzman görüşüyle yapmak istiyoruz” önerisi götürülebilir."))

s.append(P("8. Kütüphaneler ve ortam", h1))
s.append(tablo([
    ["Alan", "Kütüphane"],
    ["Derin öğrenme", "torch (PyTorch), segment_anything (Meta)"],
    ["Görüntü işleme", "opencv-python (cv2), Pillow, numpy"],
    ["Coğrafi işlem", "shapely (poligon işlemleri, STRtree mekânsal indeks), geopandas"],
    ["Veri ve grafik", "pandas, matplotlib"],
    ["Harita", "folium (Leaflet tabanlı)"],
    ["Dış servisler", "requests (PVGIS, Overpass, Esri); pvlib (güneş konumu, NOAA ile 0,01° uyumlu)"],
    ["Ortam", "Google Colab, NVIDIA T4 GPU, Jupyter defteri"],
], [4 * cm, 13 * cm]))

s.append(P("9. Veri kaynakları ve literatür", h1))
s.append(tablo([
    ["Veri", "Kaynak"],
    ["Uydu görüntüsü", "Esri World Imagery — Maxar Legion LG03/LG05/LG02 ve WorldView-2, Ekim 2025 – Şubat 2026, 0,23–0,5 m/piksel"],
    ["Bina ayak izi, kamu binaları", "OpenStreetMap (Overpass API)"],
    ["Güneş üretimi", "PVGIS (JRC)"],
    ["Gerçek GES doğrulaması", "İzmir Büyükşehir lisanssız GES verisi (26 tesis)"],
    ["Toplumsal ihtiyaç", "İzmir Açık Veri (askıda fatura, su tüketimi, nüfus); TÜİK SES 2023 (Çiğli 148,13 — İzmir'de 7./30); SEGE 2022"],
    ["Politika", "İzmir Bölge Planı 2024–2028 (Tedbir 1.4.1); İzmir SECAP"],
    ["Literatür", "Kirillov vd. 2023, <i>Segment Anything</i> (arXiv 2304.02643) · SolarSAM, <i>Renewable Energy</i> 2024, doi 10.1016/j.renene.2024.120156 · Sunter vd. 2019, <i>Nature Sustainability</i>, doi 10.1038/s41893-018-0204-z · Saaty, AHP"],
], [4.2 * cm, 12.8 * cm]))

s.append(P("10. Olası sorular ve kısa cevaplar", h1))
QA = [
    ("Modeli siz mi eğittiniz?", "Hayır. SAM'i önceden eğitilmiş ağırlıklarla zero-shot kullandık. Katkımız istem tasarımında (OSM kutusu) ve SAM'in etrafına kurduğumuz boru hattında: oturtma, tip tespiti, gölge, üretim."),
    ("Çatı eğimini nasıl buldunuz?", "Tek görüntüden güvenilir bulunamıyor. Fotometrik eğim denendi, dağılımı çok geniş çıktı. Eğimli çatılar için 17–33° bant kullanıyoruz; belirsizlik sonuçta bant olarak görünüyor."),
    ("Gölgeyi nasıl hesaba kattınız?", "Bina yüksekliğini gölge boyundan ölçtük, GPU'da yıl boyunca 279 güneş konumu için ışın izleme yaptık. Medyan kayıp %1,2, ortalama %6,2. PVGIS yalnız arazi gölgesini bilir, bina gölgesini biz ekledik."),
    ("Görüntü çözünürlüğü yeterli mi?", "0,23–0,34 m/piksel, ticari uydu görüntüsünün pratik tavanına yakın. Doğrulamada asıl hata kaynağı çözünürlük değil, oturtma kayması ve düz çatı belirsizliği çıktı."),
    ("Görüntü lisansı?", "Esri görüntüsü akademik teknik deneme olarak kullanıldı; tezde açıkça yazılacak. İzmir Açık Veri'de ortofoto olmadığını kontrol ettik."),
    ("Neden Çiğli?", "Mahalleler arası ihtiyaç farkı büyük (varyasyon katsayısı 0,52). Teknik potansiyel ile ihtiyaç ters ilişkili (Spearman −0,44) — tezin savunduğu çarpıklık burada görünüyor. Karşıyaka'da bu ilişki yalnız −0,10."),
    ("Sonuçlar ne kadar güvenilir?", "“Kesin sonuç” değil “ön model” olarak sunuyoruz: şüpheli çatılar ayrı, her sayı bant, doğrulama iki bağımsız yoldan (gerçek GES + görsel örneklem)."),
    ("Eksikler neler?", "EPDK sözleşme gücü tavanı henüz uygulanmadı (potansiyel bir miktar abartılı olabilir) · AHP için CR hesaplanmadı · bağımsız insan doğrulaması yok · “Merkezi Kütüphane” 34.346 m² tek çatı anomalisi kontrol edilmedi."),
]
for a, b_ in QA:
    s.append(KeepTogether([P("S: " + a, q), P(b_, body)]))

s.append(Spacer(1, 8))
s.append(kutu("<b>Toplantı stratejisi:</b> Eksikleri kendiniz söyleyin — “bunun farkında mısınız” sorusundan önce söylemek güçlü durur. Savunulabilir üç güçlü nokta: <b>(1)</b> belirsizliği bant olarak ölçmek, <b>(2)</b> 0,4 oturtma filtresinin doğrulamayla kanıtlanmış etkisi (%17 ↔ %88), <b>(3)</b> toplumsal katmanın sıralamayı gerçekten değiştirmesi (tau −0,11).",
              bg=LIGHT, bar=TEAL))

doc.build(s)
print("ok")
