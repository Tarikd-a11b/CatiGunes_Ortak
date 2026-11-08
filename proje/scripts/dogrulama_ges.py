# -*- coding: utf-8 -*-
"""PVGIS DOGRULAMASI - Izmir BB'nin kendi 26 GES tesisiyle ozgul verim karsilastirmasi.

NEDEN: Faz 2'de uretim tahmini tamamen PVGIS'e dayaniyor ve hicbir bagimsiz kaynakla
karsilastirilmadi. Izmir BB acik veri portalindaki "lisanssiz GES" seti, belediyenin
kendi tesislerinin kurulu gucunu ve yillik uretimini veriyor -> kWh/kWp cinsinden
gercek dunya ozgul verimi. Bizim PVGIS bandimiz bunu kapsiyor mu?

DIKKAT (veri okuma notu): setin sutun basligi "BEKLENEN YILLIK URETIM". 26 kaydin
12'sinde uretim = guc x 1600 tam olarak tutuyor; bunlar olculmus degil, belediyenin
planlama kabulu. Kalan 14 kayit proje bazinda hesaplanmis. Bu betik ikisini AYIRIR;
karistirmak dogrulamayi anlamsiz kilar.

Girdi : cache/acikveri/lisanssiz_ges.csv
        cache/pvgis_tablo.json  (Evka-5 izgarasi; yoksa PVGIS'e sorulur)
Cikti : cache/dogrulama_ges.csv, ekrana ozet
"""
import csv, io, json, os, time
import numpy as np, requests

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

IZMIR_LAT, IZMIR_LON = 38.42, 27.14      # Konak; Izmir genelinde ozgul verim ~sabit
KAYIP = 14                               # Faz 2 ile ayni sistem kaybi
PLANLAMA_KABULU = 1600.0                 # belediyenin sabit carpani (asagida tespit edilir)


def f(x):
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return None


# --- 1. PVGIS referans degerleri ---------------------------------------------
PV_CACHE = yol('cache/pvgis_dogrulama.json')
pv = json.load(open(PV_CACHE)) if os.path.exists(PV_CACHE) else {}


def ozgul(egim, aspect):
    """1 kWp icin yillik kWh. PVGIS aspect: 0=guney, -90=dogu, +90=bati, 180=kuzey."""
    k = '%d|%d' % (egim, aspect)
    if k not in pv:
        r = requests.get('https://re.jrc.ec.europa.eu/api/v5_3/PVcalc',
                         params=dict(lat=IZMIR_LAT, lon=IZMIR_LON, peakpower=1,
                                     loss=KAYIP, angle=egim, aspect=aspect,
                                     outputformat='json'), timeout=90)
        r.raise_for_status()
        pv[k] = float(r.json()['outputs']['totals']['fixed']['E_y'])
        json.dump(pv, open(PV_CACHE, 'w'))
        time.sleep(0.3)
    return pv[k]


duz = ozgul(0, 0)
guney30 = ozgul(30, 0)
guney15 = ozgul(15, 0)
dogu30 = ozgul(30, -90)
bati30 = ozgul(30, 90)
kuzey30 = ozgul(30, 180)
print('PVGIS Izmir (kayip %%%d, 1 kWp):' % KAYIP)
print('  duz 0 derece      : %.0f kWh/kWp' % duz)
print('  guney 15 derece   : %.0f' % guney15)
print('  guney 30 derece   : %.0f   <- teorik en iyi' % guney30)
print('  dogu 30 / bati 30 : %.0f / %.0f' % (dogu30, bati30))
print('  kuzey 30 derece   : %.0f   <- en kotu' % kuzey30)

# --- 2. tesisler --------------------------------------------------------------
satirlar = list(csv.DictReader(io.open(yol('cache/acikveri/lisanssiz_ges.csv'),
                                       encoding='utf-8-sig'), delimiter=';'))
GUC = 'TOPLAM GÜÇ (kW)'
URETIM = [k for k in satirlar[0] if 'ÜRETİM' in k][0]

