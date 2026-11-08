# -*- coding: utf-8 -*-
import re, os, glob, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, PageBreak, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("SG", F + r"\segoeui.ttf"))
pdfmetrics.registerFont(TTFont("SGB", F + r"\segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("SGI", F + r"\segoeuii.ttf"))
pdfmetrics.registerFont(TTFont("SGBI", F + r"\segoeuiz.ttf"))
pdfmetrics.registerFontFamily("SG", normal="SG", bold="SGB", italic="SGI", boldItalic="SGBI")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\Users\dmrta\Desktop\Kaynaklar\Cati_Gunes_Literatur_Analizi_Raporu.pdf"

TEAL = colors.HexColor("#0E6B67"); INK = colors.HexColor("#1D2327"); MUTED = colors.HexColor("#5B6770")
LIGHT = colors.HexColor("#EEF4F3"); AMBER = colors.HexColor("#B86E00"); WARN = colors.HexColor("#FFF4E0")
LINE = colors.HexColor("#C9D3D6"); RED = colors.HexColor("#A33A2A"); REDBG = colors.HexColor("#FBECE9")

body = ParagraphStyle("b", fontName="SG", fontSize=8.9, leading=12.4, textColor=INK, spaceAfter=3)
small = ParagraphStyle("s", parent=body, fontSize=8.1, leading=11)
cell = ParagraphStyle("c", parent=body, fontSize=7.6, leading=9.8, spaceAfter=0)
cellh = ParagraphStyle("ch", parent=cell, fontName="SGB", textColor=colors.white)
h1 = ParagraphStyle("h1", fontName="SGB", fontSize=15, leading=19, textColor=TEAL, spaceBefore=4, spaceAfter=8)
h2 = ParagraphStyle("h2", fontName="SGB", fontSize=11.5, leading=14.5, textColor=INK, spaceBefore=10, spaceAfter=4)
h3 = ParagraphStyle("h3", fontName="SGB", fontSize=9.4, leading=12, textColor=TEAL, spaceBefore=5, spaceAfter=1, keepWithNext=1)
bullet = ParagraphStyle("bl", parent=body, leftIndent=11, bulletIndent=2, spaceAfter=1.5)
kunye = ParagraphStyle("k", parent=small, textColor=MUTED, spaceAfter=4)
toc1 = ParagraphStyle("t1", fontName="SGB", fontSize=9.5, leading=13, leftIndent=0)
toc2 = ParagraphStyle("t2", fontName="SG", fontSize=8.6, leading=11.2, leftIndent=14, textColor=INK)


def esc(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("⊃", "›")
    return s


def P(t, st=body):
    return Paragraph(t, st)


def tablo(rows, widths, head=True, zebra=True, fs=None):
    st_c = cell if fs is None else ParagraphStyle("cx", parent=cell, fontSize=fs, leading=fs * 1.3)
    data = []
    for i, r in enumerate(rows):
        data.append([P(c, cellh if (head and i == 0) else st_c) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    s = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
         ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
         ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if head:
        s.append(("BACKGROUND", (0, 0), (-1, 0), TEAL))
    if zebra:
        for i in range(1 if head else 0, len(data)):
            if i % 2 == 0:
                s.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(s))
    return t


def kutu(t, bg=WARN, bar=AMBER):
    x = Table([[P(t, small)]], colWidths=[17 * cm])
    x.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return x


# ---------------------------------------------------------------- notları oku
ETIKET = {"KUNYE": "Künye", "TEMA": "Projeyle ilişkisi", "AMAC": "Amaç", "YONTEM": "Yöntem",
          "MODEL/TEKNOLOJI": "Kullanılan model ve teknolojiler", "VERI": "Kullanılan veriler",
          "BULGULAR": "Bulgular", "EKSIKLER": "Eksik yanlar ve sınırlılıklar",
          "BIZIM PROJEYE": "Projemize alınması gerekenler", "SINIRLAR": "Sınırlılıklar (yazarların kendi ifadesi)",
          "HIPOTEZLER": "Hipotezler", "GÖSTERGELER": "Göstergeler", "VERI ÇIKTISI": "Çıktılar",
          "POLİTİKA ÖRNEKLERİ": "Politika örnekleri", "DÜZELTME": "Düzeltme",
          "KAVRAMSAL ÇERÇEVE": "Kavramsal çerçeve", "BULGULAR/İLKELER": "Bulgular ve ilkeler",
          "GÖSTERGELER VE TÜRKİYE KAYNAKLARI": "Göstergeler ve Türkiye'deki veri kaynakları"}
LAB = re.compile(r"^([A-ZÇĞİÖŞÜ]{3,}[^:]{0,140}?):\s?(.*)$")


def etiket_adi(raw):
    base = re.split(r"\s*[\(—]", raw)[0].strip()
    ek = raw[len(base):].strip()
    ad = ETIKET.get(base, base.capitalize())
    if base == "KUNYE" and ek:
        ad = "Künye " + ek
    elif ek and base not in ("KUNYE",):
        ek2 = ek.strip(" —")
        if ek2:
            ad = ad + " " + (ek2 if ek2.startswith("(") else "— " + ek2.lower())
    return ad


def notu_oku(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    title = lines[0].lstrip("# ").strip()
    secs = []  # (etiket, [öğeler]) öğe: ('p'|'b', metin)
    cur = None
    for ln in lines[1:]:
        s = ln.rstrip()
        if not s.strip():
            continue
        m = LAB.match(s) if not s.lstrip().startswith(("-", "+")) and not re.match(r"^\s*\d+\.", s) else None
        if m and m.group(1).split()[0].upper() == m.group(1).split()[0]:
            cur = [etiket_adi(m.group(1)), []]
            secs.append(cur)
            if m.group(2).strip():
                cur[1].append(("p", m.group(2).strip()))
        else:
            if cur is None:
                cur = ["", []]; secs.append(cur)
            t = s.strip()
            if t.startswith("- ") or t.startswith("+ "):
                cur[1].append(("b", t[2:]))
            elif re.match(r"^\d+\.\s", t):
                cur[1].append(("b", t))
            else:
                cur[1].append(("p", t))
    return title, secs


def vurgu(t):
    t = esc(t.replace("!!! ", ""))
    # BÜYÜK HARFLİ vurguları kalın yap (en az 2 kelime ya da 5+ harf)
    KISA = {"SAM", "PVGIS", "OSM", "PCA", "AHP", "OECD", "JRC", "EPDK", "TÜİK", "İBB", "SECAP", "GES", "NASA", "NREL",
            "CNN", "DSM", "DTM", "LST", "ADNKS", "SEGE", "GYKA", "MEPI", "OWA", "GAZBİR", "İZMİRGAZ", "OSB", "ABD", "LLM",
            "JSON", "ESM", "CAMS", "RID", "RID2", "GIS", "CBS", "MGM", "BTK", "MEB", "İŞKUR", "SKDM", "EPİAŞ", "ÇKKV", "ODTÜ",
            "ECMWF", "ERA5", "TMY", "LCOE", "SILC", "LISA", "LIHC", "IDAE", "CLIP", "ASPP", "FPN", "BIPV", "IEEE", "ICCV",
            "YEKDEM", "MSG", "LOD2", "LOD4", "SEVI", "EVI", "WLC", "HDD", "CDD", "KMO", "SVF", "CPC", "RMSE", "MAE", "UTF",
            "GRASS", "QGIS", "CVAT", "SPA", "NOAA", "GEE", "EEG", "WACC", "HVAC", "SCOPUS", "PRISMA", "DAC", "LMI", "ACS",
            "REPLICA", "USD", "CRS", "DEM", "GHSL", "CORINE", "PDOK", "SARAH", "GPU", "CPU", "IRENA", "WHU", "UAV", "TAI"}

    def rep(m):
        g = m.group(1)
        if g in KISA or len(g.replace(" ", "")) < 5:
            return g
        return "<b>%s</b>" % g
    t = re.sub(r"(?<![\w&#])([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9'’\-]{2,}(?:\s+[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9'’\-]{1,})*)(?![\w;])", rep, t)
    return t


# ---------------------------------------------------------------- belge
class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and getattr(fl, "_toc", None):
            lvl, txt = fl._toc
            key = "k%s" % id(fl)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(re.sub("<[^>]+>", "", txt), key, level=lvl, closed=lvl > 0)
            self.notify("TOCEntry", (lvl, re.sub("<[^>]+>", "", txt), self.page, key))


def baslik(t, lvl=0):
    p = P(t, h1 if lvl == 0 else h2)
    p._toc = (lvl, t)
    return p


def sayfa(c, d):
    c.saveState(); c.setFont("SG", 7.2); c.setFillColor(MUTED)
    if d.page > 1:
        c.drawString(2 * cm, 1.15 * cm, "Çatı Güneş Paneli Uygunluk Analizi ve Toplumsal Öncelik KDS — Literatür Analizi Raporu")
        c.drawRightString(19 * cm, 1.15 * cm, str(d.page))
        c.setStrokeColor(TEAL); c.setLineWidth(1.6); c.line(2 * cm, 28.3 * cm, 19 * cm, 28.3 * cm)
    c.restoreState()


doc = Doc(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.7 * cm,
          title="Çatı Güneş Paneli Projesi — Literatür Analizi Raporu", author="Çatı Güneş Paneli proje ekibi (Claude ile)")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(2 * cm, 1.7 * cm, 17 * cm, 26.3 * cm)], onPage=sayfa)])

S = []
# ---------------------------------------------------------------- kapak
S.append(Spacer(1, 3.2 * cm))
S.append(P("LİTERATÜR ANALİZİ RAPORU", ParagraphStyle("kk", fontName="SGB", fontSize=10, textColor=TEAL, leading=13)))
S.append(Spacer(1, 6))
S.append(P("Çatı Güneş Paneli Uygunluk Analizi ve<br/>Toplumsal Öncelik Karar Destek Sistemi",
           ParagraphStyle("kt", fontName="SGB", fontSize=22, leading=28, textColor=INK)))
S.append(Spacer(1, 10))
S.append(P("27 kaynağın tek tek incelenmesi: amaçlar, yöntemler, kullanılan model ve teknolojiler, veriler, "
           "eksik yanlar ve bitirme projesine alınması gerekenler — karşılaştırmalı sentez, özgünlük analizi ve öncelikli eylem listesiyle",
           ParagraphStyle("ks", parent=body, fontSize=11, leading=15, textColor=MUTED)))
S.append(Spacer(1, 1.2 * cm))
S.append(tablo([["Pilot bölge", "İzmir / Çiğli (26 mahalle + Atatürk OSB)"],
                ["İncelenen kaynak", "26 kaynak tam metin + 1 kaynak (Farsça) özet düzeyinde; 8 ek kaynak önerisi"],
                ["Kaynak klasörü", "Masaüstü\\Kaynaklar"],
                ["Hazırlanma tarihi", "30 Eylül 2026"],
                ["Not", "Her analizdeki sayılar kaynağın kendi metninden alınmıştır. \"Projemize alınması gerekenler\" "
                        "bölümleri projenin mevcut durumuna (17–18 Eylül 2026 tam Çiğli koşusu) göre yazılmış önerilerdir."]],
               [4 * cm, 13 * cm], head=False, zebra=True, fs=8.6))
S.append(PageBreak())

# ---------------------------------------------------------------- içindekiler
S.append(P("İçindekiler", h1))
toc = TableOfContents(); toc.levelStyles = [toc1, toc2]; toc.dotsMinLevel = 0
S.append(toc)
S.append(PageBreak())

# ---------------------------------------------------------------- 1. yönetici özeti
S.append(baslik("1. Yönetici özeti: en önemli 12 bulgu"))
ozet = [
    ("Yöntemimizin neredeyse aynısı yakın zamanda yayımlandı.",
     "Pino-Gallardo vd. (Haziran 2026, Valencia) bina ayak izinden otomatik KUTU istemiyle SAM kullanıp PVGIS API ile üretim hesaplıyor ve mahalle bazında raporluyor. "
     "Tezde \"ilk kez kutu istemi kullandık\" denmemeli. Doğru konumlandırma: aynı istem stratejisini LiDAR olmayan bir bağlamda, ince ayar yapmadan, "
     "gölgeden yükseklik + binalar arası gölge ekleyerek ve toplumsal öncelik katmanıyla genişlettik. Bu aynı zamanda yöntemimizi meşrulaştırıyor."),
    ("Toplumsal katmanla birleştiren tasarımın en yakın emsali RT4ES (Padova, 2026).",
     "Uygunluk + kırılganlık endeksiyle öncelik mimarisi bizimkiyle aynı; ama LiDAR'a dayanıyor, kentsel birim ölçeğinde, ağırlıkları uzman kanaati ve duyarlılık analizi yok. "
     "Bizim farkımız: LiDAR'sız, bina + mahalle ölçeği, sıra tabanlı normalizasyon, Kendall tau duyarlılığı, planlanan AHP + tutarlılık oranı."),
    ("Potansiyel tahminimiz literatüre göre iyimser tarafta.",
     "Brüt çatı m² başına kurulu güç bizde 0,069–0,091 kWp/m²; Ember Türkiye geneli 0,043; engelleri ve teknik filtreleri uygulayan Valencia çalışması 0,009; "
     "büyük binalarda fiilî kurulum ayak izinin ~%20'si (Wussow). Fark: çatı üstü engeller (güneş kollektörü, su deposu, asansör kulesi) düşülmüyor, "
     "minimum alan/yön/ışınım filtreleri yok, kullanılabilir alan katsayıları yüksek. Bir \"sıkı filtre\" senaryosu hesaplanmalı."),
    ("Doğrulamamızda IoU yok; hakemler bunu soracak.",
     "Literatürde segmentasyon IoU ile raporlanıyor (SolarSAM 0,29–0,36; Valencia hazır SAM 0,13 → ince ayarlı 0,52; eğitilmiş U-Net 0,88). "
     "Bizim %82–91 \"doğru\" oranı görsel sınıflamadır. 109 çatılık örneklemde elle çizilmiş poligonlarla piksel IoU ölçülmeli ve ikinci bağımsız notlandırıcı eklenmeli (RID yöntemi)."),
    ("Kutu istemi uydu çözünürlüğünde sınırı aşma eğiliminde.",
     "Osco vd. (2023): bina/evde kutu en iyi istem ama 0,3–0,5 m uyduda kutu taşıyor, nokta daha iyi; 30 cm'nin üstünde başarı düşüyor. "
     "Bizim \"SAM ∩ oturtulmuş ayak izi\" kesişimimiz tam bu taşmayı düzeltiyor — tezde bu bağla gerekçelendirilmeli."),
    ("Ayak izini çatıya \"oturtma\" adımımızın yayımlanmış karşılığı var.",
     "Ni vd. (2024, Şanghay) ayak izini bina yüksekliğine göre kaydırıp çatı çizgisine oturtuyor. Bizim ek katkımız: yüksekliği OSM kat sayısından değil gölge boyundan ölçmek "
     "ve güneş azimutunu gölgelerden bulmak (Chaudhry vd. çekim saatini bilmediği için bunu yapamıyor)."),
    ("Belirsizliği bant olarak vermek literatürde en iyi uygulama.",
     "Walch vd. (2020) LiDAR ile bile ±%37 belirsizlik raporluyor; yıllık ışınım değişkenliği tek başına ±%18. Mainzer'in azimut hataları simetrik ve toplamda sönümleniyor. "
     "Bizim 1,42× bandımız ve \"bina değil mahalle bazında raporla\" ilkemiz bu literatürle savunulabilir."),
    ("Kamu binası ekseninin en güçlü dayanağı Nature Energy'de.",
     "Wussow vd. (2024): dezavantajlı topluluklarda konut güneşi %67, konut dışı (okul, hastane, itfaiye, kamu) %38 daha az — konut dışı çatılar eşitsizliği azaltmada daha etkili kaldıraç; "
     "bataryalı kamu çatısı afet/kesintide kritik hizmet sürekliliği sağlıyor. İzmir deprem bağlamında güçlü argüman."),
    ("Sorun çatıda değil erişimde.",
     "Reames (2020): düşük gelirli bölgelerin çatı potansiyeli düşük değil, kurulum düşük. Sunter (2019): eşitsizlik \"kurulu / teknik potansiyel\" oranıyla ölçülmeli. "
     "Bizim teknik potansiyel haritamız bu oranın paydasını üretiyor; mevcut GES verisi eklenirse eşitsizlik doğrudan ölçülebilir."),
    ("İhtiyaç endeksi için Türkiye'de hakemli gösterge seti ve veri kaynakları var.",
     "Değirmenci & Limanlı (2025): ısınmada geleneksel yakıt, konut sorunu, yalıtım, fatura ödeyememe, yeterli ısınamama (Alkire-Foster). "
     "Korkmaz (2024, ODTÜ): TÜİK, GAZBİR, MGM derece-gün, BTK, İŞKUR kaynaklı 15 gösterge. Mahalle karşılıkları: İZMİRGAZ abonelik, askıda fatura, yaş yapısı, bina yaşı. "
     "\"Parasal yoksulluk ≠ enerji yoksulluğu\" bulgusu emlak/servet göstergesine itirazı destekliyor."),
    ("Bileşik endeksin standart yöntemi OECD/JRC 10 adımı.",
     "\"Ağırlıklar özünde değer yargısıdır\"; sıra (rank) normalizasyonu aykırı değere dayanıklı; eşit ağırlıkta boyut içi gösterge sayısı ve çift sayım tuzakları; "
     "belirsizlik/duyarlılık analizi zorunlu. İhtiyaç endeksi ve öncelik skoru bu 10 adıma göre belgelenmeli."),
    ("LLM için yayımlanmış bir istem tasarımı ve risk kanıtı var.",
     "Liu vd. (2025): LLM'e görüntü değil yapılandırılmış metin (JSON) veriliyor, adım adım istem zinciri; aynı girdide ±%4,2 tutarsızlık, geçerli JSON için ortalama 3–5 istek, "
     "kurallar silinince hatalı çıktı. Bu, \"LLM karar vermez, formülün çıktısını açıklar\" mimarimizin doğrudan kanıtı."),
]
for i, (b, t) in enumerate(ozet, 1):
    S.append(KeepTogether([P("<b>%d. %s</b>" % (i, esc(b)), ParagraphStyle("oz", parent=body, textColor=TEAL, spaceAfter=1, spaceBefore=3)),
                           P(esc(t), body)]))

# ---------------------------------------------------------------- 2. kapsam ve yöntem
S.append(PageBreak())
S.append(baslik("2. Raporun kapsamı ve inceleme yöntemi"))
S.append(P("Masaüstündeki <i>Kaynaklar</i> klasöründeki 26 PDF/Word dosyası ile masaüstündeki ODTÜ tezi metne çevrilerek tek tek okundu. "
           "Her kaynak için aynı şablon uygulandı: <b>künye</b>, <b>projeyle ilişkisi</b>, <b>amaç</b>, <b>yöntem</b>, <b>kullanılan model ve teknolojiler</b>, "
           "<b>kullanılan veriler</b>, <b>bulgular</b>, <b>eksik yanlar</b> ve <b>projemize alınması gerekenler</b>. Kaynakların yazarlarının kendi belirttiği sınırlılıklar ile "
           "bizim gözlemimizle tespit edilen eksikler ayrıştırılmaya çalışıldı. Sayısal değerler kaynağın metninden aktarıldı; hesaplanan karşılaştırmalar (ör. kWp/m²) "
           "açıkça \"hesaplanan\" diye belirtildi."))
S.append(P("Kapsam dışı bırakılanlar: masaüstündeki <i>s11207-025-02424-0.pdf</i> (Solar Physics dergisinde astrofizik makalesi, projeyle ilgisiz) ve "
           "Cell Press arşivindeki DeepSolar dışındaki 22 makale (derginin aynı sayısından, konu dışı). Farsça olan Shirzad vd. (2019) makalesi yalnız İngilizce özet "
           "ve dergi sayfası üzerinden değerlendirildi. Okuma listesindeki 13 temel kaynağın (SolarSAM, SAM, PVGIS, GEPA, Sunter, AHP, SEGE, SECAP, EPDK, OSM) "
           "12 Eylül 2026 tarihli ayrı analizi <i>cati_projesi_kaynak_analizi.pdf</i> dosyasındadır; bu rapor onu tekrar etmez, tamamlar."))
S.append(kutu("<b>Okuma önerisi:</b> Zaman kısıtlıysa önce Bölüm 1 (özet), Bölüm 5 (karşılaştırmalı sentez), Bölüm 6 (özgünlük) ve Bölüm 7 (eylem listesi) okunmalı. "
              "Bölüm 4'teki kaynak analizleri başvuru amaçlıdır; her kaynağın sonundaki \"Projemize alınması gerekenler\" kısmı en kullanışlı bölümdür.", LIGHT, TEAL))

# ---------------------------------------------------------------- 3. kaynak haritası
TEMALAR = [
    ("A", "Görüntüden çatı PV potansiyeli: yöntem öncülleri", ["01_mainzer", "02_walch", "03_bodis", "11_zhong", "12_lanzhou", "13_ni_sanghay", "14_pino_valencia"]),
    ("B", "Derin öğrenme, temel modeller ve veri setleri", ["07_sam", "06_solarsam", "08_osco", "04_solarnet", "05_rid", "09_golge_yukseklik", "10_cephe_llm", "20_deepsolar"]),
    ("C", "Enerji adaleti ve toplumsal önceliklendirme", ["15_konzen", "19_sunter", "18_reames", "17_wussow", "16_rt4es", "27_shirzad"]),
    ("D", "Enerji yoksulluğu ölçümü ve bileşik göstergeler", ["21_robinson", "22_degirmenci", "23_odtu_korkmaz", "26_oecd"]),
    ("E", "Türkiye bağlamı", ["25_ember", "24_unal"]),
]
HARITA = {
    "01_mainzer": ("Mainzer vd. 2017", "Makale", "Açık veri + görüntü işleme ile bina bazında PV potansiyeli", "Freiburg (DE)", "Yok", "Çok yüksek"),
    "02_walch": ("Walch vd. 2020", "Makale", "Ulusal ölçek, saatlik potansiyel, belirsizlik yayılımı", "İsviçre", "Yok", "Yüksek"),
    "03_bodis": ("Bódis vd. 2019", "Makale (JRC)", "AB çatı potansiyeli, LCOE, PVGIS", "AB-28", "Politika önerisi", "Yüksek"),
    "11_zhong": ("Zhong vd. 2021", "Makale", "DeepLab v3, tabakalı örnekleme, şehir ölçeği", "Nanjing (CN)", "Yok", "Orta"),
    "12_lanzhou": ("Chen vd. 2025", "Makale", "U²-Net, sanayi vs konut, talep eşleştirme", "Lanzhou (CN)", "Yok", "Orta"),
    "13_ni_sanghay": ("Ni vd. 2024", "Makale", "OSM + gölge hacmi + çatı engelleri", "Şanghay (CN)", "Yok", "Çok yüksek"),
    "14_pino_valencia": ("Pino-Gallardo vd. 2026", "Makale", "Ayak izi → kutu istemli SAM + LiDAR + PVGIS", "Valencia (ES)", "Yok", "Çok yüksek"),
    "07_sam": ("Kirillov vd. 2023", "Makale (ICCV)", "Segment Anything modeli", "Genel", "—", "Çok yüksek"),
    "06_solarsam": ("Wang 2024", "Makale", "Metin istemli SAM ile BIPV potansiyeli", "Zibo (CN)", "Yok", "Çok yüksek"),
    "08_osco": ("Osco vd. 2023", "Makale", "SAM'in uzaktan algılamada istem türlerine göre başarımı", "Brezilya + açık veri", "—", "Çok yüksek"),
    "04_solarnet": ("Li vd. 2023", "Makale", "Çatı yüzeyi + yön öğrenen çok görevli ağ", "DE, ABD", "Yok", "Yüksek"),
    "05_rid": ("Krapf vd. 2022", "Makale + veri", "Çatı üstü nesne veri seti, etiket kalitesi", "Wartenberg (DE)", "Yok", "Yüksek"),
    "09_golge_yukseklik": ("Chaudhry vd. 2024", "Ön baskı", "Gölge boyundan bina yüksekliği", "42 Çin şehri", "—", "Yüksek"),
    "10_cephe_llm": ("Liu vd. 2025", "Ön baskı", "SAM + GroundingDINO + LLM ile cephe PV", "4 şehir (Ankara dahil)", "—", "Çok yüksek (LLM)"),
    "20_deepsolar": ("Yu vd. 2018", "Makale (Joule)", "Uydudan mevcut PV tespiti, sosyoekonomik ilişkiler", "ABD", "Kısmen", "Orta"),
    "15_konzen": ("Konzen vd. 2024", "Sistematik derleme", "Konut güneşinde dağıtımsal adaletsizlik (87 çalışma)", "Küresel", "Ana konu", "Yüksek"),
    "19_sunter": ("Sunter vd. 2019", "Makale (Nat. Sust.)", "Kurulumun ırk/etnisiteye göre eşitsizliği", "ABD", "Ana konu", "Yüksek"),
    "18_reames": ("Reames 2020", "Makale", "Potansiyel vs kurulum dağılımı", "4 ABD şehri", "Ana konu", "Yüksek"),
    "17_wussow": ("Wussow vd. 2024", "Makale (Nat. Energy)", "Konut dışı güneş ve enerji adaletsizliği", "ABD", "Ana konu", "Çok yüksek"),
    "16_rt4es": ("Ahmadi vd. 2026", "Makale", "Uygunluk + kırılganlık ile çatı önceliklendirme", "Padova (IT)", "Ana konu", "Çok yüksek"),
    "27_shirzad": ("Shirzad vd. 2019", "Makale (Farsça)", "AHP + OWA ile çatı PV uygunluğu", "Meşhed (IR)", "Yok", "Düşük"),
    "21_robinson": ("Robinson vd. 2018 (a, b)", "2 makale", "Yakıt yoksulluğu göstergelerinin coğrafyası", "İngiltere", "Ana konu", "Yüksek"),
    "22_degirmenci": ("Değirmenci & Limanlı 2025", "Makale", "Türkiye'de çok boyutlu enerji yoksulluğu", "Türkiye", "Ana konu", "Çok yüksek"),
    "23_odtu_korkmaz": ("Korkmaz 2024", "YL tezi (ODTÜ)", "Enerji yoksulluğuna sosyo-mekânsal kırılganlık", "Türkiye (81 il)", "Ana konu", "Yüksek"),
    "26_oecd": ("OECD & JRC 2008", "El kitabı", "Bileşik gösterge oluşturma yöntemi", "Genel", "—", "Çok yüksek"),
    "25_ember": ("Ember 2023", "Rapor", "Türkiye çatı GES teknik potansiyeli", "Türkiye (70 il)", "Politika", "Çok yüksek"),
    "24_unal": ("Ünal 2026", "Proje raporu (ODTÜ)", "Derin öğrenmeyle çatı tespiti ve tip sınıfı", "RID2 + Ankara", "Yok", "Yüksek"),
}
S.append(Spacer(1, 10))
S.append(baslik("3. Kaynak haritası"))
S.append(P("Kaynaklar beş tema altında toplandı. \"Toplumsal boyut\" sütunu kaynağın toplumsal/adalet boyutunu ele alıp almadığını, \"Önem\" sütunu projemiz için değerini gösterir."))
rows = [["No", "Kaynak", "Tür", "Konu", "Bölge / ölçek", "Toplumsal boyut", "Önem"]]
no = 0; NUM = {}
for kod, tema, lst in TEMALAR:
    rows.append(["<b>%s</b>" % kod, "<b>%s</b>" % esc(tema), "", "", "", "", ""])
    for k in lst:
        no += 1; NUM[k] = no
        a = HARITA[k]
        rows.append(["K%d" % no, esc(a[0]), esc(a[1]), esc(a[2]), esc(a[3]), esc(a[4]), esc(a[5])])
t = tablo(rows, [0.9 * cm, 3.2 * cm, 2.1 * cm, 4.9 * cm, 2.5 * cm, 1.7 * cm, 1.7 * cm])
st = []
for i, r in enumerate(rows):
    if r[0].startswith("<b>") and i > 0:
        st += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#D6E6E4")), ("SPAN", (1, i), (-1, i))]
t.setStyle(TableStyle(st))
S.append(t)

# ---------------------------------------------------------------- 4. kaynak analizleri
S.append(PageBreak())
S.append(baslik("4. Kaynakların tek tek analizi"))
S.append(P("Her kaynak aynı şablonla incelendi. Kaynak numaraları (K1–K27) Bölüm 3'teki haritayla aynıdır."))
for kod, tema, lst in TEMALAR:
    S.append(CondPageBreak(5 * cm))
    S.append(baslik("4.%s %s" % (kod, tema), 1))
    for k in lst:
        title, secs = notu_oku(os.path.join(HERE, "notlar", k + ".md"))
        blk = [CondPageBreak(4 * cm),
               P("K%d · %s" % (NUM[k], esc(title)), ParagraphStyle("st", parent=h2, fontSize=10.6, textColor=INK, spaceBefore=12, keepWithNext=1,
                                                                  borderPadding=(3, 0, 3, 0)))]
        S += blk
        for ad, items in secs:
            if ad.startswith("Künye"):
                txt = " ".join(x[1] for x in items)
                S.append(P("<b>%s:</b> %s" % (esc(ad), esc(txt)), kunye))
                continue
            proj = ad.startswith("Projemize")
            fl = []
            if ad:
                fl.append(P(esc(ad), ParagraphStyle("h3x", parent=h3, textColor=(AMBER if proj else TEAL))))
            for typ, x in items:
                if typ == "b":
                    fl.append(Paragraph(vurgu(x), bullet, bulletText="•"))
                else:
                    fl.append(P(vurgu(x)))
            if proj:
                inner = Table([[fl]], colWidths=[17 * cm])
                inner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WARN), ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
                                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
                S.append(inner)
            else:
                S += fl

