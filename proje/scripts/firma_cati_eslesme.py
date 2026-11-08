# -*- coding: utf-8 -*-
"""IAOSB firmasi -> OSB catisi (cati_id) eslemesi (2026-10-21).
Girdi : veri/ham/iaosb/osb_firmalar_birlesik.csv (764 firma), Desktop/CatiGunes_Model_Verisi/catilar.gpkg,
        veri/ham/osm/osm_yollar_osb_*.json + osm_adli_osb_*.json + overpass_bina_ham_ataturk_osb.json
Cikti : veri/ham/iaosb/firma_cati_eslesme.csv  (model_verisi.py -> Model_Verisi/firmalar/)
Oncelik: 0) elle       : veri/elle/firma_cati_elle.csv (scripts/firma_cati_onay.py; insan Google Maps'e bakip secti)
         1) kesin_osm  : OSM binasinda firma adi yaziyor (elle ayiklandi, KESIN sozlugu)
         2) geocode    : Google Geocoding kapi noktasi (ROOFTOP/RANGE_INTERPOLATED, sokak+no tutuyor) -> icindeki/<=GEO_TAMPON m catı
         3) sokak_aday : firmanin sokagina cephe veren catilar (liste)
Anahtar: TomTom (kartsiz, 2.500 istek/gun) env TOMTOM_API_KEY ya da CatiGunes/.tomtom_key; yoksa Google env GOOGLE_MAPS_API_KEY ya da .google_maps_key. Ikisi de yoksa 2. adim atlanir.
Google kosullari koordinatin en fazla 30 gun saklanmasina izin veriyor -> koordinatlar yalniz cache/geocode_google.json'da
(tarihli); kalici ciktiya KOORDINAT YAZILMAZ, yalniz cati_id. 30 gunden eski onbellek kayitlari otomatik silinir.
  python scripts/firma_cati_eslesme.py"""
import json, os, re, sys, time, unicodedata, datetime as dt
import pandas as pd, geopandas as gpd, requests
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, unary_union

sys.stdout.reconfigure(encoding='utf-8')
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MODEL = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi', 'catilar.gpkg')
ONBELLEK = os.path.join(KOK, 'cache', 'geocode_google.json')
CIKTI = V('ham', 'iaosb', 'firma_cati_eslesme.csv')
UTM = 32635
CEPHE_M, CEPHE_PAY_M, GEO_TAMPON = 40, 15, 25   # sokaga cephe: <=40 m ve en yakin sokaktan en fazla 15 m uzak
GECERLI = {'ROOFTOP', 'RANGE_INTERPOLATED'}

# Elle ayiklanmis kesin eslesmeler: OSM nesnesi -> firma url son parcasi (OSM adi + firma adresi birlikte kontrol edildi)
KESIN = {
    'way/905813167': 'jefe-gida-ic-ve-dis-ticaret-san-ltd-sti',
    'way/865659399': 'steel-mold-makina-san-tic-ltd-sti',
    'way/503177006': 'aytas-gida-ve-ihtiyac-maddeleri-tarim-ticaret-ve-sanayi-a-s',
    'way/503183924': 'sanli-ilac-sanayi-a-s',
    'way/503183926': 'eltas-transformator-san-ve-tic-a-s',
    'way/503183944': 'cms-jant-ve-makina-sanayii-a-s',
    'way/503183945': 'nural-plastik-amb-san-ve-tic-a-s',
    'way/503183946': 'mdk-makina-dizayn-kalip-sanayi-ve-ticaret-a-s',
    'way/503177007': 'erciyes-demir-sanayi-ve-ticaret-a-s',
    'way/503183941': 's-s-taris-zeytin-ve-zeytinyagi-tar-sat-koop-birligi',
    'way/532040215': 'abalioglu-yag-sanayi-ve-ticaret-a-s',
    'way/187706596': 'ataer-enerji-elektrik-uretim-a-s',   # tesis alani, bina degil -> cati cikmayabilir
}
# CIKARILDI (2026-10-21): OSM'de ayni adli bina var ama firmanin kayitli adresindeki sokaga ~2 km uzak (baska tesis):
#   way/503183932 Baylan (10032 No:16), way/532040218 Demsac (10022 No:18); way/187706597 AKTAS arazi alani, 957 m uzak


