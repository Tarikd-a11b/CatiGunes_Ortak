# -*- coding: utf-8 -*-
"""OSM <-> Microsoft ayak izi CAPRAZ KONTROLU - Cigli 26 mahalle (+ Menemen GMK).

NEDEN: ihtiyac analizinde MS ayak izi / resmi yapi orani Cigli'de 0,27 - 2,97
arasinda geziniyor. Iki ayri hata bu tek sayinin icinde saklaniyor olabilir:
  (a) apartman mahallelerinde MS binalari KACIRIYOR  -> oran < 1
  (b) kirsalda sera/mustemilat BINA sayiliyor        -> oran > 1
Ucuncu bir kaynak (OSM) olmadan ikisi ayirt edilemez. Bu betik o ucuncu kaynagi
getirir ve her mahalle icin uc sayiyi yan yana koyar: MS / OSM / resmi.

Girdiler
  cache/mahalle_sinirlari.geojson     OSM idari sinirlar (27 mahalle)
  cache/ms_izmir_122100310.geojsonl   Microsoft bina ayak izleri (391.215 bina)
  cache/acikveri/mahalle_bina_sayisi.csv  Izmir BB resmi yapi sayisi

Cikti
  cache/osm_binalar_cigli.geojsonl    OSM bina poligonlari (onbellek, tekrar kosuda kullanilir)
  cache/osm_capraz_kontrol.csv        mahalle bazli karsilastirma tablosu
  cache/osm_capraz_kontrol.json       ayni veri + meta

Kullanim
  python scripts/osm_capraz_kontrol.py            # onbellek varsa Overpass'e gitmez
  python scripts/osm_capraz_kontrol.py --yenile   # karolari yeniden indirir
"""
import csv, io, json, math, os, sys, time, unicodedata, urllib.parse
import numpy as np, requests
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/1.0 (akademik arastirma)'}

KARO = 0.050                      # derece - Overpass zaman asimini onlemek icin
ONBELLEK = yol('cache/osm_binalar_cigli.geojsonl')
KARO_DIZIN = yol('cache/osm_karo')
YENILE = '--yenile' in sys.argv
BASARISIZ = []          # indirilemeyen karolar; sessizce gecilmez, sonda raporlanir


def sadelestir(s):
    """Turkce duyarli eslestirme anahtari ('I'.lower() birlesik nokta uretir)."""
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def sayi(x, vars_=0.0):
    try:
        return float(str(x).replace('.', '').replace(',', '.')) if ',' in str(x) else float(x)
    except Exception:
        return vars_


# ============================ 1. sinirlar ====================================
fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))
mahalleler = []
for f in fc['features']:
    p = f['properties']
    mahalleler.append(dict(ilce=p['ilce'], mahalle=p['mahalle'], geom=shape(f['geometry']),
                           alan_km2=p['alan_km2']))
AGAC = STRtree([m['geom'] for m in mahalleler])
INDEKS = {sadelestir(m['mahalle']): m for m in mahalleler}
print('%d mahalle siniri yuklendi' % len(mahalleler))

lon0 = min(m['geom'].bounds[0] for m in mahalleler)
lat0 = min(m['geom'].bounds[1] for m in mahalleler)
lon1 = max(m['geom'].bounds[2] for m in mahalleler)
lat1 = max(m['geom'].bounds[3] for m in mahalleler)
print('kapsam bbox: %.4f %.4f %.4f %.4f' % (lon0, lat0, lon1, lat1))


def hangi_mahalle(g):
    """Poligonun temsili noktasi hangi mahallede? (None = disarida)"""
    c = g.representative_point()
    for i in AGAC.query(c):
        m = mahalleler[int(i)]
        if m['geom'].contains(c):
            return m
    return None


# ============================ 2. OSM binalari (Overpass) =====================
AYNALAR = ['https://overpass-api.de/api/interpreter',
           'https://overpass.kumi.systems/api/interpreter']


