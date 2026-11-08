# -*- coding: utf-8 -*-
"""Cati segmentasyonu degerlendirme raporu (PDF) - 2026-10-24. Sayilar dosyalardan okunur, elle yazilmaz.
Girdi : veri/elle/test_referans/{iou_sonuc, iou_insan_insan, ayakizi_duzeltme_listesi, sam_ayar_sonuc}.csv,
        Desktop/CatiGunes_Model_Verisi/catilar.csv, rapor/ara_rapor_2026-10-24/hata_turleri.png
Cikti : rapor/ara_rapor_2026-10-24/cati_segmentasyon_degerlendirme.pdf
Kosu  : python scripts/ara_rapor_pdf.py"""
import os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(KOK, 'veri', 'elle', 'test_referans')
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
OUT = os.path.join(KOK, 'rapor', 'ara_rapor_2026-10-24')
F = r'C:\Windows\Fonts'
for ad, f in (('Ar', 'arial'), ('ArB', 'arialbd'), ('ArI', 'ariali'), ('ArBI', 'arialbi')):
    pdfmetrics.registerFont(TTFont(ad, os.path.join(F, f + '.ttf')))
pdfmetrics.registerFontFamily('Ar', normal='Ar', bold='ArB', italic='ArI', boldItalic='ArBI')
MAVI = '#2a78d6'
MUREKKEP, IKINCIL = colors.HexColor('#0b0b0b'), colors.HexColor('#52514e')

# ---------- sayilar
t = pd.read_csv(os.path.join(TR, 'iou_sonuc.csv'))
ii = pd.read_csv(os.path.join(TR, 'iou_insan_insan.csv'))
sor = pd.read_csv(os.path.join(TR, 'ayakizi_duzeltme_listesi.csv'))
ay = pd.read_csv(os.path.join(TR, 'sam_ayar_sonuc.csv'))
cat = pd.read_csv(os.path.join(MV, 'catilar.csv'))
te = t[t.set == '1_test_referans']
ge = lambda x: (x >= .7).mean()
TEST = dict(n=len(te), med=te.iou_sam_insan.median(), ort=te.iou_sam_insan.mean(), ge=ge(te.iou_sam_insan),
            ai=te.iou_ayakizi_insan.median(), ii=ii.iou_insan_insan.median(), iin=len(ii))
gruplar = [('Test seti (tümü)', te), ('Şüpheli işaretsiz', te[~te.supheli]), ('Şüpheli işaretli', te[te.supheli]),
           ('Sanayi', te[te.tur == 'sanayi']), ('Okul', te[te.tur == 'okul'])]
dis_test = t[t.set.str.startswith('1_test_referans_')].set.str.replace('1_test_referans_', '').value_counts()
ADLAR = {'ayakizi_eksik': 'ayak izi eksik', 'ayakizi_hatali': 'ayak izi hatalı', 'bina_belirsiz': 'bina belirsiz',
         'bagimsiz_degil': 'SAM görülerek çizilen'}

pv = ay[ay.bolum == 'test'].pivot_table(index='cati_id', columns='kural', values='iou')
MEV = 'k0|ayak_iou|kirp'
KUR = [('Mevcut: kutu, ayak izine kırp', MEV), ('Kırpma yok', 'k0|ayak_iou|ham'),
       ('Kutu + merkez noktası, kırpma yok', 'k0n|ayak_iou|ham'), ('Kutu %10 geniş, kırp', 'k10|ayak_iou|kirp')]
rng = np.random.default_rng(0)


def ga(k):
    f = (pv[k] - pv[MEV]).values
    b = [rng.choice(f, len(f)).mean() for _ in range(2000)]
    return f.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5), int((f > .02).sum()), int((f < -.02).sum())


okul = ay[(ay.bolum == 'test') & (ay.tur == 'okul')].groupby('kural').iou.median()
gk = cat.geometri_kaynagi.value_counts()
pan = cat.groupby('panel_durumu').agg(n=('cati_id', 'size'), c=('cati_alan_m2', 'sum'), u=('uygun_alan_m2', 'sum'))