# ---------------------------------------------------------------- 5. karşılaştırmalı sentez
S.append(PageBreak())
S.append(baslik("5. Karşılaştırmalı sentez"))
S.append(baslik("5.1 Kullanılabilir alan, güç yoğunluğu ve kayıp varsayımları", 1))
S.append(P("Potansiyel tahminini en çok belirleyen varsayımlar kullanılabilir alan oranı ve m² başına kurulu güçtür. Aşağıdaki tablo literatürdeki değerleri bizim modelle karşılaştırır. "
           "\"Brüt yoğunluk\" = toplam kurulu güç / toplam çatı alanı (hesaplanan); çalışmalar arasında tanımlar farklı olduğu için yalnız büyüklük mertebesi karşılaştırılmalıdır."))
S.append(tablo([
    ["Kaynak", "Kullanılabilir alan / filtreler", "Güç yoğunluğu", "Kayıp / verim", "Brüt yoğunluk (kWp/m² çatı)"],
    ["<b>Bizim model (Çiğli)</b>", "Düz 0,55 · eğimli yüz 0,70; oturtma <0,4 hariç; engel ve min alan filtresi yok", "6 m²/kWp (≈167 W/m²)", "PVGIS kayıp %14; gölge × 0,65", "<b>0,069–0,091</b> (383–504 MWp / 5,53 km²)"],
    ["Ember 2023 (Türkiye)", "Uygun çatı %27,6 (Random Forest; dolu çatılar hariç)", "6,4 m²/kW (Türkiye projeleri ort. 6,3)", "Solargis + PVGIS düzeltme", "0,043 (120 GW / 2.800 km²)"],
    ["Pino-Gallardo 2026 (Valencia)", "Engel hariç %48,6 → filtreler sonrası %14,6", "Modül yerleşimi (IDAE aralığı)", "PVGIS", "0,009 (173 MW / 18,4 km²)"],
    ["Wussow 2024 (ABD, büyük bina)", "Fiilî kurulum ayak izinin ~%20'si (%5–29)", "200 W/m²", "—", "~0,040 (hesaplanan)"],
    ["Chen 2025 (Lanzhou)", "Panel yerleşimi: sanayi %62,8, konut %51,2; engel/gölge yok", "η %15 (≈150 W/m²)", "Ek kayıp yok", "~0,077–0,094 (hesaplanan)"],
    ["Walch 2020 (İsviçre)", "Toplam çatının %55–56'sı; büyük düz %70–80, orta boy %30–60; <8 m² ve kuzey hariç", "Panel yerleşimi", "PVWatts, Perez", "—"],
    ["Bódis 2019 (AB)", "%49–64 uygun × %60 ek azaltma", "—", "Kayıp %14; bozulma %0,5/yıl", "—"],
    ["Krapf 2022 (RID)", "Engeller −%15–20; mevcut PV −%29,5", "Eğimli 0,25 kWp/m², düz 0,125", "PVGIS kayıp %14", "—"],
    ["Ni 2024 (Şanghay)", "Engeller %14,9; gölge + engel birlikte −%25,6", "—", "PR 0,80; η %22,5 − %0,28/°C", "—"],
    ["SolarSAM 2024", "K_mapping 0,40–0,80 (bina türüne göre)", "Tutarsız (20,8 W/m²)", "pvlib", "—"],
    ["Mainzer 2017", "Modül yerleşimi + engel tespiti + genel −%30", "Modül bazında", "Doğrusal olmayan modül/evirici modeli", "—"],
    ["RT4ES 2026 (Padova)", "Min 100 m²; kuzey hariç; düz çatıda PV yalnız konut dışı", "0,219 kWp/m² (uygun alanda)", "—", "—"],
], [3.2 * cm, 5.2 * cm, 2.8 * cm, 2.9 * cm, 2.9 * cm], fs=7.3))
S.append(Spacer(1, 5))
S.append(kutu("<b>Yorum:</b> Bizim brüt yoğunluğumuz engel ve filtre uygulamayan Lanzhou çalışmasıyla aynı mertebede; engelleri ve teknik filtreleri uygulayan çalışmalarda "
              "(Ember, Valencia) 2 ile 10 kat daha düşük. Bu, üst sınırımızın (749 GWh/yıl) iyimser olduğunu, alt sınırımızın da (526 GWh/yıl) muhtemelen \"teknik üst potansiyel\" "
              "olarak yorumlanması gerektiğini gösterir. Tezde sonuçlar \"teknik potansiyel (engel ve mevzuat kısıtı öncesi)\" diye adlandırılmalı ve Bölüm 7'deki sıkı filtre senaryosu "
              "ile birlikte raporlanmalıdır. Olumlu tutarlılıklar: 6 m²/kWp değerimiz Türkiye'deki gerçek projelerle (6,3) uyumlu; düz çatının optimuma oranı bizde ~%86, Ember'de %84; "
              "%14 kayıp varsayımı JRC ve RID ile aynı."))
