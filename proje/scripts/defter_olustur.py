# -*- coding: utf-8 -*-
"""Colab defterini uretir: notebooks/CatiGunes_Model_Calismasi.ipynb

Girdi tablosu (cache/colab_girdi.csv) deftere gomulur; defter internet ya da
Drive baglantisi istemeden Model 1-3'u bastan hesaplar.

  python scripts/defter_olustur.py          -> ciktisiz defter (Colab'a yuklenecek)
  python scripts/defter_olustur.py --kos    -> ayrica yerelde calistirip ciktili kopya
"""
import csv, io, json, os, sys, unicodedata
import nbformat as nbf

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())

# --- girdi: yerel modelle AYNI satir sirasi (mahalle_sinirlari.geojson sirasi) ---
# Onceki normalizasyon esit degerleri dizideki siraya gore ayiriyordu; eski sonucu
# birebir uretebilmek icin sira korunuyor.
ILCELER = ['ÇİĞLİ', 'KARŞIYAKA']
sira = [(sadelestir(f['properties']['ilce']), sadelestir(f['properties']['mahalle']))
        for f in json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))['features']
        if f['properties']['ilce'] in ILCELER]
girdi = list(csv.DictReader(io.open(yol('cache/colab_girdi.csv'), encoding='utf-8'), delimiter=';'))
ref = {(sadelestir(r['ilce']), sadelestir(r['mahalle'])): r['skor_AHP benzeri'] for r in
       csv.DictReader(io.open(yol('cache/bolge_modelleri.csv'), encoding='utf-8-sig'), delimiter=';')}
G = {(sadelestir(r['ilce']), sadelestir(r['mahalle'])): r for r in girdi}
assert set(G) == set(sira) == set(ref), 'mahalle kumeleri uyusmuyor'
buf = io.StringIO()
w = csv.writer(buf, delimiter=';', lineterminator='\n')
w.writerow(list(girdi[0].keys()) + ['ref_skor_ahp'])
for k in sira:
    w.writerow(list(G[k].values()) + [ref[k]])
GIRDI = buf.getvalue().strip()

hucreler = []
def md(s): hucreler.append(nbf.v4.new_markdown_cell(s.strip('\n')))
def kod(s): hucreler.append(nbf.v4.new_code_cell(s.strip('\n')))

md(r'''
# Çatı güneş paneli uygunluğu ve toplumsal öncelik: Çiğli + Karşıyaka model çalışması

Bu defter projenin üç modelini 53 mahalle için baştan hesaplar:

1. **Model 1 · Çatı alanı:** OSM ve Microsoft bina ayak izlerinden kullanılabilir çatı alanı *bandı*
2. **Model 2 · Üretim:** PVGIS özgül verimiyle kurulu güç (kWp) ve yıllık üretim (kWh) *bandı*
3. **Model 3 · Öncelik:** teknik / ihtiyaç / erişim eksenleri, sıra tabanlı normalizasyon, AHP benzeri ağırlıklar, duyarlılık analizi

**Bu sürümdeki iki değişiklik (11 Eylül 2026)**

| Değişiklik | Önce | Şimdi | Etkisi |
|---|---|---|---|
| Hane tüketimi | 3.600 kWh/yıl (varsayım) | 1.059 kWh/kişi × 2,8 kişi/hane ≈ **2.965 kWh/yıl** | Yalnızca "hane eşdeğeri" sayıları; skorlar değişmez |
| Eşit değerlerin sırası | Dizideki sıraya göre keyfi ayrılıyordu | Eşit değerler **ortalama sıra** alıyor | Erişim ve ihtiyaç puanları, dolayısıyla sıralama |

Hane tüketiminin kaynakları: İZKA *İzmir Mevcut Durum Analizi* (2023), PDF s.255 ve *2024–2028 İzmir Bölge Planı*, PDF s.89.

**Veri nereden geliyor?** Ağır coğrafi adımlar yerel bilgisayarda çalıştı: Microsoft'un 391 bin binalık ayak izi dosyası, OSM Overpass sorguları, kamu binası eşleştirmesi ve PVGIS sorguları. Sonuçları mahalle başına tek satır olarak aşağıdaki hücreye gömülü. Defter internet ya da Drive bağlantısı istemez: **Çalışma zamanı → Tümünü çalıştır**.
''')