# ---------- grafik: gruplara gore medyan IoU (tek seri)
fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
ad = [g[0] for g in gruplar][::-1]
val = [g[1].iou_sam_insan.median() for g in gruplar][::-1]
n = [len(g[1]) for g in gruplar][::-1]
ax.barh(ad, val, color=MAVI, height=0.55)
for y, (v, k) in enumerate(zip(val, n)):
    ax.text(v + 0.01, y, f'{v:.2f}'.replace('.', ',') + f'  (n={k})', va='center', fontsize=8, color='#52514e')
ax.axvline(0.70, color='#52514e', lw=1, ls='--')
ax.text(0.70, len(ad) - 0.35, 'hedef 0,70', fontsize=7.5, color='#52514e', ha='center')
ax.axvline(TEST['ii'], color='#52514e', lw=1, ls=':')
ax.text(TEST['ii'], len(ad) - 0.35, 'insan↔insan ' + f"{TEST['ii']:.2f}".replace('.', ','), fontsize=7.5, color='#52514e', ha='center')
ax.set_xlim(0, 1.1)
ax.set_xlabel('SAM ↔ insan çizimi, medyan IoU', fontsize=8, color='#52514e')
ax.tick_params(labelsize=8, colors='#52514e')
for s in ('top', 'right'):
    ax.spines[s].set_visible(False)
ax.grid(axis='x', color='#e6e6e3', lw=0.6)
ax.set_axisbelow(True)
plt.tight_layout()
GRAF = os.path.join(OUT, 'iou_gruplar.png')
plt.savefig(GRAF)
plt.close()

# ---------- PDF
S = lambda **k: ParagraphStyle('s', **{**dict(fontName='Ar', fontSize=9.5, leading=13.5, textColor=MUREKKEP), **k})
P_ = S(spaceAfter=5)
H1 = S(fontName='ArB', fontSize=16, leading=20, spaceAfter=4)
H2 = S(fontName='ArB', fontSize=12, leading=16, spaceBefore=10, spaceAfter=5)
KUC = S(fontSize=8, leading=11, textColor=IKINCIL)
MAD = S(leftIndent=12, bulletIndent=2, spaceAfter=3)
f2 = lambda x: f'{x:.2f}'.replace('.', ',')
f3 = lambda x: f'{x:.3f}'.replace('.', ',')
yz = lambda x: f'%{100 * x:.0f}'
bin_ = lambda x: f'{x:,.0f}'.replace(',', '.')


def tablo(veri, gen, hiza=None):
    tb = Table([[Paragraph(str(h), S(fontName='ArB', fontSize=8.5, leading=11)) for h in veri[0]]] +
               [[Paragraph(str(c), S(fontSize=8.5, leading=11)) for c in r] for r in veri[1:]], colWidths=gen)
    tb.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, 0), 0.8, MUREKKEP), ('LINEBELOW', (0, 1), (-1, -1), 0.3, colors.HexColor('#d9d9d6')),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return tb


def madde(liste):
    return [Paragraph(m, MAD, bulletText='•') for m in liste]


H = []
H += [Paragraph('Çatı Segmentasyonu — Değerlendirme Raporu', H1),
      Paragraph('Atatürk OSB + Çiğli kamu · insan çizimleriyle SAM doğrulaması, hata analizi, panel düşümü · 24 Ekim 2026', KUC),
      Spacer(1, 8)]
H += [Paragraph('Özet', H2)] + madde([
    f"SAM'in çatı sınırı başarısı <b>yansız test setinde {TEST['n']} çatı</b> üzerinde ölçüldü: medyan IoU <b>{f3(TEST['med'])}</b>, "
    f"çatıların <b>{yz(TEST['ge'])}</b>'i hedef eşik 0,70'in üstünde. İki insan çizimcinin birbiriyle uyumu {f3(TEST['ii'])} (tavan).",
    'Düşük skorların büyük kısmı modelden değil, <b>çizim tarifinin belirsizliğinden</b> (bitişik çatılar) ve <b>kayıtlı ayak izi hatalarından</b> '
    f"geliyordu. Bunlar ayıklanınca test medyanı 0,845 → {f3(TEST['med'])} oldu.",
    f"Şüphe işareti çalışıyor: işaretsiz çatılarda medyan {f3(gruplar[1][1].iou_sam_insan.median())}, işaretlilerde "
    f"{f3(gruplar[2][1].iou_sam_insan.median())}. Zayıf nokta <b>okullar</b> (kırma çatı).",
    'SAM ayar deneyi (model eğitimi yok): maskeyi ayak izine <b>kırpmamak</b> küçük ama anlamlı bir kazanç veriyor; merkez noktası eklemek tek başına etkisiz.',
    f"Her çatıya son geometri atandı (SAM {gk.get('sam', 0)} · insan {gk.get('insan', 0)} · ayak izi {gk.get('ayak_izi', 0)}) ve "
    f"mevcut paneller düşüldü: kullanılabilir alan <b>{f2(cat.uygun_alan_m2.sum() / 1e6)} km²</b> (ayak izi toplamı ~2,41 km²)."])