S.append(baslik("5.2 Segmentasyon başarımları", 1))
S.append(P("Segmentasyon başarımı çalışmalar arasında farklı hedef sınıflar, çözünürlükler ve metriklerle raporlanıyor; doğrudan karşılaştırma dikkatle yapılmalıdır."))
S.append(tablo([
    ["Kaynak", "Model / istem", "Görüntü", "Hedef", "Başarım"],
    ["SolarSAM 2024", "SAM + metin istemi (sıfır atış)", "Google Earth uydu", "6 bina türünün çatısı", "IoU 0,29–0,36"],
    ["Osco 2023", "SAM ViT-H, kutu", "İHA 0,04 m", "Ev", "IoU 0,86"],
    ["Osco 2023", "SAM ViT-H, kutu / nokta / metin", "Uydu 0,30 m", "Çok sınıflı (bina, yol…)", "IoU 0,23 / 0,57 / 0,51"],
    ["Pino-Gallardo 2026", "SAM hazır / ince ayarlı, kutu", "Ortofoto 0,25 m", "Engelsiz çatı yüzeyi", "IoU 0,13 → 0,52 (duyarlılık 0,96)"],
    ["Li (SolarNet) 2023", "ResNet34 çok görevli (eğitimli)", "Hava 0,1 m", "Çatı yüzeyi + 4 yön", "mIoU 0,60–0,69; düz çatı IoU 0,35"],
    ["Krapf (RID) 2022", "U-Net / Panoptic FPN", "Hava ~0,1 m", "Çatı üstü nesneler", "mIoU 0,42–0,46 (insanlar arası 0,48; çatı sınırında 0,95)"],
    ["Zhong 2021", "DeepLab v3", "Google Earth 0,25 m", "Çatı", "Doğruluk 0,92; F1 0,80"],
    ["Ni 2024", "DeepLab v3 (ResNet-101)", "Google uydu", "Çatı engelleri", "IoU 0,84"],
    ["Chen 2025", "U²-Net", "ESRI uydu", "Çatı (sanayi / konut)", "maxFβ 0,889 / 0,846"],
    ["Ünal 2026", "U-Net ResNet34", "Hava 0,08 m (RID2)", "Çatı; tip sınıfı", "IoU 0,88; tip doğruluğu %80,8 (düz F1 0,76)"],
    ["Liu 2025", "GroundingDINO + SAM (metin)", "Sokak fotoğrafı", "Cephe elemanları", "mIoU 0,81"],
    ["<b>Bizim model</b>", "SAM ViT-B, OSM kutu istemi + ayak izi kesişimi", "Uydu 0,23–0,34 m (WV02 0,5 m)", "Çatı sınırı + tip", "<b>Görsel denetim: %82,3–90,6 \"doğru\"; IoU ölçülmedi</b>"],
], [3.0 * cm, 4.0 * cm, 3.0 * cm, 3.3 * cm, 3.7 * cm], fs=7.3))
S.append(Spacer(1, 5))
S.append(kutu("<b>Yorum:</b> (1) Hazır SAM'in başarımı hedefin tanımına ve çözünürlüğe çok duyarlı: evde 0,86, uyduda çok sınıflı görevde 0,23, engelsiz yüzey hedefinde 0,13. "
              "(2) Düz çatı her modelde en zor sınıf (SolarNet 0,35; Ünal F1 0,76) — bizim düz/teras doğruluğumuzun %61,5 çıkması literatürle tutarlı. "
              "(3) Karşılaştırılabilirlik için doğrulamaya piksel IoU eklenmesi şart; hedef tanımımız (\"çatı sınırı\") açıkça yazılmalı."))