md(r'''
## 0 · Kurulum ve girdi tablosu

| Sütun | Anlamı | Kaynak |
|---|---|---|
| `kademe`, `ortusme` | MS binalarının OSM binasıyla örtüşme oranı; A ≥ 0,65 · B ≥ 0,50 · C altı | MS × OSM çapraz kontrol |
| `osm_m2`, `ms_m2` | 25–8.000 m² arası bina ayak izi alanı toplamı | OSM Overpass, Microsoft Global ML Building Footprints |
| `oz_duz`, `oz_guney`, `oz_kuzey` | 1 kWp için yıllık kWh: düz, 30° güney, 30° kuzey | PVGIS v5.3, %14 sistem kaybı |
| `askida_n` | Askıda fatura başvurusu | İzmir BB açık veri (2020) |
| `su_kisi` | Konut abonesi başına ortalama aylık su tüketimi (gelir vekili) | İzmir BB açık veri (2023) |
| `ses` | Sosyoekonomik seviye skoru, **ilçe düzeyi** | TÜİK SES 2023 |
| `kamu_n`, `kamu_m2` | Mülkiyeti kamu olan tesislerdeki binaların çatı alanı | OSM + mülkiyet sınıflandırması |
| `belirsiz_n`, `belirsiz_m2` | Mülkiyeti belirsiz tesisler (skora girmez) | aynı |
| `ref_skor_ahp` | Yerel modelin önceki AHP skoru (yalnızca doğrulama için) | `cache/bolge_modelleri.csv` |
''')

kod(r'''
import io, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

pd.set_option('display.width', 180)
pd.set_option('display.max_columns', 40)

GIRDI = """__GIRDI__"""

df = pd.read_csv(io.StringIO(GIRDI), sep=';')
ILCELER = ['ÇİĞLİ', 'KARŞIYAKA']
AD = {'ÇİĞLİ': 'Çiğli', 'KARŞIYAKA': 'Karşıyaka'}
print(len(df), 'mahalle |', {AD[k]: int(v) for k, v in df.groupby('ilce').size().items()})
df.head()
''')

md(r'''
## 1 · Varsayımlar
''')

kod(r'''
M2_PER_KWP = 6.0                        # m² başına ~200 W modül
KULLANILABILIR = {0: 0.55, 30: 0.35}    # düz çatı (sıra aralığı + kenar) / 30° beşik çatı (tek yüz)

KISI_BASI_MESKEN = 1059.0               # kWh/kişi/yıl, İzmir 2021 (MDA s.255)
HANE_BUYUKLUGU = 2.8                    # kişi/hane, İzmir 2021 (BP s.89)
HANE_TUKETIM = KISI_BASI_MESKEN * HANE_BUYUKLUGU
HANE_TUKETIM_ESKI = 3600.0

IHTIYAC_AGIRLIK = {'askida': 0.40, 'su_ters': 0.40, 'ses_ters': 0.20}
AGIRLIK = {                             # (teknik, ihtiyaç, erişim)
    'yalnız teknik':     (1.00, 0.00, 0.00),
    'AHP benzeri':       (0.50, 0.35, 0.15),
    'ihtiyaç ağırlıklı': (0.35, 0.50, 0.15),
    'eşit':              (0.34, 0.33, 0.33),
}
ANA = 'AHP benzeri'
print(f'Hane tüketimi: {HANE_TUKETIM:,.1f} kWh/yıl (eski {HANE_TUKETIM_ESKI:,.0f}) '
      f'-> hane eşdeğeri x{HANE_TUKETIM_ESKI / HANE_TUKETIM:.3f}'.replace(',', '.'))
''')