def overpass(sorgu, deneme=6):
    """GET ile sorgula (POST bazi aglarda bloklu). 429/504'te bekle, aynayi degistir."""
    for i in range(deneme):
        uc = AYNALAR[i % len(AYNALAR)]
        try:
            r = requests.get(uc + '?data=' + urllib.parse.quote(sorgu),
                             headers=UA, timeout=120)
            if r.status_code == 200:
                return r.json()
            print('     HTTP %d (%s)' % (r.status_code, uc.split('/')[2]))
        except Exception as e:
            print('     hata: %s' % str(e)[:80])
        bekle = 10 * (i + 1)
        print('     %d s bekleniyor...' % bekle)
        time.sleep(bekle)
    return None


def karolari_indir():
    os.makedirs(KARO_DIZIN, exist_ok=True)
    karolar = []
    y = lat0
    while y < lat1:
        x = lon0
        while x < lon1:
            karolar.append((x, y, min(x + KARO, lon1), min(y + KARO, lat1)))
            x += KARO
        y += KARO
    # sadece bir mahalleyle kesisen karolar
    karolar = [k for k in karolar
               if any(m['geom'].intersects(box(*k)) for m in mahalleler)]
    print('%d karo indirilecek (%.3f derece)' % (len(karolar), KARO))

    # Yogun karolar Overpass'te 504 veriyor. Basarisiz karo ATLANMAZ, dorde bolunur:
    # bir karonun sessizce dusmesi o karodaki mahalleleri "OSM'de bina yok" gibi
    # gosterir (ilk kosuda EVKA-2/EVKA-6 tam olarak boyle yanlis okundu).
    kuyruk = [(k, 0) for k in karolar]
    toplam = len(kuyruk); n = 0
    while kuyruk:
        (a, b, c, d), derinlik = kuyruk.pop(0)
        n += 1
        dosya = os.path.join(KARO_DIZIN, 'k_%.4f_%.4f_%.4f_%.4f.json' % (a, b, c, d))
        if os.path.exists(dosya) and not YENILE:
            continue
        sorgu = ('[out:json][timeout:180];('
                 'way["building"](%.5f,%.5f,%.5f,%.5f);'
                 'relation["building"](%.5f,%.5f,%.5f,%.5f););'
                 'out geom qt;' % (b, a, d, c, b, a, d, c))
        print('  karo %d/%d (derinlik %d) ...' % (n, toplam, derinlik), end=' ', flush=True)
        j = overpass(sorgu, deneme=3)
        if j is None:
            if derinlik >= 3:
                print('BASARISIZ - bolunemedi, sinir derinlik')
                BASARISIZ.append((a, b, c, d))
                continue
            mx, my = (a + c) / 2.0, (b + d) / 2.0
            alt = [(a, b, mx, my), (mx, b, c, my), (a, my, mx, d), (mx, my, c, d)]
            kuyruk = [(k, derinlik + 1) for k in alt] + kuyruk
            toplam += 4
            print('504/hata -> dorde bolundu')
            continue
        json.dump(j, open(dosya, 'w'), separators=(',', ':'))
        print('%d nesne' % len(j.get('elements', [])))
        time.sleep(1.5)


def karolardan_poligon():
    """Karo dosyalarindan tekil (id bazli) bina poligonlari uret."""
    gorulen = set()
    binalar = []
    for ad in sorted(os.listdir(KARO_DIZIN)):
        if not ad.endswith('.json'):
            continue
        j = json.load(open(os.path.join(KARO_DIZIN, ad)))
        for e in j.get('elements', []):
            anahtar = (e['type'], e['id'])
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            try:
                if e['type'] == 'way':
                    hat = [(p['lon'], p['lat']) for p in e.get('geometry', [])]
                    if len(hat) < 4:
                        continue
                    g = Polygon(hat)
                else:                                    # relation (multipolygon)
                    dis = []
                    for u in e.get('members', []):
                        if u.get('role') == 'outer' and u.get('geometry'):
                            hat = [(p['lon'], p['lat']) for p in u['geometry']]
                            if len(hat) >= 4:
                                dis.append(Polygon(hat))
                    if not dis:
                        continue
                    g = MultiPolygon(dis) if len(dis) > 1 else dis[0]
                if not g.is_valid:
                    g = g.buffer(0)
                if g.is_empty or g.area <= 0:
                    continue
            except Exception:
                continue
            binalar.append((e['type'], e['id'], e.get('tags', {}), g))
    return binalar