S.append(baslik("5.3 Önceliklendirme ve ağırlık şemaları", 1))
S.append(tablo([
    ["Kaynak", "Eksenler / göstergeler", "Normalizasyon", "Ağırlık belirleme", "Duyarlılık"],
    ["<b>Bizim model</b>", "Teknik 0,50 · ihtiyaç 0,35 (askıda fatura, su tüketimi, SES) · erişim 0,15 (kamu çatısı)", "Sıra-yüzdelik (ortalama sıra)", "\"AHP benzeri\"; gerçek AHP + CR planlı", "4 ağırlık seti, Kendall tau −0,11"],
    ["RT4ES 2026", "Fiziksel uygunluk 0,25 · çevresel kırılganlık 0,35 (LST, yeşil alan, geçirimsiz yüzey, park) · sosyoekonomik 0,40 (6 gösterge)", "Min-max", "Literatür + uzman tartışması", "Yok"],
    ["Shirzad 2019", "Kullanım 0,141 · üretilen kW 0,483 · potansiyel güç 0,101 · 20 yıllık getiri 0,276", "—", "AHP, 25 uzman; OWA", "—"],
    ["Değirmenci 2025", "Yakıt türü 1/3 · konut sorunu 1/6 · yalıtım 1/6 · mali yük 1/6 · yeterli ısınma 1/6", "İkili yoksunluk", "Normatif; Alkire-Foster çift eşik", "k eşiği 0,50–1,0"],
    ["Korkmaz 2024", "15 kırılganlık göstergesi (il)", "z-skoru", "PCA (4 bileşen, %74,2)", "KMO 0,727"],
    ["Robinson 2018", "%10 ve LIHC yakıt yoksulluğu göstergeleri", "Ondalık", "—", "LISA, GWR"],
    ["Bódis 2019 / Chen 2025", "Yalnız teknik + ekonomik (LCOE; talep)", "—", "—", "—"],
    ["OECD/JRC 2008", "Rehber: 10 adım", "Rank, z, min-max…", "EW, PCA/FA, BOD, BAP, AHP, CA", "Zorunlu (ağırlık, gösterge, normalizasyon)"],
], [2.8 * cm, 6.0 * cm, 2.4 * cm, 3.1 * cm, 2.7 * cm], fs=7.3))
S.append(Spacer(1, 5))
S.append(kutu("<b>Yorum:</b> Toplumsal öncelik kuran tek emsal olan RT4ES sosyal eksene en yüksek ağırlığı veriyor (0,40) ve teknik uygunluğa en düşük (0,25); bizim şema teknik ağırlıklı (0,50). "
              "Uzman anketi yapan Shirzad'da uzmanlar üretim ve getiriyi baskın görüyor — uzman AHP'sinde ihtiyaç ağırlığı düşük çıkabilir; bu yanlılık tezde tartışılmalı. "
              "Duyarlılık analizi yapan tek çalışma bizimki; OECD'nin önerdiği gösterge çıkarma ve alternatif normalizasyon testleri eklenirse bu yön güçlü bir katkı olur."))

