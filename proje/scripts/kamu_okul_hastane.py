# -*- coding: utf-8 -*-
"""Kamu kapsami daraltma (2026-10-15, hoca karari): Cigli'de YALNIZ devlete ait OKUL ve HASTANE.
Girdi : veri/ham/kamu/kamu_tesisleri_cigli_osm.geojson (208 kamu hizmeti tesisi, OSM islev etiketi)
Cikti : veri/islenmis/kamu_okul_hastane_cigli.geojson   -> kapsamdaki kamu okul + hastaneler
        veri/islenmis/kamu_belirsiz_kontrol.geojson     -> mulkiyeti OSM'den cikmayanlar (MEB listesiyle bakilacak)
        veri/inceleme/kamu_secim_kontrol.xlsx           -> 208 kaydin her biri icin karar + gerekce
Kurallar (sirayla): elle karar listesi > operator:type > operator MEB/Saglik Bak./devlet univ. > meb.k12.tr sitesi >
ad (Ozel/Koleji/Okullari = ozel; Ilkokulu/Ortaokulu/Lisesi/Ilkogretim = kamu) > adsiz bina, adli kampusun icindeyse ondan miras.
Aile sagligi merkezi, poliklinik, klinik, kurs merkezi: 'hastane'/'okul' degil -> kapsam disi.
2026-10-17 (kullanici karari): DEVLET UNIVERSITESI de kapsamda -> tur='universite'. Cigli'de Izmir Katip Celebi Univ.
  YALNIZ Balatcik ana kampusu (relation/6904659); Aydinlikevler yerleskesi kullanici karariyla disarida. Ana kampus kamu_tesisleri sorgusunda geometrisiz
  geldigi icin ayri dosyadan okunur: veri/ham/kamu/ikcu_kampus_osm.geojson. Kampus icindeki adsiz binalar kampustan miras."""
import json, os
import pandas as pd
from shapely.geometry import shape

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = lambda *p: os.path.join(KOK, 'veri', *p)
os.makedirs(H('islenmis'), exist_ok=True)
F = json.load(open(H('ham', 'kamu', 'kamu_tesisleri_cigli_osm.geojson'), encoding='utf-8'))['features']
_var = {f['properties']['osm'] for f in F}
F += [f for f in json.load(open(H('ham', 'kamu', 'ikcu_kampus_osm.geojson'), encoding='utf-8'))['features']
      if f['properties']['osm'] not in _var]

