# -*- coding: utf-8 -*-
"""DISA AKTARIM - uretilen tum veriyi Masaustunde tek klasorde CSV olarak toplar.

Hazir CSV'ler kopyalanir; GeoJSON/GeoJSONL kaynaklar CSV'ye cevrilir (geometri
yerine merkez koordinati + UTM alani yazilir, boyle bir tablo Excel'de acilabilir).
Klasore ayrica 00_icindekiler.csv konur: hangi dosya nedir, kac satir, hangi betik
uretti, hangi tarihte.

Kullanim
  python scripts/disa_aktar_csv.py
"""
import csv, io, json, os, shutil, time
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform

HEDEF = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Veri')
os.makedirs(HEDEF, exist_ok=True)
print('hedef klasor: %s\n' % HEDEF)

icindekiler = []


def kaydet(ad, aciklama, betik, satir):
    icindekiler.append(dict(dosya=ad, aciklama=aciklama, satir=satir, ureten_betik=betik))
    print('  %-34s %7d satir' % (ad, satir))


def satir_say(p):
    with io.open(p, encoding='utf-8-sig') as f:
        return sum(1 for _ in f) - 1


# ---------------------------------------------------------------- hazir CSV'ler
print('hazir CSV kopyalaniyor:')
KOPYA = [
    ('cache/bolge_modelleri.csv', '01_model_sonuclari_cigli_karsiyaka.csv',
     'Uc modelin mahalle bazli ciktisi: cati alani, PVGIS uretim bandi, '
     'AHP oncelik skorlari, guvenilirlik kademesi (53 mahalle x 34 sutun)',
     'bolge_modelleri.py'),
    ('cache/kamu_cigli.csv', '02_kamu_binalari_cigli.csv',
     'OSM kamu hizmeti binalari; tesis alani ve CATI alani ayri sutunda '
     '(okul poligonu bahceyi de kapsiyor, doluluk sutununa bakin)',
     'kamu_binalari.py'),
    ('cache/osm_capraz_kontrol.csv', '03_capraz_kontrol_ms_osm.csv',
     'Microsoft ayak izi ile OSM karsilastirmasi: bina sayisi, cati alani, '
     'ortusme orani, resmi yapi sayisi (Cigli + Karsiyaka + Menemen GMK)',
     'osm_capraz_kontrol.py'),
    ('cache/dogrulama_ges.csv', '04_pvgis_dogrulama_izmirbb_ges.csv',
     'Izmir BB nin kendi 26 gunes tesisi; ozgul verim (kWh/kWp) ile PVGIS '
     'tahmininin karsilastirmasi. tur sutunu: proje_bazli = kullanilabilir, '
     'planlama_kabulu = sabit 1600 carpani, olcum degil',
     'dogrulama_ges.py'),
    ('cache/ihtiyac_analizi.csv', '05_ihtiyac_analizi_cigli.csv',
     'Pilot bolge secimi icin mahalle bazli ihtiyac tablosu (2026-09-09)',
     'ihtiyac_analizi.py'),
    ('cache/ses2023_ilce.csv', '09_tuik_ses2023_tum_ilceler.csv',
     'TUIK Sosyoekonomik Seviye 2023, Turkiye genelinde 973 ilce. SES skoru '
     'hane geliri + egitim suresi + meslek bilesenlerinden; 26 milyon hanenin '
     'tamami icin idari kayitlardan hesaplanmis. Kaynak: TUIK bulten 57942',
     'tuik_ses.py'),
]
for kaynak, hedef_ad, acik, betik in KOPYA:
    p = yol(kaynak)
    if not os.path.exists(p):
        print('  %-34s YOK, atlandi' % hedef_ad); continue
    shutil.copy2(p, os.path.join(HEDEF, hedef_ad))
    kaydet(hedef_ad, acik, betik, satir_say(p))


# ---------------------------------------------------------------- mahalle atamasi
fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))
MAH = [(f['properties']['ilce'], f['properties']['mahalle'], shape(f['geometry']))
       for f in fc['features']]
AGAC = STRtree([m[2] for m in MAH])


def hangi(nokta):
    for i in AGAC.query(nokta):
        if MAH[int(i)][2].contains(nokta):
            return MAH[int(i)][0], MAH[int(i)][1]
    return '', ''