# ---------------------------------------------------------------- 6. özgünlük
S.append(PageBreak())
S.append(baslik("6. Literatürdeki boşluk ve projenin özgünlüğü (güncellenmiş)"))
S.append(tablo([
    ["Bileşen", "Literatürde var mı?", "Bizim farkımız"],
    ["Açık ayak izi + görüntü ile LiDAR'sız bina bazında potansiyel", "Evet (Mainzer 2017; Ni 2024; Ember 2023)", "SAM ile piksel düzeyi segmentasyon; Türkiye'de mahalle ölçeği"],
    ["Ayak izinden kutu istemiyle SAM", "EVET — Pino-Gallardo 2026 (ince ayarlı, LiDAR'lı)", "İnce ayarsız, LiDAR'sız, uydu görüntüsüyle; ayak iziyle kesişim + oturtma"],
    ["Ayak izini çatıya oturtma", "Evet (Ni 2024; OSM kat sayısıyla)", "Kayma ve yükseklik gölgelerden ölçülüyor"],
    ["Gölge boyundan yükseklik", "Evet (Chaudhry 2024; saat bilinmiyor, yer gerçeğiyle ayar)", "Güneş azimutu gölgelerden ölçülüyor, çekim bazında güvenilirlik ölçütü"],
    ["Binalar arası yıllık gölge", "Evet, 3B veriyle (Walch, Ni); Valencia'da yok", "3B veri olmadan, ölçülen yükseklikten GPU ışın izleme"],
    ["Belirsizliği bant olarak raporlama", "Evet (Walch 2020)", "LiDAR'sız bir çalışmada eğim/yön belirsizliğini bant olarak taşıma"],
    ["Uygunluk + kırılganlıkla öncelik", "Evet (RT4ES 2026, Padova; LiDAR, kentsel birim)", "Enerji yoksulluğu göstergeleri, bina + mahalle, duyarlılık analizi, AHP + CR"],
    ["Kamu binası ekseni", "Kısmen (Wussow 2024 ABD; Kutlu 2022 Ankara kamu potansiyeli)", "Öncelik skorunda ayrı eksen + EPDK saatlik mahsuplaşma gerekçesi"],
    ["LLM ile açıklama/rapor", "Evet, yerleşim tasarımı için (Liu 2025)", "LLM karar vermez; skor çıktısını açıklar, senaryoyu araç çağrısıyla çalıştırır"],
    ["Türkiye'de uçtan uca (segmentasyon → gölge → PVGIS → toplumsal öncelik)", "Bulunamadı (Ember: teknik/il; Ünal: yalnız geometri; Kutlu: Ankara teknik)", "Bu birleşim Türkiye'de ilk olabilir — tez teslimine yakın DergiPark, YÖK Tez ve Scholar'da son kez kontrol edilmeli"],
], [5.2 * cm, 5.2 * cm, 6.6 * cm], fs=7.5))
S.append(Spacer(1, 6))
S.append(kutu("<b>Tezde kullanılabilecek özgünlük cümlesi:</b> \"Bu çalışma, Pino-Gallardo vd. (2026) tarafından önerilen ayak izi tabanlı kutu istemli SAM segmentasyonunu "
              "LiDAR verisinin bulunmadığı bir bağlama taşımakta; bina yüksekliğini ve güneş konumunu uydu görüntüsündeki gölgelerden ölçerek binalar arası gölgelenmeyi hesaba katmakta "
              "ve elde edilen teknik potansiyeli, Ahmadi vd. (2026)'nın uygunluk–kırılganlık yaklaşımına benzer biçimde, enerji yoksulluğu ve kamu binası erişimi eksenleriyle "
              "birleştirerek mahalle ölçeğinde bir karar destek sistemine dönüştürmektedir. Türkiye için bu bileşimin ilk uygulamalarından biridir.\"", LIGHT, TEAL))