# elle karar: OSM etiketinden cikmayan ya da etiketi yanlis olanlar (kaynak: ad / web sitesi / adres)
ELLE = {
    'way/503350239': ('hastane', 'kamu', 'Çiğli Eğitim ve Araştırma Hastanesi',
                      'adsiz building=hospital, 5 kat; adres Yeni Mah. 8780/1 Sk. No:18 = Cigli EAH (Saglik Bak.)'),
    'way/879136910': ('hastane', 'kamu', None, 'IKCU Dis Hekimligi Fakultesi binasi; devlet universitesi hastanesi'),
    'node/9658210078': ('okul', 'ozel', None, 'Teoti Anaokulu: operator:type=public yanlis, ticari zincir (teotianaokullari.com)'),
    'way/156842271': ('okul', 'ozel', None, 'Cakabey Okullari, operator:type=private_for_profit'),
    'way/503429091': ('okul', 'ozel', None, 'Cakabey kampusu binasi'),
    'way/503429099': ('okul', 'ozel', None, 'Cakabey kampusu binasi'),
    'way/392528157': ('kapsam_disi', None, None, 'TEGV egitim parki - okul degil (vakif)'),
    'node/12119758002': ('kapsam_disi', None, None, 'IBB Meslek Fabrikasi kurs merkezi - okul degil'),
    'node/13473681649': ('okul', 'kamu', None, 'Yuvamiz Izmir, operator Izmir Buyuksehir Belediyesi (okul oncesi)'),
    'relation/6904659': ('universite', 'kamu', 'İzmir Kâtip Çelebi Üniversitesi', 'devlet universitesi ana kampus (Balatcik); 2026-10-17 kapsama alindi'),
    'way/376444055': ('kapsam_disi', None, None, 'IKCU Aydinlikevler yerleskesi: kullanici yalniz Balatcik ana kampusunu istedi (2026-10-17)'),
    'way/1147404424': ('kapsam_disi', None, None, 'Izmir Anadolu Ogretmen Lisesi: MEB resmi listesinde yok (ogretmen liseleri 2014te kapandi), '
                                                  '930 m icinde MEB okulu yok; faal okul degil (2026-10-17 kullanici karari)'),
}
# OSM'deki eski/kisa adlar -> MEB resmi okul adi (veri/ham/kamu/meb_cigli_resmi_okullar_2026-10-17.json; konumla eslesti, <=29 m)
MEB_AD = {
    '80. Yıl Küçük Çiğli İlkokulu': '80.Yıl Küçükçiğli İlkokulu',
    'Büyük Çiğli Anadolu Lisesi': 'Büyükçiğli Anadolu Lisesi',
    'Büyük Çiğli İlköğretim Okulu': 'Büyükçiğli İlkokulu',
    'Evka 6 İlkokulu': 'Şehit Uğur Görkem Harmankaya İlkokulu',
    'Gülen KORA Ortaokulu': 'Gülen Kora Ortaokulu',
    'Maltepe İlköğretim Okulu': 'Maltepe İlkokulu',
    'Mehmet Hikmet Kaşerci Ortaokulu': 'Mehmet-Hikmet Kaşerci Ortaokulu',
    'Münevver Öğretmen Ortaokulu': 'Münevver Öğretmen İlkokulu ve Ortaokulu',
    'Naime Tömek Lisesi': 'Çiğli Naime TÖMEK Ticaret Mesleki ve Teknik Anadolu Lisesi',
    'Toki İlköğretim Okulu': 'TOKİ İlkokulu',
    'Turan Çakın İlköğretim Okulu': 'Turan Çakın İlkokulu',
    'Tüpraş Mahmut Esat Bozkurt İ.Ö.O.': 'Tüpraş Mahmut Esat Bozkurt İlkokulu ve Ortaokulu',
    'Yıldız Tınas İzmiroğlu Anadolu Lisesi': 'Çiğli Yıldız Tınas İzmiroğlu Anadolu Lisesi',
    'İMKB Anadolu Meslek Lisesi': 'Çiğli Borsa İstanbul Mesleki ve Teknik Anadolu Lisesi',
    'Çiğli Rotary Ticaret Meslek Lisesi': 'Çiğli Rotary Ticaret Mesleki ve Teknik Anadolu Lisesi',
    'İzzet Gökçimen İlöğretim Okulu': 'İzzet Gökçimen Ortaokulu',
    'Şehit Ali Karaoğlan Çok Programlı Anadolu Lisesi': 'Şehit Ali Karaoğlan Anadolu Lisesi ve Mesleki ve Teknik Anadolu Lisesi',
}
OZEL_AD = ('özel', 'kolej', 'okulları', 'fen bilimleri', 'klinik', 'tıp merkezi', 'poliklini', 'acıbadem',
           'metropol', 'ekol ')
KAMU_AD = ('ilkokulu', 'ortaokulu', 'lisesi', 'ilköğretim', 'ilöğretim', 'i.ö.o', 'bilim ve sanat merkezi')
KAMU_OPER = ('milli eğitim', 'millî eğitim', 'sağlık bakanlığı', 'kâtip çelebi', 'katip çelebi', 'büyükşehir belediyesi')


def kucuk(s):  # Turkce: 'İ'.lower() birlesik nokta uretir
    return (s or '').replace('İ', 'i').replace('I', 'ı').lower()


def tur(p):
    e = p['eslesen_etiket']
    if 'hospital' in e: return 'hastane'
    if 'university' in e: return 'universite'
    if any(k in e for k in ('school', 'kindergarten')): return 'okul'
    return None


def sahiplik(p):
    ad = kucuk(p.get('name')); op = kucuk(p.get('operator')); ot = p.get('operator:type') or ''
    if ot in ('private', 'private_for_profit', 'business'): return 'ozel', 'operator:type=' + ot
    if any(k in op for k in KAMU_OPER): return 'kamu', 'operator=' + p['operator']
    if ot in ('government', 'public'): return 'kamu', 'operator:type=' + ot
    if 'meb.k12.tr' in (p.get('website') or ''): return 'kamu', 'web sitesi meb.k12.tr'
    if any(k in ad for k in OZEL_AD) or (tur(p) == 'hastane' and ad): return 'ozel', 'ad: ' + p['name']
    if any(k in ad for k in KAMU_AD): return 'kamu', 'ad: MEB okul adlandirmasi'
    return None, None