if not os.path.exists(ONBELLEK) or YENILE or '--karo' in sys.argv:
    karolari_indir()
    if BASARISIZ:
        print('!! %d karo indirilemedi -> bu karolardaki mahalleler EKSIK sayilir:' % len(BASARISIZ))
        for a, b, c, d in BASARISIZ:
            etkilenen = [m['mahalle'] for m in mahalleler if m['geom'].intersects(box(a, b, c, d))]
            print('   %.4f %.4f %.4f %.4f -> %s' % (a, b, c, d, ', '.join(etkilenen)))
        sys.exit('Eksik karo varken tablo uretilmez; tekrar calistir.')
    print('karolar birlestiriliyor...')
    binalar = karolardan_poligon()
    with io.open(ONBELLEK, 'w', encoding='utf-8') as f:
        for tip, oid, etiket, g in binalar:
            f.write(json.dumps(dict(type='Feature',
                                    properties=dict(osm_tip=tip, osm_id=oid,
                                                    building=etiket.get('building'),
                                                    amenity=etiket.get('amenity'),
                                                    levels=etiket.get('building:levels')),
                                    geometry=g.__geo_interface__),
                               ensure_ascii=False) + '\n')
    print('onbellek yazildi: %d bina -> %s' % (len(binalar), ONBELLEK))

print('OSM binalari okunuyor...')
osm = []
with io.open(ONBELLEK, encoding='utf-8') as f:
    for satir in f:
        d = json.loads(satir)
        osm.append((d['properties'], shape(d['geometry'])))
print('%d OSM bina poligonu' % len(osm))

# ============================ 3. mahalleye dagitim ===========================
for m in mahalleler:
    m['osm_n'] = 0; m['osm_alan'] = 0.0; m['osm_alanlar'] = []
    m['ayak_n'] = 0; m['ayak_alan'] = 0.0; m['ayak_alanlar'] = []

for prop, g in osm:
    m = hangi_mahalle(g)
    if m is None:
        continue
    a = transform(to_utm, g).area
    if a < 10 or a > 50000:              # kulube / hatali dev poligon
        continue
    m['osm_n'] += 1; m['osm_alan'] += a; m['osm_alanlar'].append(a)

# MS binalari tek geciste taranir: mahalleye dagitim + OSM ile ortusme testi.
print('MS ayak izleri taraniyor (mahalle + OSM eslesmesi)...')
osm_agac = STRtree([g for _, g in osm])
for m in mahalleler:
    m['ms_eslesen'] = 0
eslesen = 0; ms_toplam = 0
t0 = time.time(); n = 0
with io.open(yol('cache/ms_izmir_122100310.geojsonl'), encoding='utf-8') as f:
    for satir in f:
        n += 1
        try:
            g = shape(json.loads(satir)['geometry'])
        except Exception:
            continue
        m = hangi_mahalle(g)
        if m is None:
            continue
        a = transform(to_utm, g).area
        m['ayak_n'] += 1; m['ayak_alan'] += a; m['ayak_alanlar'].append(a)
        ms_toplam += 1
        c = g.representative_point()
        for i in osm_agac.query(c):
            if osm[int(i)][1].contains(c):
                m['ms_eslesen'] += 1; eslesen += 1
                break
        if n % 100000 == 0:
            print('   %d/391215 (%.0f s)' % (n, time.time() - t0))
print('MS taramasi bitti (%.0f s)' % (time.time() - t0))
print('MS %d bina (kapsam icinde), OSM ile ortusen %d (%%%.1f)'
      % (ms_toplam, eslesen, 100.0 * eslesen / max(ms_toplam, 1)))