# ---------------------------------------------------------------- 7. eylem listesi
S.append(PageBreak())
S.append(baslik("7. Projeye alınması gerekenler: öncelikli eylem listesi"))
S.append(P("Kaynak analizlerinden çıkan öneriler tek listede toplandı. Öncelik: <b>A</b> = tez teslimine kadar mutlaka, <b>B</b> = güçlü önerilir, <b>C</b> = ileri çalışma."))
act = [["#", "Eylem", "Dayanak kaynaklar", "Katman", "Öncelik"],
       ["1", "Doğrulamaya piksel IoU ölçümü ekle (109 çatıda elle çizilmiş poligon ↔ model); ikinci bağımsız notlandırıcı ve Cohen kappa", "Krapf 2022, Pino-Gallardo 2026, Liu 2025", "Teknik", "A"],
       ["2", "\"Sıkı filtre\" senaryosu: min alan 10 m², eğimli çatıda kuzeye bakan yüzeyleri ele, 0,6 m bakım koridoru (içe tampon), yüksekliği <5 m olanları ele, yüksek gölgeli alanları ele", "Pino-Gallardo 2026, Walch 2020, RT4ES 2026", "Teknik", "A"],
       ["3", "Kullanılabilir alan katsayıları için duyarlılık: bina türüne göre (SolarSAM K_mapping), alan sınıfına göre (Walch), %10/25/40 senaryosu (Wussow)", "Wang 2024, Walch 2020, Wussow 2024", "Teknik", "A"],
       ["4", "EPDK sözleşme gücü tavanını uygula: kapasite = min(alan tabanlı, tavan)", "Wussow 2024 (fiilî ~%20); EPDK md. 5/1-h", "Teknik", "A"],
       ["5", "Çatı üstü engeller (güneş kollektörü, su deposu, asansör kulesi) için belirsizlik payı (−%15 ile −%25) ve sınırlılık notu", "Krapf 2022, Ni 2024, Ember 2023", "Teknik", "A"],
       ["6", "OSB tip sınıflaması düzeltmesi: >3.000 m² çatıları düz kabul et ya da OSB'de kiremit sınıfını sac çatı say", "Mainzer 2017, Ünal 2026", "Teknik", "B"],
       ["7", "Ember (İzmir 9,3 GW / 12,4 TWh) ve Kutlu 2022 (Ankara) ile çapraz karşılaştırma tablosu; Microsoft ayak izi abartısı tartışması", "Ember 2023, Kutlu 2022", "Teknik / tez", "A"],
       ["8", "Mevcut GES tespiti (İBB listesi + görüntüden) → mahalle bazında kurulu / teknik potansiyel oranı", "Sunter 2019, Reames 2020, Yu 2018, Mainzer 2017", "Toplumsal", "B"],
       ["9", "İhtiyaç endeksini OECD 10 adımına göre kur: askıda fatura, İZMİRGAZ abonelik oranı, 65+ ve 0–4 yaş payı, bina yaşı, (varsa) fatura gecikme; eşit ağırlıklı veya Alkire-Foster; opsiyonel yüzey sıcaklığı (LST)", "OECD 2008, Değirmenci 2025, Korkmaz 2024, Robinson 2018, RT4ES 2026", "Toplumsal", "A"],
       ["10", "Gerçek AHP: danışman + 2–3 uzman ikili karşılaştırma, CR ≤ 0,08 raporla; uzman yanlılığını tartış", "OECD 2008, Shirzad 2019", "Toplumsal", "A"],
       ["11", "Duyarlılık analizini genişlet: RT4ES tipi ağırlık seti, Borda toplamı, gösterge çıkarma testi, korelasyonlara bootstrap güven aralığı", "OECD 2008, RT4ES 2026, Sunter 2019, Wussow 2024", "Toplumsal", "B"],
       ["12", "Kamu ekseni gerekçesini genişlet: konut dışı çatının eşitsizlik azaltma etkisi + afet/kesinti dayanıklılığı (bataryalı kamu çatısı)", "Wussow 2024, Ember 2023", "Toplumsal / tez", "B"],
       ["13", "LLM modülü: skor çıktısını JSON olarak ver, adım adım istem zinciri, şema doğrulama + yeniden deneme, rakam tutarlılık kontrolü, iki LLM karşılaştırması, istem ablasyonu", "Liu 2025", "LLM", "A"],
       ["14", "LLM öneri kütüphanesi: apartman ortak çatısı/sanal mahsuplaşma, belediye destekli ön ödemesiz model, deprem sonrası çatı kiralama, muhtarlık üzerinden bilgilendirme, \"tohum\" kamu GES'i", "Ember 2023, Tice 2023, Reames 2020, Sunter 2019, Konzen 2024", "LLM / politika", "B"],
       ["15", "Özgünlük cümlesini Pino-Gallardo 2026 ve RT4ES'e göre güncelle (Bölüm 6)", "Pino-Gallardo 2026, Ahmadi 2026", "Tez", "A"],
       ["16", "Kuramsal çerçeve: enerji adaleti boyutları (dağıtımsal, tanınma, usul) ve enerji yoksulluğu tanımı", "Konzen 2024, Robinson 2018, Değirmenci 2025", "Tez", "A"],
       ["17", "Sınırlılıklar bölümü: ekolojik yanılgı, 30 cm çözünürlük eşiği, yıllık ışınım değişkenliği ±%18, gölge ve engel etkisinin toplanamazlığı, Türkiye'de enerji yoksulluğu tanımı ve çatı GES istatistiği olmaması", "Robinson 2018, Osco 2023, Walch 2020, Ni 2024, Değirmenci 2025, Ember 2023", "Tez", "A"],
       ["18", "Harita dosyasını Ramer-Douglas-Peucker ile sadeleştir (GeoJSON ~%70 küçülme)", "Ünal 2026", "Teknik", "C"],
       ["19", "Kutu + merkez noktası birlikte istem ve SAM'in 3 maskesinden ayak iziyle en uyumlusunu seçme denemesi (özellikle <150 m² çatılar)", "Osco 2023, Kirillov 2023", "Teknik", "C"],
       ["20", "Eğitilmiş çatı tipi sınıflayıcı (EfficientNetB0; Ankara + Çiğli etiketleri) ile kural tabanlı tip ayrımını karşılaştır", "Ünal 2026", "Teknik", "C"],
       ]