md(r'''
## 2 · Model 1: çatı alanı bandı

Microsoft ayak izleri bitişik binaları birleştirdiği için alanı büyütüyor, OSM ise eksik çizilmiş binalar yüzünden küçültebiliyor. Bu yüzden tek bir alan değil, iki kaynağın arası bant olarak taşınıyor. Alt sınır küçük olan, üst sınır büyük olan kaynak.
''')

kod(r'''
df['alan_alt'] = df[['osm_m2', 'ms_m2']].min(axis=1)
df['alan_ust'] = df[['osm_m2', 'ms_m2']].max(axis=1)
df['alan_orta'] = np.sqrt(df['alan_alt'].clip(lower=1) * df['alan_ust'].clip(lower=1))

g = df.groupby('ilce')
ozet1 = pd.DataFrame({
    'OSM bina': g['osm_n'].sum(),
    'MS bina': g['ms_n'].sum(),
    'OSM alan (ha)': g['osm_m2'].sum() / 1e4,
    'MS alan (ha)': g['ms_m2'].sum() / 1e4,
    'örtüşme medyanı': g['ortusme'].median(),
    'kademe A/B/C': g['kademe'].apply(lambda s: '/'.join(str(int((s == k).sum())) for k in 'ABC')),
}).reindex(ILCELER)
ozet1['MS/OSM alan'] = ozet1['MS alan (ha)'] / ozet1['OSM alan (ha)']
ozet1.rename(index=AD).round(3)
''')

md(r'''
## 3 · Model 2: üretim bandı

* **Alt sınır:** küçük alan × beşik çatı (%35) × kuzeye bakan yüz
* **Üst sınır:** büyük alan × düz çatı (%55) × optimum yön
* **Bant merkezi:** alt ve üst sınırın geometrik ortalaması; ek varsayım gerektirmez
* **En olası yerleşim:** orta alan × düz çatı. Türkiye'de teras çatı yaygın olduğu için eklendi. Bandın ortası değildir, üst sınıra yakın durur.
''')

kod(r'''
df['kWp_alt'] = df['alan_alt'] * KULLANILABILIR[30] / M2_PER_KWP
df['kWp_ust'] = df['alan_ust'] * KULLANILABILIR[0] / M2_PER_KWP
df['kWp_olasi'] = df['alan_orta'] * KULLANILABILIR[0] / M2_PER_KWP
df['kWh_alt'] = df['kWp_alt'] * df['oz_kuzey']
df['kWh_ust'] = df['kWp_ust'] * df['oz_duz']
df['kWh_gm'] = np.sqrt(df['kWh_alt'].clip(lower=1) * df['kWh_ust'])
df['kWh_olasi'] = df['kWp_olasi'] * df['oz_duz']

t = df.groupby('ilce')[['kWp_alt', 'kWp_ust', 'kWh_alt', 'kWh_gm', 'kWh_olasi', 'kWh_ust']].sum().reindex(ILCELER)
t.loc['TOPLAM'] = t.sum()
ozet2 = pd.DataFrame({
    'MWp alt': t['kWp_alt'] / 1e3, 'MWp üst': t['kWp_ust'] / 1e3,
    'GWh alt': t['kWh_alt'] / 1e6, 'GWh bant merkezi': t['kWh_gm'] / 1e6,
    'GWh en olası': t['kWh_olasi'] / 1e6, 'GWh üst': t['kWh_ust'] / 1e6,
})
ozet2['bant (üst/alt)'] = ozet2['GWh üst'] / ozet2['GWh alt']
ozet2.rename(index=AD).round(2)
''')

md(r'''
### Canlı PVGIS kontrolü (isteğe bağlı)

Gömülü özgül verim değerleri PVGIS'ten alındı. `PVGIS_KONTROL = True` yapıp çalıştırırsan bir mahalle için API yeniden sorgulanır ve değerler karşılaştırılır. İnternet gerekir.
''')