tesis = []
for r in satirlar:
    kw, kwh = f(r[GUC]), f(r[URETIM])
    if not kw or not kwh:
        continue
    ov = kwh / kw
    # guc x 1600 tam tutuyorsa: olculmus degil, sabit planlama carpani
    sabit = abs(kwh - kw * PLANLAMA_KABULU) < 1.0
    tesis.append(dict(ad=r['PROJE ADI'].strip(), kW=kw, kWh=kwh, ozgul=ov,
                      tur='planlama_kabulu' if sabit else 'proje_bazli',
                      aciklama=(r.get('AÇIKLAMA') or '').strip()))

proje = [t for t in tesis if t['tur'] == 'proje_bazli']
kabul = [t for t in tesis if t['tur'] == 'planlama_kabulu']
print('\n%d tesis: %d proje bazli hesap, %d sabit planlama kabulu (guc x %.0f)'
      % (len(tesis), len(proje), len(kabul), PLANLAMA_KABULU))

# --- 3. karsilastirma ---------------------------------------------------------
o = np.array([t['ozgul'] for t in proje])
print('\n=== PROJE BAZLI %d TESIS (dogrulama icin kullanilabilir grup) ===' % len(proje))
print('  ozgul verim  : medyan %.0f | ortalama %.0f | aralik %.0f - %.0f kWh/kWp'
      % (np.median(o), o.mean(), o.min(), o.max()))
print('  kurulu guc   : toplam %.0f kW (%.0f - %.0f kW)'
      % (sum(t['kW'] for t in proje), min(t['kW'] for t in proje),
         max(t['kW'] for t in proje)))
icinde = int(((o >= duz) & (o <= guney30)).sum())
print('  PVGIS duz(%.0f) - guney30(%.0f) bandinin ICINDE : %d/%d tesis'
      % (duz, guney30, icinde, len(o)))
print('  bandin ustunde %d, altinda %d'
      % (int((o > guney30).sum()), int((o < duz).sum())))
print('  medyan tesis / PVGIS duz     = %.3f' % (np.median(o) / duz))
print('  medyan tesis / PVGIS guney30 = %.3f' % (np.median(o) / guney30))

print('\n=== SABIT KABUL GRUBU (%d tesis) ===' % len(kabul))
print('  hepsi tam %.0f kWh/kWp -- bu bir OLCUM DEGIL, belediyenin planlama carpani.'
      % PLANLAMA_KABULU)
print('  PVGIS guney30 (teorik en iyi) = %.0f  ->  kabul/teorik = %.3f'
      % (guney30, PLANLAMA_KABULU / guney30))
if PLANLAMA_KABULU > guney30:
    print('  >> Belediyenin kabulu, IDEAL yonelimli bir catinin PVGIS tahmininden bile'
          ' %.0f kWh/kWp YUKSEK. Gercek catilarda ulasilmasi beklenmemeli.'
          % (PLANLAMA_KABULU - guney30))

print('\n  --- proje bazli tesisler, ozgul verime gore ---')
print('  %-42s %8s %10s %8s' % ('tesis', 'kW', 'kWh/yil', 'kWh/kWp'))
for t in sorted(proje, key=lambda x: -x['ozgul']):
    print('  %-42s %8.1f %10.0f %8.0f' % (t['ad'][:42], t['kW'], t['kWh'], t['ozgul']))

# --- 4. cikti -----------------------------------------------------------------
sutun = ['ad', 'kW', 'kWh', 'ozgul', 'tur', 'aciklama']
with io.open(yol('cache/dogrulama_ges.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=sutun + ['pvgis_duz', 'pvgis_guney30', 'bant_ici'],
                       delimiter=';')
    w.writeheader()
    for t in sorted(tesis, key=lambda x: -x['ozgul']):
        d = {k: t[k] for k in sutun}
        d['pvgis_duz'] = round(duz)
        d['pvgis_guney30'] = round(guney30)
        d['bant_ici'] = int(duz <= t['ozgul'] <= guney30)
        w.writerow(d)
print('\n-> cache/dogrulama_ges.csv')