# ============================ 4. resmi yapi sayisi ===========================
for r in csv.DictReader(io.open(yol('cache/acikveri/mahalle_bina_sayisi.csv'),
                                encoding='utf-8-sig'), delimiter=';'):
    m = INDEKS.get(sadelestir(r['MAHALLE']))
    if m and sadelestir(r['ILCE']) == sadelestir(m['ilce']):
        m['resmi_yapi'] = int(sayi(r['YAPI']))

# ============================ 5. tablo =======================================
satirlar = []
for m in sorted(mahalleler, key=lambda x: (x['ilce'], x['mahalle'])):
    resmi = m.get('resmi_yapi')
    ms_n, osm_n = m['ayak_n'], m['osm_n']
    satirlar.append(dict(
        ilce=m['ilce'], mahalle=m['mahalle'], alan_km2=m['alan_km2'],
        resmi_yapi=resmi, ms_n=ms_n, osm_n=osm_n,
        ms_resmi=round(ms_n / resmi, 3) if resmi else None,
        osm_resmi=round(osm_n / resmi, 3) if resmi else None,
        ms_osm=round(ms_n / osm_n, 3) if osm_n else None,
        ms_eslesen=m.get('ms_eslesen', 0),
        ms_eslesme_orani=round(m.get('ms_eslesen', 0) / ms_n, 3) if ms_n else None,
        ms_alan_ha=round(m['ayak_alan'] / 1e4, 2),
        osm_alan_ha=round(m['osm_alan'] / 1e4, 2),
        alan_ms_osm=round(m['ayak_alan'] / m['osm_alan'], 3) if m['osm_alan'] else None,
        ms_medyan_m2=round(float(np.median(m['ayak_alanlar'])), 1) if m['ayak_alanlar'] else None,
        osm_medyan_m2=round(float(np.median(m['osm_alanlar'])), 1) if m['osm_alanlar'] else None,
    ))

with io.open(yol('cache/osm_capraz_kontrol.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()), delimiter=';')
    w.writeheader(); w.writerows(satirlar)

json.dump(dict(uretim=time.strftime('%Y-%m-%d %H:%M'),
               kaynak=dict(osm='Overpass API, way+relation building, karo %.3f derece' % KARO,
                           ms='Microsoft Global ML Building Footprints, karo 122100310',
                           resmi='Izmir BB acik veri, mahalle_bina_sayisi.csv'),
               filtre='OSM: 10 m2 < alan < 50.000 m2',
               ms_toplam=ms_toplam, ms_osm_ortusen=eslesen,
               satirlar=satirlar),
          io.open(yol('cache/osm_capraz_kontrol.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ============================ 6. ekrana ozet =================================
print('\n%-28s %7s %7s %7s  %6s %6s %6s' %
      ('MAHALLE', 'resmi', 'MS', 'OSM', 'MS/res', 'OSM/re', 'eslesme'))
print('-' * 78)
for s in satirlar:
    print('%-28s %7s %7d %7d  %6s %6s %6s' %
          (s['mahalle'][:28], s['resmi_yapi'] if s['resmi_yapi'] else '-',
           s['ms_n'], s['osm_n'],
           '%.2f' % s['ms_resmi'] if s['ms_resmi'] else '-',
           '%.2f' % s['osm_resmi'] if s['osm_resmi'] else '-',
           '%.2f' % s['ms_eslesme_orani'] if s['ms_eslesme_orani'] else '-'))

ms_r = [s['ms_resmi'] for s in satirlar if s['ms_resmi']]
osm_r = [s['osm_resmi'] for s in satirlar if s['osm_resmi']]
print('\nMS/resmi   : medyan %.2f  aralik %.2f - %.2f  CV %.2f'
      % (np.median(ms_r), min(ms_r), max(ms_r), np.std(ms_r) / np.mean(ms_r)))
print('OSM/resmi  : medyan %.2f  aralik %.2f - %.2f  CV %.2f'
      % (np.median(osm_r), min(osm_r), max(osm_r), np.std(osm_r) / np.mean(osm_r)))
print('\ncikti: cache/osm_capraz_kontrol.csv + .json')