S.append(tablo(act, [0.7 * cm, 8.4 * cm, 4.6 * cm, 2.0 * cm, 1.3 * cm], fs=7.3))

# ---------------------------------------------------------------- 8. düzeltmeler
S.append(PageBreak())
S.append(baslik("8. Önceki değerlendirmelerimdeki düzeltmeler"))
S.append(P("Bu rapor sırasında tam metinler okununca, daha önce sohbette verdiğim bazı bilgilerin eksik veya hatalı olduğu görüldü:"))
dz = [
    ("Osco vd. (2023) kutu istemini koşulsuz desteklemiyor.", "Daha önce \"kutu istemi tercihinin ikinci bağımsız dayanağı\" demiştim. Doğrusu: kutu istemi yüksek çözünürlükte ev/bina gibi belirgin nesnelerde en iyi; 0,3–0,5 m uydu görüntüsünde sınırı aşıyor ve nokta istemi daha iyi. Bizim yöntem kesişim adımıyla bunu telafi ediyor; tezde bu nüansla yazılmalı."),
    ("Shirzad vd. (2019)'daki \"gelir\" kriteri hane geliri değil.", "\"Gelir kriterini çok kriterli modele koyan örnek\" demiştim. Doğrusu: kriter, PV'den elde edilecek 20 yıllık kazanç (yatırım getirisi). Toplumsal gösterge olarak kullanılmamalı."),
    ("\"Türkiye'de ilk\" iddiası daraltılmalı.", "Ayak izinden kutu istemli SAM artık Pino-Gallardo vd. (2026) tarafından yayımlandı. Özgünlük, yöntem bileşiminde ve Türkiye bağlamında aranmalı (Bölüm 6)."),
    ("Ünal (2026) bir tez değil, 28 sayfalık proje raporu.", "Daha önce \"ODTÜ yüksek lisans tezi\" demiştim; belge ODTÜ Enformatik Enstitüsü dönem projesi raporu niteliğinde. Atıfta belge türü doğru yazılmalı."),
    ("Potansiyel sonuçlarımız \"kesin\" değil \"teknik üst potansiyel\" olarak sunulmalı.", "Model açıklamasında 526–749 GWh/yıl'ı ana sonuç olarak verdim; literatür karşılaştırması (Bölüm 5.1) engeller ve mevzuat kısıtı olmadan bu değerin iyimser olduğunu gösteriyor."),
    ("RT4ES \"en yakın çalışma\" ama zayıf yanları var.", "Önceki özetimde ağırlıklarının uzman kanaatine dayandığını, duyarlılık analizi olmadığını ve PV üretiminde makale içi tutarsızlık (0,837 ↔ 0,47 TWh/yıl) bulunduğunu belirtmemiştim."),
]
for b, t in dz:
    S.append(KeepTogether([P("<b>%s</b>" % esc(b), ParagraphStyle("dzb", parent=body, textColor=RED, spaceBefore=4, spaceAfter=1)), P(esc(t))]))