kod(r'''
PVGIS_KONTROL = False

if PVGIS_KONTROL:
    import requests
    r0 = df.iloc[0]
    q = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc', timeout=90,
                     params=dict(lat=round(r0.lat, 3), lon=round(r0.lon, 3), peakpower=1, loss=14,
                                 angle=0, aspect=0, outputformat='json'))
    canli = q.json()['outputs']['totals']['fixed']['E_y']
    print(f'{r0.mahalle}: gömülü {r0.oz_duz:.1f} | canlı {canli:.1f} kWh/kWp')
else:
    print('Atlandı (PVGIS_KONTROL = False).')
''')

md(r'''
## 4 · Hane eşdeğeri: düzeltmenin etkisi

"Hane eşdeğeri" yıllık üretimin kaç hanenin yıllık mesken elektriğine denk geldiğini gösterir. Tahmini hane sayısı nüfus / 2,8 ile hesaplandı. **Karşılama oranı** yıllık enerji dengesidir: üretimin gündüz yapılması, şebeke ve depolama bu orana dahil değildir.
''')

kod(r'''
h = df.groupby('ilce')[['kWh_alt', 'kWh_gm', 'kWh_ust', 'nufus']].sum().reindex(ILCELER)
h.loc['TOPLAM'] = h.sum()
hane = pd.DataFrame({
    'eski (3.600) merkez': h['kWh_gm'] / HANE_TUKETIM_ESKI,
    'yeni alt': h['kWh_alt'] / HANE_TUKETIM,
    'yeni merkez': h['kWh_gm'] / HANE_TUKETIM,
    'yeni üst': h['kWh_ust'] / HANE_TUKETIM,
    'tahmini hane': h['nufus'] / HANE_BUYUKLUGU,
})
hane['karşılama alt %'] = 100 * hane['yeni alt'] / hane['tahmini hane']
hane['karşılama merkez %'] = 100 * hane['yeni merkez'] / hane['tahmini hane']
print(f"Merkez tahminde hane eşdeğeri artışı: %{100 * (HANE_TUKETIM_ESKI / HANE_TUKETIM - 1):.1f}")
hane.rename(index=AD).round(0).astype(int)
''')

md(r'''
## 5 · Model 3: öncelik skoru

Üç eksen ayrı tutuluyor:

* **Teknik:** yıllık üretimin bant merkezi
* **İhtiyaç:** askıda fatura / 1000 kişi (%40) + düşük su tüketimi (%40) + düşük SES (%20)
* **Erişim:** kamu çatısı m² / 1000 kişi

Erişim ayrı eksende çünkü Çiğli'de kamu binası yoğunluğu ihtiyaçla ters ilişkili. Aynı terimde toplanırsa skor yatırımı ihtiyaçtan uzaklaştırıyor.

Her gösterge 0–1 arasına **sıra tabanlı** yerleştiriliyor (min-max değil; tek bir dev mahalle diğerlerini sıkıştırmasın diye). Aşağıda eski ve düzeltilmiş normalizasyon birlikte hesaplanıyor.
''')

kod(r'''
n = df['nufus'].clip(lower=1)
df['askida_bin'] = df['askida_n'] / n * 1000
df['kamu_bin'] = df['kamu_n'] / n * 1000
df['kamu_cati_bin'] = df['kamu_m2'] / n * 1000
df['cati_kisi'] = df['alan_orta'] / n


def yuzdelik_eski(x):
    """Önceki sürüm: eşit değerler dizideki sıraya göre farklı puan alıyordu."""
    x = np.asarray(x, float)
    s = np.empty(len(x))
    s[np.argsort(x)] = np.arange(len(x))
    return s / (len(x) - 1)


def yuzdelik(x):
    """Düzeltilmiş: eşit değerler ortalama sırayı alır."""
    return (pd.Series(np.asarray(x, float)).rank(method='average').to_numpy() - 1) / (len(x) - 1)


def eksenler(norm):
    a = norm(df['askida_bin'])
    s = norm(-df['su_kisi'])
    ses = norm(-df['ses'])
    return dict(
        teknik=norm(df['kWh_gm']),
        ihtiyac=IHTIYAC_AGIRLIK['askida'] * a + IHTIYAC_AGIRLIK['su_ters'] * s + IHTIYAC_AGIRLIK['ses_ters'] * ses,
        ihtiyac_sessiz=0.5 * a + 0.5 * s,
        erisim=norm(df['kamu_cati_bin']),
        erisim_sayim=norm(df['kamu_bin']),
        ses=ses,
    )


def skor(E, agirlik, ihtiyac='ihtiyac', erisim='erisim'):
    wt, wi, we = agirlik
    return wt * E['teknik'] + wi * E[ihtiyac] + we * E[erisim]


E_eski = eksenler(yuzdelik_eski)
E = eksenler(yuzdelik)

# Doğrulama: eski yöntem yerel modelin önceki çıktısını üretmeli
fark = np.abs(skor(E_eski, AGIRLIK[ANA]) - df['ref_skor_ahp']).max()
print(f'Eski yöntem ile yerel çıktı arasındaki en büyük skor farkı: {fark:.5f}')
assert fark < 1e-3, 'Defter yerel modeli üretemedi'
print('Doğrulama geçti: defter yerel modelle aynı sonucu veriyor.')
''')