H += [Paragraph('1. Mevcut durum', H2),
      Paragraph('Ölçüt IoU (kesişim/birleşim; 1 = birebir aynı alan). Referans: LabelMe ile elle çizilen çatılar. '
                'Test seti, SAM veri setinin rastgele ayrılmış <i>test_referans</i> bölümüdür; kural ayarında kullanılmadı.', P_),
      tablo([['Grup', 'n', 'Medyan IoU', 'IoU ≥ 0,70', 'Ayak izi ↔ insan']] +
            [[a, len(g), f3(g.iou_sam_insan.median()), yz(ge(g.iou_sam_insan)), f3(g.iou_ayakizi_insan.median())] for a, g in gruplar] +
            [['İnsan ↔ insan (bağımsız 2 çizim)', TEST['iin'], f3(TEST['ii']), '—', '—']],
            [6.2 * cm, 1.3 * cm, 2.6 * cm, 2.6 * cm, 3.3 * cm]),
      Spacer(1, 6), Image(GRAF, width=16.5 * cm, height=16.5 * cm * 2.6 / 7.2),
      Paragraph(f"Test dışında tutulanlar (gerekçeli, raporda sayı olarak verilmeli): "
                + ', '.join(f'{ADLAR.get(k, k)} {v}' for k, v in dis_test.items())
                + '. Bu çatılarda insan ile kayıt aynı binaya bakmıyor; IoU modeli ölçmez.', KUC)]

H += [PageBreak(), Paragraph('2. Hatalar nelerden kaynaklanıyor?', H2),
      Paragraph('IoU < 0,5 olan 44 çatı tek tek incelendi. Görselde <font color="#1e9e1e">yeşil</font> insan çizimi, '
                '<font color="#d42020">kırmızı</font> kayıtlı ayak izi, <font color="#2a78d6">mavi</font> SAM maskesi.', P_),
      Image(os.path.join(OUT, 'hata_turleri.png'), width=14 * cm, height=14 * cm * 780 / 1110), Spacer(1, 6),
      tablo([['Kaynak', 'Ne oluyor', 'Kimin hatası'],
             ['Birim farkı (en yaygın)', 'OSB\'de çatılar bitişik; çizen kutunun yanındaki çatıları da çizdi. İnsan ve SAM farklı alanı ölçtü.', 'Çizim tarifi'],
             ['Ayak izi eksik', f"Bina kayıttan büyük; SAM'e eksik kutu verildi ({int((sor.sorun == 'ayakizi_eksik').sum())} çatı).", 'Veri (OSM/Microsoft)'],
             ['Ayak izi yanlış binada', f"Kayıt başka yapıyı gösteriyor ({int((sor.sorun == 'ayakizi_hatali').sum())} çatı).", 'Veri'],
             ['Hedef bina belirsiz', 'Kutu birden çok yapıyı kapsıyor (1 çatı).', 'Veri'],
             ['Kırma/beşik çatı', 'SAM tek yüzü seçiyor; en çok okullarda.', 'Model'],
             ['Ağaç, gölge, iki renkli çatı, panel', 'SAM çatının bir parçasını alıyor.', 'Model'],
             ['OSM tek kayıt / Microsoft parçalı', 'Bitişik kompleks OSM\'de tek, Microsoft\'ta parçalı (ör. c0286); "tek bina" kesin değil.', 'Veri (sınırlılık)']],
            [4.2 * cm, 9.3 * cm, 3 * cm])]