def kat(s):  # buyuk harf + Turkce katlama
    s = (s or '').replace('İ', 'I').replace('ı', 'i').upper()
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def sokak_kodu(ad):
    a = kat(ad)
    if 'KEMAL' in a and ('BUL' in a or 'BLV' in a): return 'MKA'
    if 'ESKI HAVAALANI' in a: return 'EHC'
    if 'ANADOLU' in a and 'CAD' in a: return 'ANADOLU'
    m = re.match(r'\s*(\d{1,2}[.]?\d{3}(?:/\d+)?)', a)
    return m.group(1).replace('.', '') if m else None


def adres_coz(a):
    A = kat(a)
    m = re.search(r'(\d{1,2}[.]?\d{3}(?:/\d+)?)\s*\.?\s*(SOKAK|SOK|SK)\b.*?N[O0]\s*[:.]?\s*(\d+)', A)
    if m: return m.group(1).replace('.', ''), int(m.group(3))
    m = re.search(r'(?:BUL|BLV|CAD)\S*\s*N[O0]\s*[:.]?\s*(\d+)', A)
    if m: return sokak_kodu(A), int(m.group(1))
    return None, None


def son(desen):
    d = os.path.dirname(V('ham', 'osm', desen))
    return os.path.join(d, sorted(f for f in os.listdir(d) if re.fullmatch(desen.replace('*', '.*'), f))[-1])


# ---- girdiler
c = gpd.read_file(MODEL, layer='catilar')
c = c[c.bolge == 'ataturk_osb'].to_crs(UTM).reset_index(drop=True)
f = pd.read_csv(V('ham', 'iaosb', 'osb_firmalar_birlesik.csv'), sep=';', dtype=str).fillna('')
f[['sokak', 'no']] = f.adres.apply(lambda a: pd.Series(adres_coz(a), dtype=object))
f['no'] = f['no'].astype('Int64')   # NaN yuzunden float'a donmesin (11.0 != '11')
f['slug'] = f.url.str.rsplit('/', n=1).str[-1]
assert not set(KESIN.values()) - set(f.slug), set(KESIN.values()) - set(f.slug)

yr = []
for e in json.load(open(son('osm_yollar_osb_*.json'), encoding='utf-8'))['elements']:
    if 'geometry' in e:
        yr.append(dict(osm=f"way/{e['id']}", hw=e['tags'].get('highway'), kod=sokak_kodu(e['tags'].get('name', '')),
                       geometry=LineString([(p['lon'], p['lat']) for p in e['geometry']])))
y = gpd.GeoDataFrame(yr, crs=4326).to_crs(UTM)
geo = {f"way/{e['id']}": Polygon([(p['lon'], p['lat']) for p in e['geometry']])
       for e in json.load(open(V('ham', 'osm', 'overpass_bina_ham_ataturk_osb.json'), encoding='utf-8'))['elements']
       if e['type'] == 'way' and 'geometry' in e}
for e in json.load(open(son('osm_adli_osb_*.json'), encoding='utf-8'))['elements']:
    k = f"{e['type']}/{e['id']}"
    if k not in geo and ('lon' in e or 'center' in e):
        geo[k] = Point(e['lon'], e['lat']) if 'lon' in e else Point(e['center']['lon'], e['center']['lat'])


def cati_bul(g, tampon):
    """geometrinin ortustugu catilar (en buyuk kesisim once), yoksa <=tampon m en yakin cati"""
    k = c[c.intersects(g)]
    if len(k): return list(k.assign(o=k.intersection(g).area).sort_values('o', ascending=False).cati_id[:3])
    d = c.distance(g)
    return [int(c.cati_id[d.idxmin()])] if d.min() <= tampon else []


# ---- 1) kesin eslesmeler
kesin = {}
for osm, slug in KESIN.items():
    ids = list(c[c.osm == osm].cati_id) or cati_bul(gpd.GeoSeries([geo[osm]], crs=4326).to_crs(UTM).iloc[0], 30)
    kesin[slug] = (osm, ids)

# ---- adsiz OSM sokaklarina ad: kesin firmanin catisina en yakin adsiz yol parcasi (<=40 m)
yad = y[y.kod.isna() & ~y.hw.isin(['footway', 'path', 'steps', 'cycleway', 'motorway', 'motorway_link', 'trunk', 'trunk_link'])]
for slug, (osm, ids) in kesin.items():
    sk = f.loc[f.slug == slug, 'sokak'].iloc[0]
    if ids and sk and sk not in set(y.kod.dropna()):
        d = yad.distance(c.set_index('cati_id').geometry[ids[0]])
        if d.min() <= 40: y.loc[d.idxmin(), 'kod'] = sk; print('adsiz yola ad verildi:', sk, y.at[d.idxmin(), 'osm'])