md(r'''
### 5.1 · Eşit değer sorunu

SES ilçe düzeyinde yayımlandığı için bir ilçedeki bütün mahallelerde aynı. Birçok mahallede de kamu çatısı yok. Eski normalizasyon bu eşit değerlere farklı puanlar veriyordu.
''')

kod(r'''
for il in ILCELER:
    m = (df['ilce'] == il).to_numpy()
    print(f"{AD[il]:10s} SES {df.loc[m, 'ses'].iloc[0]:.2f} (bütün mahallelerde aynı) | "
          f"düşük SES puanı eski {E_eski['ses'][m].min():.2f}–{E_eski['ses'][m].max():.2f}, "
          f"yeni {E['ses'][m].min():.2f}")

sifir = (df['kamu_m2'] == 0).to_numpy()
print(f"\nKamu çatısı olmayan {sifir.sum()} mahalle | erişim puanı eski "
      f"{E_eski['erisim'][sifir].min():.2f}–{E_eski['erisim'][sifir].max():.2f}, "
      f"yeni {E['erisim'][sifir].min():.2f}")
pd.DataFrame({'ilçe': df['ilce'].map(AD), 'mahalle': df['mahalle'],
              'erişim eski': E_eski['erisim'], 'erişim yeni': E['erisim']})[sifir] \
    .sort_values('erişim eski', ascending=False).round(3).head(10)
''')

md(r'''
### 5.2 · Eksenler arası ilişki (Spearman)
''')

kod(r'''
def rho(a, b):
    """Spearman: ortalama sıralar arasındaki Pearson korelasyonu (eşit değerlere dayanıklı)."""
    ra = pd.Series(np.asarray(a, float)).rank(method='average')
    rb = pd.Series(np.asarray(b, float)).rank(method='average')
    return float(np.corrcoef(ra, rb)[0, 1])

satir = []
for il in ILCELER + [None]:
    m = np.ones(len(df), bool) if il is None else (df['ilce'] == il).to_numpy()
    satir.append({
        'kapsam': 'iki ilçe' if il is None else AD[il], 'n': int(m.sum()),
        'askıda ↔ kamu sayısı': rho(df['askida_bin'][m], df['kamu_bin'][m]),
        'ihtiyaç ↔ erişim': rho(E['ihtiyac'][m], E['erisim'][m]),
        'ihtiyaç ↔ teknik': rho(E['ihtiyac'][m], E['teknik'][m]),
        'su/kişi ↔ çatı/kişi': rho(df['su_kisi'][m], df['cati_kisi'][m]),
    })
pd.DataFrame(satir).set_index('kapsam').round(2)
''')

md(r'''
### 5.3 · Ağırlık senaryoları ve duyarlılık

Kendall tau, bir senaryonun ilk 10'unun ana senaryodaki (AHP benzeri) sırayla ne kadar uyuştuğunu ölçer. 1'e yakın değer, ağırlığın sıralamayı değiştirmediği anlamına gelir.
''')