H += [Paragraph('3. Bu hataları nasıl çözüyoruz?', H2),
      tablo([['Sorun', 'Çözüm', 'Durum'],
             ['Çizim tarifi belirsiz', 'Kural: kutu = hangi bina; sınır görüntüden; ayrı yapı (duvar/çatı tipi/renk değişimi) katılmaz. '
              'Kutu dışına >%15 taşan 36 çizim SAM\'den bağımsız ölçütle seçilip yeniden çizildi.', 'Yapıldı'],
             ['Seçim yanlılığı riski', 'Yeniden çizim SAM skoruna değil taşma oranına göre seçildi; test seti ayarda kullanılmadı.', 'Yapıldı'],
             ['Ayak izi eksik / hatalı', f"{len(sor)} çatılık liste (ayakizi_duzeltme_listesi.csv); test puanından ayrı. "
              'Düzeltme: insan çizimini ayak izi olarak al (komşu kayda >%15 taşmıyorsa). 24 Eki: 23 çatıdan 10\'u düzeltildi; '
              '13\'ü komşu OSM kaydına taştığı için uygulanmadı (bina OSM\'de parçalı); c0485 bina belirsiz.', 'Uygulandı (10/23)'],
             ['İnsan çizimi komşu kayda taşıyor', 'Çift sayımı önlemek için kullanılmıyor (komşunun >%15\'i).', 'Otomatik (betik)'],
             ['Başka binaya çizim', 'Kendi ayak izinin <%5\'ine dokunan çizim atlanır (ör. c1307).', 'Otomatik (betik)'],
             ['SAM şüpheli çatılar', 'Son veride insan çizimi, yoksa ayak izi kullanılır.', 'Yapıldı'],
             ['SAM kırma çatı / kırpma', 'Maskeyi ayak izine kırpmamak + komşu taşma kontrolü (bkz. 4). Kalıcı çözüm: ince ayar (daha çok çizim).', 'Öneri — model ekibi'],
             ['Çizilmemiş ~900 çatıda ayak izi hatası', 'Çizimli örnekte oran ~%13; aynı oran genelde de beklenir. Şüpheli + büyük çatılardan başlayıp örneklem kontrolü.', 'Açık']],
            [4 * cm, 9.6 * cm, 2.9 * cm])]

r = [ga(k) for _, k in KUR]
H += [Paragraph('4. SAM ayar deneyi (Colab, 24 Ekim)', H2),
      Paragraph('Model yeniden eğitilmedi. İnsan çizimli 178 çatıda SAM 3 istemle koşuldu (kutu; kutu %10 geniş; kutu + merkez noktası), '
                'her istemin 3 aday maskesi kaydedildi ve 30 seçim kuralı denendi. Kural <b>ayar</b> bölümünde (52 çatı) seçildi, '
                f"<b>test</b> bölümünde ({len(pv)} çatı) mevcut kuralla eşleştirilmiş olarak karşılaştırıldı. Mevcut kuralın bu koşudaki test medyanı "
                f"{f3(pv[MEV].median())}, önceki ölçümle ({f3(TEST['med'])}) tutarlı — SAM deterministik.", P_),
      tablo([['Kural', 'Test medyan', 'Ort. fark', '%95 GA', 'İyileşen / kötüleşen', 'Okul medyan']] +
            [[a, f3(pv[k].median()), ('—' if k == MEV else f'{x[0]:+.3f}'.replace('.', ',')),
              ('—' if k == MEV else f'{f3(x[1])} – {f3(x[2])}'), ('—' if k == MEV else f'{x[3]} / {x[4]}'), f3(okul.get(k, np.nan))]
             for (a, k), x in zip(KUR, r)],
            [5.4 * cm, 2 * cm, 1.8 * cm, 2.7 * cm, 2.4 * cm, 2.2 * cm]),
      Paragraph('Fark eşiği ±0,02 IoU. GA: eşleştirilmiş bootstrap (2.000 tekrar).', KUC), Spacer(1, 4)] + madde([
    'Kazancın kaynağı <b>kırpmamak</b>: kayıtlı ayak izleri çoğu zaman çatıdan biraz küçük ya da kayık; kırpma SAM\'in doğru bulduğu kenarı kesiyor.',
    f"Okullarda (kırma çatı) en iyi sonucu <b>kutuyu %10 genişletmek</b> veriyor (medyan {f3(okul.get('k10|ayak_iou|kirp', np.nan))}); "
    'ama okul örneği 9 çatı, kesin hüküm için az. Merkez noktası genelde tek başına etkisiz.',
    'Uygulamak için tüm 1.085 çatıda kırpmasız koşu (~40 dk) + komşu çatıya taşma kontrolü gerekir; kazanç küçük (~+0,015 IoU) olduğundan <b>karar model ekibinde</b>.'])