H = {}
for k, g in y[y.kod.notna()].groupby('kod'):
    u = unary_union(list(g.geometry)); H[k] = u if u.geom_type == 'LineString' else linemerge(u)
D = pd.DataFrame({k: c.geometry.distance(H[k]) for k in H}, index=c.cati_id)
enyakin = D.min(axis=1)


def adaylar(sk):
    if sk not in D: return []
    d = D[sk]
    return list(d[(d <= CEPHE_M) & (d <= enyakin + CEPHE_PAY_M)].sort_values().index)


MERKEZ = c.to_crs(4326).union_all().centroid   # Ataturk OSB merkezi (geocoding arama siniri)
# ---- 2) Geocoding (anahtar varsa): once TomTom (kartsiz ucretsiz plan), yoksa Google
def anahtar_oku(ortam, dosya):
    p = os.path.join(KOK, dosya)
    return os.environ.get(ortam) or (open(p, encoding='utf-8-sig').read().strip() if os.path.exists(p) else '')
anahtar = anahtar_oku('TOMTOM_API_KEY', '.tomtom_key')
SAGLAYICI = 'tomtom' if anahtar else 'google'
if not anahtar: anahtar = anahtar_oku('GOOGLE_MAPS_API_KEY', '.google_maps_key')
if not anahtar: SAGLAYICI = ''
print('geocoding saglayicisi:', SAGLAYICI or 'YOK (anahtar bulunamadi, adim atlaniyor)')
ONBELLEK = ONBELLEK.replace('google', SAGLAYICI or 'google')
onb = json.load(open(ONBELLEK, encoding='utf-8')) if os.path.exists(ONBELLEK) else {}
bugun = dt.date.today()
onb = {k: v for k, v in onb.items() if (bugun - dt.date.fromisoformat(v['tarih'])).days < 30}   # 30 gun kurali


def adres_metni(sk, no):
    yol = {'MKA': 'Mustafa Kemal Atatürk Bulvarı', 'EHC': 'Eski Havaalanı Caddesi', 'ANADOLU': 'Anadolu Caddesi'}.get(sk, f'{sk}. Sokak')
    return f'{yol} No:{no}, Atatürk Organize Sanayi Bölgesi, 35620 Çiğli/İzmir'


def geocode(sk, no):
    q = adres_metni(sk, no)
    if q in onb: return onb[q]
    if not anahtar: return None
    v = dict(tarih=bugun.isoformat())
    if SAGLAYICI == 'tomtom':
        r = requests.get('https://api.tomtom.com/search/2/geocode/%s.json' % requests.utils.quote(q, safe=''), timeout=30,
                         params=dict(key=anahtar, countrySet='TR', language='tr-TR', limit=1,
                                     lat=MERKEZ.y, lon=MERKEZ.x, radius=3000))   # yoksa Tire OSB'ye gidiyor
        if r.status_code != 200: sys.exit('TomTom hatasi: %s %s' % (r.status_code, r.text[:200]))
        res = r.json().get('results', [])
        v['durum'] = 'OK' if res else 'ZERO_RESULTS'
        if res:   # type: Point Address = kapi noktasi, Address Range = aralik, Street/Geography = kaba
            s = res[0]; a = s.get('address', {})
            v.update(lat=s['position']['lat'], lon=s['position']['lon'],
                     tip={'Point Address': 'ROOFTOP', 'Address Range': 'RANGE_INTERPOLATED'}.get(s['type'], s['type'].upper()),
                     yol=a.get('streetName', ''), no=a.get('streetNumber', ''), skor=s.get('matchConfidence', {}).get('score'))
        time.sleep(0.25)   # ucretsiz plan: 5 istek/sn
    else:
        r = requests.get('https://maps.googleapis.com/maps/api/geocode/json', timeout=30,
                         params=dict(address=q, region='tr', language='tr', components='country:TR', key=anahtar)).json()
        if r['status'] not in ('OK', 'ZERO_RESULTS'): sys.exit('Google hatasi: %s %s' % (r['status'], r.get('error_message', '')))
        v['durum'] = r['status']
        if r['results']:
            s = r['results'][0]; ac = {t: x['long_name'] for x in s['address_components'] for t in x['types']}
            v.update(lat=s['geometry']['location']['lat'], lon=s['geometry']['location']['lng'],
                     tip=s['geometry']['location_type'], yol=ac.get('route', ''), no=ac.get('street_number', ''))
        time.sleep(0.05)
    onb[q] = v
    return v