kod(r'''
ETIKET = (df['mahalle'] + '|' + df['ilce']).to_numpy()


def sirala(s):
    return list(ETIKET[np.argsort(-np.asarray(s), kind='stable')])


def kendall(a, b):
    idx = {v: i for i, v in enumerate(b)}
    o = [x for x in a if x in idx]
    uy = ters = 0
    for i in range(len(o)):
        for j in range(i + 1, len(o)):
            d = idx[o[i]] - idx[o[j]]
            uy += d < 0
            ters += d > 0
    return (uy - ters) / max(uy + ters, 1)


ana_sira = sirala(skor(E, AGIRLIK[ANA]))
tablo = []
for ad, w in AGIRLIK.items():
    s = sirala(skor(E, w))
    tablo.append({'senaryo': ad, 'ilk 10 ortak': len(set(s[:10]) & set(ana_sira[:10])),
                  'Kendall tau': kendall(s[:10], ana_sira)})
for ad, s in [('SES çıkarılırsa', skor(E, AGIRLIK[ANA], ihtiyac='ihtiyac_sessiz')),
              ('kamu alanı yerine sayısı', skor(E, AGIRLIK[ANA], erisim='erisim_sayim'))]:
    s = sirala(s)
    tablo.append({'senaryo': ad, 'ilk 10 ortak': len(set(s[:10]) & set(ana_sira[:10])),
                  'Kendall tau': kendall(s[:10], ana_sira)})
eski_sira = sirala(skor(E_eski, AGIRLIK[ANA]))
tablo.append({'senaryo': 'ESKİ normalizasyon', 'ilk 10 ortak': len(set(eski_sira[:10]) & set(ana_sira[:10])),
              'Kendall tau': kendall(eski_sira[:10], ana_sira)})
pd.DataFrame(tablo).set_index('senaryo').round(2)
''')

md(r'''
### 5.4 · Sonuç: düzeltilmiş sıralamada ilk 15 mahalle
''')

kod(r'''
for ad, w in AGIRLIK.items():
    df['skor_' + ad] = skor(E, w)
df['p_teknik'], df['p_ihtiyac'], df['p_erisim'] = E['teknik'], E['ihtiyac'], E['erisim']
yeni_no = {k: i + 1 for i, k in enumerate(ana_sira)}
eski_no = {k: i + 1 for i, k in enumerate(eski_sira)}
df['sira'] = [yeni_no[k] for k in ETIKET]
df['eski_sira'] = [eski_no[k] for k in ETIKET]

sonuc = df.sort_values('sira')
goster = sonuc[['sira', 'eski_sira', 'ilce', 'mahalle', 'kademe', 'skor_AHP benzeri',
                'p_teknik', 'p_ihtiyac', 'p_erisim', 'kWh_gm', 'nufus']].copy()
goster['ilce'] = goster['ilce'].map(AD)
goster['kWh_gm'] = goster['kWh_gm'] / 1e3
goster = goster.rename(columns={'kWh_gm': 'MWh (merkez)', 'skor_AHP benzeri': 'skor'})
ilk = sonuc.head(15)
print('İlk 15 içinde ilçe dağılımı:', {AD[k]: int(v) for k, v in ilk['ilce'].value_counts().items()},
      '| kademe:', ilk['kademe'].value_counts().sort_index().to_dict())
goster.head(15).round(3).set_index('sira')
''')

kod(r'''
degisen = goster.assign(fark=goster['eski_sira'] - goster['sira'])
degisen = degisen[degisen['fark'].abs() >= 4].sort_values('fark')
print(f"Sırası 4 ve daha fazla değişen mahalle: {len(degisen)}")
degisen[['sira', 'eski_sira', 'fark', 'ilce', 'mahalle', 'p_erisim', 'p_ihtiyac']].round(3).set_index('mahalle')
''')

md(r'''
## 6 · Grafikler
''')