# ---------------------------------------------------------------- 9. ek kaynaklar
S.append(Spacer(1, 8))
S.append(baslik("9. Ek kaynak önerileri (okunmadı)"))
title, secs = notu_oku(os.path.join(HERE, "notlar", "28_ek_kaynaklar.md"))
for ad, items in secs:
    for typ, x in items:
        if typ == "b":
            S.append(Paragraph(vurgu(x), bullet, bulletText="•"))
        else:
            S.append(P(esc(x)))

# ---------------------------------------------------------------- 10. kaynakça
S.append(PageBreak())
S.append(baslik("10. Kaynakça (incelenen kaynaklar)"))
kaynakca = []
for f in sorted(glob.glob(os.path.join(HERE, "notlar", "[0-2]*.md"))):
    if "28_ek" in f:
        continue
    _, secs = notu_oku(f)
    for ad, items in secs:
        if ad.startswith("Künye"):
            txt = " ".join(x[1] for x in items)
            txt = re.sub(r"\s*\(Okuma listesindeki künye HATALIYDI[^)]*\)", "", txt)
            kaynakca.append(txt)
import locale
kaynakca.sort(key=lambda s: s.replace("Ş", "Sz").replace("Ü", "Uz").replace("Ç", "Cz").replace("Ö", "Oz").replace("İ", "I"))
for k in kaynakca:
    S.append(Paragraph(esc(k), ParagraphStyle("kc", parent=small, leftIndent=12, firstLineIndent=-12, spaceAfter=3.5)))
S.append(Spacer(1, 8))
S.append(P("İnternet taramasında kullanılan erişim sayfaları: ODTÜ açık arşivi (open.metu.edu.tr), AVESİS, Liverpool ve Manchester üniversite arşivleri, EPFL Infoscience, "
           "KIT yayın arşivi, arXiv, MDPI, JRC yayın arşivi, Ember (ember-energy.org), Unpaywall ve Crossref API (açık erişim konum tespiti). Erişim tarihi: 30 Eylül 2026.", small))

doc.multiBuild(S)
print("OK", OUT)