geo_sonuc = {}
for sk, no in f.loc[f.sokak.notna(), ['sokak', 'no']].drop_duplicates().itertuples(index=False):
    v = geocode(sk, no)
    if not v or 'lat' not in v: continue
    tut = (v['tip'] in GECERLI and str(int(no)) == re.sub(r'\D.*', '', v['no'] or '')
           and (sokak_kodu(v['yol']) == sk or sk.replace('/', '') in kat(v['yol']).replace('/', '').replace('.', '')))
    if tut:
        p = gpd.GeoSeries([Point(v['lon'], v['lat'])], crs=4326).to_crs(UTM).iloc[0]
        geo_sonuc[(sk, no)] = (v['tip'] + ('' if c.contains(p).any() else '_yakin'), cati_bul(p, GEO_TAMPON))
    else:
        geo_sonuc[(sk, no)] = ('tutmadi:' + v['tip'], [])
if onb:
    os.makedirs(os.path.dirname(ONBELLEK), exist_ok=True)
    json.dump(onb, open(ONBELLEK, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

# ---- tablo
ELLE = V('elle', 'firma_cati_elle.csv')
elle = {}
if os.path.exists(ELLE):
    for r in pd.read_csv(ELLE, dtype=str).fillna('').itertuples():
        elle[(r.sokak, int(r.kapi_no))] = r
    print('elle karar:', len(elle), 'adres')
rows = []
for r in f.itertuples():
    b = dict(firma=r.firma, nace=r.nace, nace_bolum=r.nace_bolum, adres=r.adres, url=r.url, sokak=r.sokak, kapi_no=r.no,
             eslesme='', cati_id='', geocode_tipi='', aday_sayisi=0, aday_cati_id='', kaynak='')
    sokaksiz = pd.isna(r.sokak) or pd.isna(r.no)
    gs = None if sokaksiz else geo_sonuc.get((r.sokak, r.no))
    if gs: b['geocode_tipi'] = gs[0]
    ad = [] if sokaksiz else adaylar(r.sokak)   # elle kontrolde komsu catilari da gostermek icin her satira
    b.update(aday_sayisi=len(ad), aday_cati_id=';'.join(map(str, ad)))
    el = None if sokaksiz else elle.get((r.sokak, int(r.no)))
    if el is not None and el.karar == 'cati':
        b.update(eslesme='elle', cati_id=el.cati_id, kaynak='elle:' + (el.isaretleyen or '?'))
    elif r.slug in kesin and kesin[r.slug][1]:
        osm, ids = kesin[r.slug]; b.update(eslesme='kesin_osm', cati_id=';'.join(map(str, ids)), kaynak=osm)
    elif gs and gs[1]:
        b.update(eslesme='geocode_' + gs[0].lower(), cati_id=';'.join(map(str, gs[1])), kaynak=SAGLAYICI + '_geocoding')
    elif sokaksiz:
        b['eslesme'] = 'adres_cozulemedi'
    else:
        b['eslesme'] = 'sokak_aday' if ad else 'sokak_osmde_yok'
    rows.append(b)
out = pd.DataFrame(rows)
out['kapi_no'] = out.kapi_no.astype('Int64')
out.to_csv(CIKTI, index=False, encoding='utf-8-sig')
print(out.eslesme.value_counts().to_string())
if geo_sonuc:   # dogrulama: kesin eslesmelerde geocode ayni catiyi buldu mu
    k = [(s, kesin[s][1], geo_sonuc.get(tuple(f.loc[f.slug == s, ['sokak', 'no']].iloc[0]))) for s in kesin if kesin[s][1]]
    ok = [s for s, ids, g in k if g and g[1] and set(g[1]) & set(ids)]
    print(f'dogrulama: {len(k)} kesin eslesmenin {sum(1 for _, _, g in k if g and g[1])} tanesinde geocode cati buldu, '
          f'{len(ok)} tanesi ayni cati')
    for s, ids, g in k: print('  ', s[:40], 'kesin', ids, 'geocode', g)
print('->', CIKTI)