kod(r'''
fig, ax = plt.subplots(figsize=(8.5, 2.6))
for i, il in enumerate(ILCELER):
    r = ozet2.loc[il]
    ax.plot([r['GWh alt'], r['GWh üst']], [i, i], color='#0E6B67', lw=3, solid_capstyle='round')
    ax.scatter([r['GWh alt'], r['GWh üst']], [i, i], color='#0E6B67', s=45, zorder=3)
    ax.scatter(r['GWh bant merkezi'], i, marker='|', s=400, color='#1E2A30', zorder=4, linewidths=2)
    ax.annotate(f"{r['GWh alt']:.0f}", (r['GWh alt'], i), xytext=(-8, 0), textcoords='offset points', ha='right', va='center')
    ax.annotate(f"{r['GWh üst']:.0f}", (r['GWh üst'], i), xytext=(8, 0), textcoords='offset points', ha='left', va='center')
    ax.annotate(f"merkez {r['GWh bant merkezi']:.0f}", (r['GWh bant merkezi'], i), xytext=(0, 11),
                textcoords='offset points', ha='center', fontsize=9, color='#3F4D55')
ax.set_yticks(range(len(ILCELER)), [AD[k] for k in ILCELER])
ax.set_ylim(-0.7, len(ILCELER) - 0.3)
ax.set_xlim(0, ozet2.loc[ILCELER, 'GWh üst'].max() * 1.15)
ax.set_xlabel('Yıllık üretim (GWh/yıl)')
ax.set_title('Çatı GES teknik üretim bandı', loc='left')
ax.grid(axis='x', color='#E7ECEE'); ax.set_axisbelow(True)
for k in ['top', 'right', 'left']: ax.spines[k].set_visible(False)
plt.tight_layout(); plt.show()
''')

kod(r'''
en = sonuc.head(12).iloc[::-1]
etiket = [f"{m} ({AD[i]})" for m, i in zip(en['mahalle'], en['ilce'])]
wt, wi, we = AGIRLIK[ANA]
fig, ax = plt.subplots(figsize=(8.5, 5))
sol = np.zeros(len(en))
for ad, w, col, renk in [('teknik', wt, 'p_teknik', '#2F6DB5'), ('ihtiyaç', wi, 'p_ihtiyac', '#D9822B'),
                         ('erişim', we, 'p_erisim', '#3A9E7A')]:
    v = w * en[col].to_numpy()
    ax.barh(etiket, v, left=sol, color=renk, edgecolor='white', linewidth=1.5, label=f'{ad} × {w:.2f}')
    sol += v
for y, s in enumerate(sol):
    ax.text(s + 0.01, y, f'{s:.3f}', va='center', fontsize=9)
ax.set_xlim(0, 1)
ax.set_xlabel('Skor katkısı')
ax.set_title('İlk 12 mahalle: skorun eksenlere dağılımı (AHP benzeri)', loc='left')
ax.legend(loc='lower right', frameon=False)
for k in ['top', 'right']: ax.spines[k].set_visible(False)
plt.tight_layout(); plt.show()
''')

kod(r'''
fig, ax = plt.subplots(figsize=(5.5, 5.2))
for il, renk in [('ÇİĞLİ', '#0E6B67'), ('KARŞIYAKA', '#A8650F')]:
    m = df['ilce'] == il
    ax.scatter(df.loc[m, 'eski_sira'], df.loc[m, 'sira'], s=28, color=renk, label=AD[il], alpha=.85)
ax.plot([1, len(df)], [1, len(df)], color='#9AA6AD', lw=1, ls='--')
for _, r in degisen.iterrows():
    ax.annotate(r['mahalle'], (r['eski_sira'], r['sira']), xytext=(4, -3), textcoords='offset points', fontsize=7.5)
ax.set_xlabel('Eski sıra'); ax.set_ylabel('Düzeltilmiş sıra')
ax.set_title('Normalizasyon düzeltmesi sıralamayı nasıl değiştirdi?', loc='left', fontsize=11)
ax.invert_xaxis(); ax.invert_yaxis()
ax.legend(frameon=False)
plt.tight_layout(); plt.show()
''')