kayit = []
for f in F:
    p = f['properties']; g = shape(f['geometry'])
    r = {'osm': p['osm'], 'ad': p.get('name'), 'etiket': p['eslesen_etiket'], 'operator': p.get('operator'),
         'geometri': g.geom_type, 'tesis_alan_m2': p.get('tesis_alan_m2'), '_g': g, '_f': f}
    if p['osm'] in ELLE:
        r['tur'], r['sahiplik'], ad, r['gerekce'] = ELLE[p['osm']]
        if ad: r['ad'] = ad
    else:
        r['tur'] = tur(p) or 'kapsam_disi'
        r['sahiplik'], r['gerekce'] = sahiplik(p) if r['tur'] != 'kapsam_disi' else (None, 'islev: ' + p['eslesen_etiket'])
    kayit.append(r)

# adsiz/kararsiz kayit: icinde/disinda adli ve karari belli bir kayit varsa miras al
KURUM = ('okul', 'hastane', 'universite')
belli = [r for r in kayit if r['tur'] in KURUM and r['sahiplik'] and r['geometri'] != 'Point']
for r in kayit:
    if r['tur'] in KURUM and not r['sahiplik']:
        kap = [b for b in belli if b is not r and (b['_g'].contains(r['_g'].representative_point())
                                                    or r['_g'].contains(b['_g'].representative_point()))]
        if kap:
            b = max(kap, key=lambda b: b['_g'].area)
            r['sahiplik'] = b['sahiplik']; r['gerekce'] = 'kampus/bina eslesmesi: %s (%s)' % (b['ad'], b['osm'])
            if not r['ad'] and b['_g'].contains(r['_g'].representative_point()): r['ad'] = b['ad']
    if r['tur'] in KURUM and not r['sahiplik']:
        r['sahiplik'] = 'belirsiz'; r['gerekce'] = r.get('gerekce') or 'OSM\'de ad/isletmeci yok'

for r in kayit:
    if r['ad'] in MEB_AD: r['ad'] = MEB_AD[r['ad']]

# karar
for r in kayit:
    r['karar'] = ('KAPSAMDA' if r['sahiplik'] == 'kamu' else
                  'KONTROL (MEB listesi)' if r['sahiplik'] == 'belirsiz' else
                  'cikarildi: ozel' if r['sahiplik'] == 'ozel' else 'cikarildi: okul/hastane degil')


def yaz(ad, sec):
    oz = [{'type': 'Feature', 'geometry': r['_f']['geometry'],
           'properties': {'osm': r['osm'], 'ad': r['ad'], 'tur': r['tur'], 'sahiplik': r['sahiplik'],
                          'gerekce': r['gerekce'], 'tesis_alan_m2': r['tesis_alan_m2'],
                          'etiketler': {k: v for k, v in r['_f']['properties'].items() if k not in ('osm', 'tesis_alan_m2')}}}
          for r in sec]
    json.dump({'type': 'FeatureCollection', 'features': oz}, open(H('islenmis', ad), 'w', encoding='utf-8'),
              ensure_ascii=False)
    return len(oz)


n1 = yaz('kamu_okul_hastane_cigli.geojson', [r for r in kayit if r['karar'] == 'KAPSAMDA'])
n2 = yaz('kamu_belirsiz_kontrol.geojson', [r for r in kayit if r['sahiplik'] == 'belirsiz'])
df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith('_')} for r in kayit])
df = df.sort_values(['karar', 'tur', 'ad'], na_position='last')
with pd.ExcelWriter(H('inceleme', 'kamu_secim_kontrol.xlsx'), engine='openpyxl') as w:
    df.to_excel(w, sheet_name='Kamu_secim', index=False)
    ws = w.sheets['Kamu_secim']; ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(60, max(10, *(len(str(c.value or '')) for c in col)) + 2)
print(df.groupby(['karar', 'tur'], dropna=False).size().to_string())
print('kapsamda %d, kontrol %d' % (n1, n2))
