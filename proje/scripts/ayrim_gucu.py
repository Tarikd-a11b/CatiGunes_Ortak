# -*- coding: utf-8 -*-
"""PILOT SECIMI ICIN AYRIM GUCU ANALIZI.

Soru: pilot bolge hangi kapsamda secilirse toplumsal ihtiyac degiskeni gercekten
      ayrim uretir? (Faz 3'te bulunan sorun: tek mahallede agirliklar siralamayi
      degistirmiyor, cunku ihtiyac katmani sabit kaliyor.)

Yontem: Izmir'in TUM mahalleleri icin mahalle kademesindeki iki ihtiyac vekilini
        hesaplar - askida fatura basvurusu/1000 kisi ve konut su tuketimi/abone -
        sonra aday pilot kapsamlarinin bu dagilimin ne kadarini kapsadigini olcer.
        Sinir poligonu gerekmez; sadece resmi CSV'ler kullanilir.

Cikti: cache/ayrim_gucu.csv (tum Izmir mahalleleri) + ekrana senaryo karsilastirmasi
"""
import csv, io, json, os, unicodedata
import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)


def sade(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def csv_oku(p):
    return list(csv.DictReader(io.open(yol(p), encoding='utf-8-sig'), delimiter=';'))


def sayi(x):
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return 0.0


# --------------------------------------------------------------------------
M = {}   # (ilce, mahalle) -> kayit


def kayit(ilce, mahalle):
    a = (sade(ilce), sade(mahalle))
    if a not in M:
        M[a] = dict(ilce=ilce.strip(), mahalle=mahalle.strip(), nufus=0, yapi=0,
                    askida=0, su_abone_ay=0.0, su_m3=0.0)
    return M[a]


for r in csv_oku('cache/acikveri/mahalle_nufus.csv'):
    k = kayit(r['ILCE_ADI'], r['MAHALLE_ADI'])
    k['nufus'] = int(sayi(r['NUFUS_ERKEK_TOPLAM']) + sayi(r['NUFUS_KADIN_TOPLAM']))

for r in csv_oku('cache/acikveri/mahalle_bina_sayisi.csv'):
    kayit(r['ILCE'], r['MAHALLE'])['yapi'] = int(sayi(r['YAPI']))

for r in csv_oku('cache/acikveri/askida_fatura.csv'):
    kayit(r['ILCE'], r['MAHALLE'])['askida'] += int(sayi(r['BASVURU_SAYISI']))

SU_YIL = '2023'
with io.open(yol('cache/acikveri/mahalle_su_tuketim.csv'), encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter=';'):
        if r['ABONELIK_GRUBU'].strip() != 'Konut' or r['YIL'].strip() != SU_YIL:
            continue
        k = kayit(r['ILCE'], r['MAHALLE'])
        k['su_abone_ay'] += sayi(r['ABONE_ADEDI'])
        k['su_m3'] += sayi(r['ORTALAMA_TUKETIM'])

for k in M.values():
    k['askida_1000'] = (1000.0 * k['askida'] / k['nufus']) if k['nufus'] else None
    k['su_abone_basi'] = (k['su_m3'] / k['su_abone_ay']) if k['su_abone_ay'] else None

# SEGE ilce skorlari (Izmir Mevcut Durum Analizi 2023, Tablo 1.7'den cikarildi)
sege = {}
sp = yol('cache/izka/sege_ilce.json')
if os.path.exists(sp):
    for r in json.load(open(sp, encoding='utf-8')):
        sege[sade(r['ilce'])] = dict(skor=sayi(r['s2022_skor']),
                                     kademe=int(sayi(r['s2022_kademe'])),
                                     tr_sira=int(sayi(r['s2022_tr'])))
# tabloda ilk sayfada kalan 4 ilce elle eklendi (ayni tablo, s.36)
for ad, (tr, skor, kad) in {'Aliağa': (105, 1.154, 2), 'Balçova': (18, 2.902, 1),
                            'Bayındır': (503, -0.304, 4), 'Bayraklı': (92, 1.322, 2)}.items():
    sege.setdefault(sade(ad), dict(skor=skor, kademe=kad, tr_sira=tr))
for k in M.values():
    s = sege.get(sade(k['ilce']))
    k['sege_skor'] = s['skor'] if s else None
    k['sege_kademe'] = s['kademe'] if s else None

gecerli = [k for k in M.values() if k['askida_1000'] is not None and k['nufus'] >= 300]
print('Izmir mahalle kaydi: %d  |  gecerli (nufus>=300, askida hesaplanabilir): %d'
      % (len(M), len(gecerli)))

# --------------------------------------------------------------------------
def ozet(ad, kume):
    """Bir pilot kapsaminin ihtiyac degiskenindeki ayrim gucu."""
    if len(kume) < 2:
        print('  %-42s birim=%-3d  AYRIM YOK (tek birim)' % (ad, len(kume)))
        return
    a = np.array([k['askida_1000'] for k in kume])
    s = np.array([k['su_abone_basi'] for k in kume if k['su_abone_basi']])
    kad = sorted({k['sege_kademe'] for k in kume if k['sege_kademe']})
    print('  %-42s birim=%-3d  askida/1000: %.1f-%.1f (CV %.2f) | su: %.1f-%.1f | SEGE kademe %s'
          % (ad, len(kume), a.min(), a.max(), a.std() / a.mean() if a.mean() else 0,
             s.min() if len(s) else 0, s.max() if len(s) else 0,
             ','.join(map(str, kad)) or '-'))
    return a


tum = np.array([k['askida_1000'] for k in gecerli])
print('\nIZMIR GENELI askida fatura/1000 kisi: medyan %.1f  %%10 %.1f  %%90 %.1f  max %.1f'
      % (np.median(tum), np.percentile(tum, 10), np.percentile(tum, 90), tum.max()))

cigli = [k for k in gecerli if sade(k['ilce']) == sade('ÇİĞLİ')]
menemen = [k for k in gecerli if sade(k['ilce']) == sade('MENEMEN')]
evka5 = [k for k in gecerli if sade(k['mahalle']) == sade('EVKA-5')
         and sade(k['ilce']) == sade('ÇİĞLİ')]
balatcik = [k for k in gecerli if sade(k['mahalle']) == sade('BALATÇIK')]
gmk = [k for k in gecerli if sade(k['mahalle']) == sade('GAZİ MUSTAFA KEMAL')
       and sade(k['ilce']) == sade('MENEMEN')]

# SEGE kademelerini gercekten yayan bir ornek kapsam
COK_ILCE = ['KONAK', 'ÇİĞLİ', 'MENEMEN', 'BERGAMA', 'KİRAZ']
cok = [k for k in gecerli if any(sade(k['ilce']) == sade(x) for x in COK_ILCE)]

print('\n=== SENARYO KARSILASTIRMASI (ihtiyac degiskeninde ayrim gucu) ===')
ozet('A) yalniz Evka-5', evka5)
ozet('B) yalniz Balatcik', balatcik)
ozet('C) yalniz Seyrek (Menemen/Gazi M.Kemal)', gmk)
ozet('D) Cigli ilcesi (tum mahalleler)', cigli)
ozet('E) Cigli + Menemen', cigli + menemen)
ozet('F) Konak+Cigli+Menemen+Bergama+Kiraz', cok)
ozet('G) Izmir geneli (ust sinir)', gecerli)

print('\n=== ADAYLARIN IZMIR DAGILIMINDAKI YERI ===')
def yuzdelik(k):
    return 100.0 * (tum < k['askida_1000']).mean()
for ad, kume in [('EVKA-5', evka5), ('BALATÇIK', balatcik),
                 ('GAZİ MUSTAFA KEMAL (Seyrek)', gmk)]:
    for k in kume:
        print('  %-30s askida/1000 = %5.1f  -> Izmir dagiliminda %%%.0f yuzdelik  '
              '| su %.1f m3/abone/ay | SEGE %s. kademe (%s)'
              % (ad, k['askida_1000'], yuzdelik(k), k['su_abone_basi'] or 0,
                 k['sege_kademe'], k['ilce']))

print('\n=== IZMIR GENELINDE EN YUKSEK IHTIYAC (askida/1000, nufus>=2000) ===')
buyuk = [k for k in gecerli if k['nufus'] >= 2000]
for k in sorted(buyuk, key=lambda k: -k['askida_1000'])[:12]:
    print('  %-16s %-24s nufus %6d  askida/1000 %5.1f  su %4.1f  SEGE kademe %s'
          % (k['ilce'], k['mahalle'][:24], k['nufus'], k['askida_1000'],
             k['su_abone_basi'] or 0, k['sege_kademe']))

# --------------------------------------------------------------------------
sut = ['ilce', 'mahalle', 'nufus', 'yapi', 'askida', 'askida_1000',
       'su_abone_basi', 'sege_skor', 'sege_kademe']
with io.open(yol('cache/ayrim_gucu.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    f.write(';'.join(sut) + '\n')
    for k in sorted(gecerli, key=lambda k: -k['askida_1000']):
        f.write(';'.join(str(k.get(s, '')).replace(';', ',') for s in sut) + '\n')
print('\n-> cache/ayrim_gucu.csv  (%d mahalle)' % len(gecerli))