md(r'''
## 7 · Çıktı dosyası

Sonuç tablosu çalışma klasörüne yazılır. Colab'da soldaki **Dosyalar** panelinden indirilebilir. `INDIR = True` yaparsan tarayıcı indirmesi de başlar.
''')

kod(r'''
INDIR = False

sutun = ['sira', 'eski_sira', 'ilce', 'mahalle', 'kademe', 'ortusme', 'nufus',
         'alan_alt', 'alan_ust', 'kWp_alt', 'kWp_ust', 'kWh_alt', 'kWh_gm', 'kWh_olasi', 'kWh_ust',
         'askida_bin', 'su_kisi', 'ses', 'kamu_n', 'kamu_m2', 'kamu_cati_bin',
         'p_teknik', 'p_ihtiyac', 'p_erisim'] + ['skor_' + a for a in AGIRLIK]
dosya = 'catigunes_model_sonuclari.csv'
sonuc[sutun].round(4).to_csv(dosya, sep=';', index=False, encoding='utf-8-sig')
print('Yazıldı:', dosya, '|', len(sonuc), 'satır')
if INDIR:
    from google.colab import files
    files.download(dosya)
''')

md(r'''
## 8 · Sınırlılıklar

* Çatı alanı SAM segmentasyonundan değil bina ayak izinden geliyor; çatı eğimi ve yönü mahalle ölçeğinde doğrulanmadı.
* Hane tüketimi ve hane büyüklüğü **il** ortalaması. Çiğli ve Karşıyaka için ilçe verisi (TÜİK ADNKS hane büyüklüğü, GDZ mahalle tüketimi) istenmeli.
* Karşılama oranı yıllık enerji dengesidir; saatlik eşleşme, şebeke ve depolama kısıtı içermez.
* SES ilçe düzeyinde; mahalleler arasında ayrım üretmez, yalnızca iki ilçeyi ayırır.
* Askıda fatura verisi 2020 pandemi programından; seçilim yanlılığı taşır, tek başına yoksulluk ölçüsü değildir.
* Plan belgelerinin işaret ettiği risk katmanları (sel ve kıyı riski, Kaklıç havaalanı, Sasalı doğal sit, bina kalitesi) henüz modelde yok.
''')

nb = nbf.v4.new_notebook(cells=hucreler, metadata={
    'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'},
    'language_info': {'name': 'python'},
    'colab': {'provenance': [], 'toc_visible': True},
})
for c in nb.cells:
    if c.cell_type == 'code':
        c.source = c.source.replace('__GIRDI__', GIRDI)

os.makedirs(yol('notebooks'), exist_ok=True)
temiz = yol('notebooks', 'CatiGunes_Model_Calismasi.ipynb')
nbf.write(nb, temiz)
print('ciktisiz defter:', temiz, os.path.getsize(temiz), 'bayt')

if '--kos' in sys.argv:
    from nbclient import NotebookClient
    kosu = nbf.read(temiz, as_version=4)
    NotebookClient(kosu, timeout=300, kernel_name='python3',
                   resources={'metadata': {'path': yol('notebooks')}}).execute()
    ciktili = yol('notebooks', 'CatiGunes_Model_Calismasi_ciktili.ipynb')
    nbf.write(kosu, ciktili)
    print('ciktili defter :', ciktili, os.path.getsize(ciktili), 'bayt')
    for i, c in enumerate(kosu.cells):
        if c.cell_type != 'code':
            continue
        for o in c.get('outputs', []):
            if o.get('output_type') == 'stream':
                print('--- [%d] stdout\n%s' % (i, o['text'][:1500]))
            elif o.get('output_type') in ('execute_result', 'display_data'):
                d = o.get('data', {})
                if 'text/plain' in d and 'image/png' not in d:
                    print('--- [%d] tablo\n%s' % (i, d['text/plain'][:2500]))
                elif 'image/png' in d:
                    print('--- [%d] grafik (%d kB)' % (i, len(d['image/png']) // 1024))
            elif o.get('output_type') == 'error':
                print('--- [%d] HATA %s: %s' % (i, o['ename'], o['evalue']))