# ---------------------------------------------------------------- OSM binalari
print('\nGeoJSONL -> CSV cevriliyor:')
p = yol('cache/osm_binalar_cigli.geojsonl')
if os.path.exists(p):
    ad = '06_osm_bina_ayak_izleri.csv'
    n = 0
    with io.open(os.path.join(HEDEF, ad), 'w', encoding='utf-8-sig', newline='') as out:
        w = csv.writer(out, delimiter=';')
        w.writerow(['ilce', 'mahalle', 'osm_tip', 'osm_id', 'bina_etiketi',
                    'kat', 'alan_m2', 'merkez_lon', 'merkez_lat'])
        with io.open(p, encoding='utf-8') as f:
            for satir in f:
                d = json.loads(satir)
                g = shape(d['geometry'])
                c = g.representative_point()
                il, mh = hangi(c)
                if not il:
                    continue          # ilce disi (bbox tasmasi)
                pr = d['properties']
                w.writerow([il, mh, pr.get('osm_tip'), pr.get('osm_id'),
                            pr.get('building'), pr.get('levels'),
                            round(transform(to_utm, g).area, 1),
                            round(c.x, 6), round(c.y, 6)])
                n += 1
    kaydet(ad, 'OSM bina ayak izleri, Cigli + Karsiyaka; geometri yerine merkez '
               'koordinati ve UTM alani. Model 1 in birincil girdisi.',
           'osm_capraz_kontrol.py', n)

# ---------------------------------------------------------------- referans kume
p = yol('cache/referans_kume.geojsonl')
if os.path.exists(p):
    ad = '07_sam_kalibrasyon_referans_kumesi.csv'
    kayitlar = [json.loads(s) for s in io.open(p, encoding='utf-8')]
    if kayitlar:
        with io.open(os.path.join(HEDEF, ad), 'w', encoding='utf-8-sig', newline='') as out:
            w = csv.DictWriter(out, fieldnames=list(kayitlar[0].keys()), delimiter=';')
            w.writeheader(); w.writerows(kayitlar)
        kaydet(ad, 'MS ve OSM nin ayni binada ayni alani soyledigi kayitlar '
                   '(+-%15). SAM kalibrasyonunun referansi; yer gercegi DEGIL.',
               'referans_kume.py', len(kayitlar))

# ---------------------------------------------------------------- kamu geojson
p = yol('cache/kamu_cigli.geojson')
if os.path.exists(p):
    j = json.load(open(p, encoding='utf-8'))
    ad = '08_kamu_binalari_cigli_konumlu.csv'
    with io.open(os.path.join(HEDEF, ad), 'w', encoding='utf-8-sig', newline='') as out:
        alanlar = ['mahalle', 'ad', 'tur', 'grup', 'cati_m2', 'tesis_m2', 'doluluk',
                   'bina_ic', 'kaynak', 'isletmeci', 'isletmeci_tur',
                   'osm_tip', 'osm_id', 'lon', 'lat']
        w = csv.DictWriter(out, fieldnames=alanlar, delimiter=';')
        w.writeheader()
        for f in j['features']:
            pr = dict(f['properties'])
            c = shape(f['geometry']).representative_point()
            pr['lon'] = round(c.x, 6); pr['lat'] = round(c.y, 6)
            w.writerow({a: pr.get(a) for a in alanlar})
    kaydet(ad, '02 ile ayni veri, ustune konum (lon/lat) eklenmis - haritaya '
               'dogrudan yuklenebilir.', 'kamu_binalari.py', len(j['features']))


# ------------------------------------------------- SES: Izmir alt kumesi
# Tez metnine giren tablo bu; 973 satirlik kaynak dosyayi her seferinde
# filtrelemek yerine hazir dursun.
p = yol('cache/ses2023_ilce.csv')
if os.path.exists(p):
    ad = '10_tuik_ses2023_izmir_ilceleri.csv'
    with io.open(p, encoding='utf-8-sig') as f:
        okur = csv.DictReader(f, delimiter=';')
        alanlar = okur.fieldnames
        izmir = [r for r in okur if r['il'] == 'İzmir']
    izmir.sort(key=lambda r: float(r['ses']), reverse=True)
    with io.open(os.path.join(HEDEF, ad), 'w', encoding='utf-8-sig', newline='') as out:
        w = csv.DictWriter(out, fieldnames=alanlar, delimiter=';')
        w.writeheader(); w.writerows(izmir)
    kaydet(ad, 'Ayni verinin Izmir alt kumesi, SES skoruna gore sirali (30 ilce). '
               'Karsiyaka 160,59 (TR 14.) ile Cigli 148,13 (TR 45.) arasindaki '
               'fark ust seviye hane payindan geliyor, en alt paydan degil.',
           'tuik_ses.py', len(izmir))

# ---------------------------------------------------------------- icindekiler
ad = '00_icindekiler.csv'
with io.open(os.path.join(HEDEF, ad), 'w', encoding='utf-8-sig', newline='') as out:
    w = csv.DictWriter(out, fieldnames=['dosya', 'aciklama', 'satir', 'ureten_betik'],
                       delimiter=';')
    w.writeheader(); w.writerows(icindekiler)

print('\n%d dosya + icindekiler yazildi' % len(icindekiler))
print('Tumu noktali virgul ayrac, UTF-8 BOM (Excel Turkce karakterleri dogru acar).')
print('-> %s' % HEDEF)