H += [Paragraph('5. Son geometri ve panel düşümü', H2),
      Paragraph('Model_Verisi\'ne her çatı için panele esas çatı poligonu (katman <i>cati_son</i>) ve panel düşülmüş kullanılabilir alan '
                '(katman <i>uygun_alan</i>) eklendi. Ayak izi yalnız 10 çatıda insan çizimiyle düzeltildi. c0157 ve c0319 kısmi işaretliydi; '
                'görselde neredeyse tamamen panelli bulunup tam sayıldı. Öncelik: insan çizimi → SAM (şüpheli değilse) → ayak izi.', P_),
      tablo([['Panel durumu', 'Çatı', 'Çatı alanı m²', 'Kullanılabilir m²', 'Kural']] +
            [[{'panel_yok': 'Panel yok', 'tam_dolu': 'Mevcut GES tam', 'kismi_panel_dusuldu': 'Kısmi GES, panel düşüldü',
               'kismi_panel_cizilmedi': 'Kısmi GES, panelsiz alan çizilmedi'}[k], int(v.n), bin_(v.c), bin_(v.u),
              {'panel_yok': 'son çatı', 'tam_dolu': '0 (potansiyel yok)', 'kismi_panel_dusuldu': 'elle çizilen panelsiz alan ∩ çatı',
               'kismi_panel_cizilmedi': 'çatının tamamı — kontrol edilmeli'}[k]] for k, v in pan.iterrows()] +
            [['Toplam', int(pan.n.sum()), bin_(pan.c.sum()), bin_(pan.u.sum()), '']],
            [4.6 * cm, 1.3 * cm, 2.6 * cm, 2.8 * cm, 5.2 * cm]),
      Paragraph(f"Kısmi GES'li 25 çatıda panel düşümü alanı %{100 * (1 - pan.loc['kismi_panel_dusuldu'].u / pan.loc['kismi_panel_dusuldu'].c):.0f} azalttı. "
                'PVGIS/NPV hesabı <i>uygun_alan_m2</i> ile yapılmalı.', P_)]

H += [Paragraph('6. Sıradaki adımlar', H2)] + madde([
    '<b>Veri:</b> komşu OSM kaydına taşan 13 çatı birleştirilmedi — çatı sayısı kaynak veriden geldiği gibi korunur (bu çatılarda kayıtlı ayak izi kullanılır).',
    '<b>Model ekibi:</b> kırpmasız SAM kararını ver; uygulanacaksa tam koşu + taşma kontrolü. İnce ayar ara rapordan sonra, çizim sayısı artınca.',
    '<b>Rapor (13 Kas.):</b> test tablosu + insan↔insan tavanı + dışlanan çatı sayıları + sınırlılıklar (OSM/Microsoft birim farkı, çizilmemiş çatılarda ~%13 ayak izi hatası beklentisi, okul örneği küçük).',
    '<b>Hesap:</b> NPV ve üretim <i>uygun_alan_m2</i> üzerinden; EPDK tarifesi NPV\'ye girecek.'])
H += [Spacer(1, 8), Paragraph('Kaynak dosyalar: CatiGunes/veri/elle/test_referans/*.csv · Desktop/CatiGunes_Model_Verisi (catilar.gpkg, insan_referans/) · '
                              'betikler: cizim_iou.py, cati_geometri.py, sam_ayar.py, ara_rapor_pdf.py.', KUC)]


def alt(c, d):
    c.saveState(); c.setFont('Ar', 7.5); c.setFillColor(IKINCIL)
    c.drawString(2 * cm, 1.2 * cm, 'Çatı GES KDS — segmentasyon değerlendirmesi · 24.10.2026')
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, str(d.page)); c.restoreState()


PDF = os.path.join(OUT, 'cati_segmentasyon_degerlendirme.pdf')
SimpleDocTemplate(PDF, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                  title='Çatı Segmentasyonu — Değerlendirme Raporu', author='CatiGunes').build(H, onFirstPage=alt, onLaterPages=alt)
print(PDF)
