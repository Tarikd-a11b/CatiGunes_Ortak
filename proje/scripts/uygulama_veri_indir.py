# -*- coding: utf-8 -*-
"""UYGULAMA FAZI veri indirme (2026-10-14, hoca 'uygulamaya baslayin' dedi).

Kapsam: (1) Ataturk OSB (pilot, sanayi catilari)  (2) Cigli ilcesindeki kamu hizmeti binalari.
Her adim ayri calisir, ciktilar veri/ham/<kaynak>/ altina, envanter veri/envanter.json'a yazilir.

  python scripts/uygulama_veri_indir.py sinir      # ilce + OSB sinirlari (Overpass)
  python scripts/uygulama_veri_indir.py osm        # iki bolgedeki TUM OSM binalari (tum etiketler)
  python scripts/uygulama_veri_indir.py kamu       # Cigli kamu hizmeti tesisleri (OSM islev etiketi)
  python scripts/uygulama_veri_indir.py ms         # Microsoft ayak izleri (cache'ten kirpilir)
  python scripts/uygulama_veri_indir.py pvgis      # PVGIS saatlik/aylik/TMY/ufuk, iki bolge merkezi
  python scripts/uygulama_veri_indir.py goruntu    # Esri World Imagery z19 karolari (OSB + kamu catilari)
  python scripts/uygulama_veri_indir.py hepsi
"""
import json, math, os, sys, time, datetime, urllib.parse
import concurrent.futures as cf
import requests
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, Point
from shapely.geometry import LineString
from shapely.ops import transform, unary_union, polygonize, linemerge
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
HAM = yol('veri', 'ham')
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/2.0 (akademik arastirma; Izmir Bakircay Univ.)'}
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform
BUGUN = datetime.date.today().isoformat()
AYNALAR = ['https://overpass-api.de/api/interpreter']   # 2026-10-14: kumi/mail.ru zaman asimi
CIGLI_REL = 1268482          # OSM relation, Cigli ilcesi (cache/bolgeler.geojson ile ayni)


# ------------------------------------------------------------------ yardimcilar
def klasor(*p):
    d = os.path.join(HAM, *p); os.makedirs(d, exist_ok=True); return d


def envanter(anahtar, **kw):
    p = yol('veri', 'envanter.json')
    d = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    kw.setdefault('indirme_tarihi', BUGUN)
    d[anahtar] = kw
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def overpass(sorgu, deneme=6):
    for i in range(deneme):
        uc = AYNALAR[i % len(AYNALAR)]
        try:
            r = requests.post(uc, data={'data': sorgu}, headers=UA, timeout=200)
            if r.status_code == 200:
                return r.json()
            print('   HTTP %d (%s)' % (r.status_code, uc.split('/')[2]))
        except Exception as e:
            print('   hata: %s' % str(e)[:80])
        time.sleep(10 * (i + 1))
    raise RuntimeError('Overpass cevap vermedi — SESSIZCE ATLANMAZ, tekrar calistir.')


def geom(e):
    """Overpass 'out geom' elemanindan shapely poligon."""
    if e['type'] == 'way':
        h = [(p['lon'], p['lat']) for p in e.get('geometry', [])]
        return Polygon(h) if len(h) >= 4 else None
    if e['type'] == 'relation':
        # uye yollar parca parca gelir -> once halkalari birlestir (polygonize)
        def halka(rol):
            hatlar = [LineString([(p['lon'], p['lat']) for p in u['geometry']])
                      for u in e.get('members', [])
                      if u.get('type') == 'way' and u.get('role') == rol and len(u.get('geometry') or []) >= 2]
            return unary_union(list(polygonize(linemerge(unary_union(hatlar))))) if hatlar else None
        dis, ic = halka('outer'), halka('inner')
        if dis is None or dis.is_empty: return None
        return dis.difference(ic) if ic is not None and not ic.is_empty else dis
    return None


def geojson_yaz(p, ozellikler):
    json.dump({'type': 'FeatureCollection', 'features': ozellikler},
              open(p, 'w', encoding='utf-8'), ensure_ascii=False)


def sinirlar():
    p = os.path.join(HAM, 'sinir', 'sinirlar.geojson')
    if not os.path.exists(p): sys.exit('once: sinir')
    return {f['properties']['etiket']: shape(f['geometry'])
            for f in json.load(open(p, encoding='utf-8'))['features']}


def alan_m2(g): return transform(to_utm, g).area


# ------------------------------------------------------------------ 1) sinir
def adim_sinir():
    d = klasor('sinir')
    q = """[out:json][timeout:180];
rel(%d);out geom;
rel(area:%d)["name"~"Atat.rk Organize",i];out geom;
way(area:%d)["name"~"Atat.rk Organize",i];out geom;
""" % (CIGLI_REL, 3600000000 + CIGLI_REL, 3600000000 + CIGLI_REL)
    j = overpass(q)
    json.dump(j, open(os.path.join(d, 'overpass_sinir_ham.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    oz = []
    for e in j['elements']:
        g = geom(e)
        if g is None or g.is_empty: continue
        t = e.get('tags', {})
        if e['id'] == CIGLI_REL and e['type'] == 'relation':
            et = 'cigli'
        else:
            print('   OSB adayi: %s/%s %s  %s  %.2f km2' % (e['type'], e['id'], t.get('name'),
                  {k: t[k] for k in ('boundary', 'admin_level', 'landuse') if k in t}, alan_m2(g) / 1e6))
            et = 'osb_aday_%s%s' % (e['type'][0], e['id'])
        oz.append({'type': 'Feature', 'geometry': mapping(g),
                   'properties': {'etiket': et, 'osm': '%s/%s' % (e['type'], e['id']),
                                  'ad': t.get('name'), 'alan_km2': round(alan_m2(g) / 1e6, 3),
                                  **{k: t[k] for k in ('boundary', 'admin_level', 'landuse') if k in t}}})
    # OSB secimi: admin sinir varsa o (wiki: OSM'de admin_level 8 ayri birim), yoksa en buyuk aday
    aday = [f for f in oz if f['properties']['etiket'].startswith('osb_aday')]
    if not aday: raise RuntimeError('Ataturk OSB siniri bulunamadi')
    sec = sorted(aday, key=lambda f: (f['properties'].get('boundary') != 'administrative',
                                      -f['properties']['alan_km2']))[0]
    sec = dict(sec, properties=dict(sec['properties'], etiket='ataturk_osb'))
    son = [f for f in oz if f['properties']['etiket'] == 'cigli'] + [sec]
    geojson_yaz(os.path.join(d, 'sinirlar.geojson'), son)
    geojson_yaz(os.path.join(d, 'osb_adaylari.geojson'), aday)
    for f in son: print('   SECILEN %-12s %s  %.2f km2' % (f['properties']['etiket'], f['properties']['osm'], f['properties']['alan_km2']))
    envanter('sinir', kaynak='OpenStreetMap (Overpass API)', lisans='ODbL 1.0',
             dosya='veri/ham/sinir/sinirlar.geojson', not_='OSB: admin sinir oncelikli, yoksa en buyuk aday; adaylar osb_adaylari.geojson')


def karo_al(kd, lon, lat, A, derinlik=0):
    """Bir karonun bina elemanlari; zaman asiminda 4 alt karoya bolunur (en fazla 2 kez)."""
    kp = os.path.join(kd, 'b_%.4f_%.4f_%.4f.json' % (lon, lat, A)) if derinlik else          os.path.join(kd, 'b_%.3f_%.3f.json' % (lon, lat))
    if not (os.path.exists(kp) and os.path.getsize(kp) > 50):
        bbox = '%f,%f,%f,%f' % (lat, lon, lat + A, lon + A)
        try:
            jj = overpass('[out:json][timeout:180];(way["building"](%s);rel["building"](%s););out geom tags;'
                          % (bbox, bbox), deneme=3 if derinlik < 2 else 6)
        except RuntimeError:
            if derinlik >= 2: raise
            print('   karo bolunuyor: %.4f %.4f (%.4f)' % (lon, lat, A))
            h = A / 2; el = []
            for dx in (0, h):
                for dy in (0, h):
                    el += karo_al(kd, lon + dx, lat + dy, h, derinlik + 1)
            return el
        json.dump(jj, open(kp, 'w', encoding='utf-8')); time.sleep(2)
    return json.load(open(kp, encoding='utf-8'))['elements']


# ------------------------------------------------------------------ 2) osm binalar
def adim_osm():
    d = klasor('osm')
    s = sinirlar()
    for et in ('ataturk_osb', 'cigli'):
        g = s[et]
        # buyuk bbox Overpass'ta 504 veriyor -> 0,03 derecelik karolar, her karo diske onbelleklenir
        kd = klasor('osm', 'karo'); b = g.bounds; A = 0.03
        elemanlar = {}
        lon = b[0]
        while lon < b[2]:
            lat = b[1]
            while lat < b[3]:
                kutu = Polygon([(lon, lat), (lon + A, lat), (lon + A, lat + A), (lon, lat + A)])
                if g.intersects(kutu):
                    for e in karo_al(kd, lon, lat, A):
                        elemanlar[(e['type'], e['id'])] = e
                lat += A
            lon += A
        j = {'elements': list(elemanlar.values())}
        print('   %d tekil eleman (karolardan)' % len(j['elements']))
        hazir = g.buffer(0)
        oz = []
        for e in j['elements']:
            p = geom(e)
            if p is None or p.is_empty or not p.is_valid and not p.buffer(0).is_valid: continue
            if not hazir.intersects(p.representative_point()): continue
            t = e.get('tags', {})
            oz.append({'type': 'Feature', 'geometry': mapping(p),
                       'properties': {'osm': '%s/%s' % (e['type'], e['id']),
                                      'alan_m2': round(alan_m2(p), 1), **t}})
        p = os.path.join(d, 'binalar_%s.geojson' % et)
        geojson_yaz(p, oz)
        print('   %d bina, toplam %.3f km2 taban -> %s' % (len(oz), sum(f['properties']['alan_m2'] for f in oz) / 1e6, p))
        envanter('osm_bina_' + et, kaynak='OpenStreetMap (Overpass API)', lisans='ODbL 1.0',
                 dosya='veri/ham/osm/binalar_%s.geojson' % et, kayit=len(oz),
                 not_='tum etiketler korundu (height, building:levels, roof:* vb.)')
        time.sleep(5)


# ------------------------------------------------------------------ 3) kamu
KAMU_ETIKET = [  # scripts/kamu_binalari.py ile ayni kume (+ healthcare, office=government)
    ('amenity', 'school'), ('amenity', 'kindergarten'), ('amenity', 'college'), ('amenity', 'university'),
    ('building', 'school'), ('building', 'university'), ('building', 'kindergarten'),
    ('amenity', 'hospital'), ('amenity', 'clinic'), ('amenity', 'doctors'), ('building', 'hospital'),
    ('healthcare', 'centre'), ('healthcare', 'hospital'), ('healthcare', 'clinic'),
    ('amenity', 'townhall'), ('amenity', 'courthouse'), ('amenity', 'police'), ('amenity', 'fire_station'),
    ('amenity', 'post_office'), ('office', 'government'), ('building', 'government'), ('building', 'public'),
    ('amenity', 'community_centre'), ('amenity', 'social_facility'), ('amenity', 'library'),
    ('amenity', 'arts_centre'), ('amenity', 'theatre'), ('amenity', 'place_of_worship'),
    ('leisure', 'sports_centre'), ('leisure', 'stadium'), ('building', 'sports_hall'),
    ('amenity', 'animal_shelter'), ('amenity', 'marketplace'), ('amenity', 'prison'),
]


def adim_kamu():
    d = klasor('kamu')
    a = 3600000000 + CIGLI_REL
    parca = ''.join('nwr(area:%d)["%s"="%s"];' % (a, k, v) for k, v in KAMU_ETIKET)
    j = overpass('[out:json][timeout:300];(%s);out geom tags;' % parca)
    json.dump(j, open(os.path.join(d, 'overpass_kamu_ham.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    oz = []
    for e in j['elements']:
        t = e.get('tags', {})
        g = Point(e['lon'], e['lat']) if e['type'] == 'node' else geom(e)
        if g is None or g.is_empty: continue
        eslesen = ['%s=%s' % (k, v) for k, v in KAMU_ETIKET if t.get(k) == v]
        oz.append({'type': 'Feature', 'geometry': mapping(g),
                   'properties': {'osm': '%s/%s' % (e['type'], e['id']), 'eslesen_etiket': ';'.join(eslesen),
                                  'tesis_alan_m2': round(alan_m2(g), 1) if g.geom_type != 'Point' else None, **t}})
    geojson_yaz(os.path.join(d, 'kamu_tesisleri_cigli_osm.geojson'), oz)
    print('   %d kamu hizmeti tesisi (nokta+poligon)' % len(oz))
    envanter('kamu_osm', kaynak='OpenStreetMap (Overpass API)', lisans='ODbL 1.0',
             dosya='veri/ham/kamu/kamu_tesisleri_cigli_osm.geojson', kayit=len(oz),
             not_='ISLEV etiketi, MULKIYET degil; place_of_worship + prison bu surumde eklendi, filtrelenebilir')


# ------------------------------------------------------------------ 4) microsoft
def adim_ms():
    d = klasor('ms')
    s = sinirlar()
    kaynak = yol('cache', 'ms_izmir_122100310.geojsonl')
    out = {k: [] for k in s}
    with open(kaynak, encoding='utf-8') as f:
        for satir in f:
            if not satir.strip(): continue
            o = json.loads(satir)
            g = shape(o['geometry']); c = g.representative_point()
            for k, b in s.items():
                if b.contains(c):
                    out[k].append({'type': 'Feature', 'geometry': o['geometry'],
                                   'properties': dict(o.get('properties') or {}, alan_m2=round(alan_m2(g), 1))})
    for k, v in out.items():
        geojson_yaz(os.path.join(d, 'ms_binalar_%s.geojson' % k), v)
        print('   %s: %d MS bina' % (k, len(v)))
        envanter('ms_bina_' + k, kaynak='Microsoft GlobalMLBuildingFootprints (quadkey 122100310)',
                 lisans='ODbL 1.0', dosya='veri/ham/ms/ms_binalar_%s.geojson' % k, kayit=len(v),
                 not_='bitisik binalari birlestirebiliyor; capraz kontrol icin')


# ------------------------------------------------------------------ 5) pvgis
PVGIS = 'https://re.jrc.ec.europa.eu/api/v5_3/'


def adim_pvgis():
    d = klasor('pvgis')
    s = sinirlar()
    for k, g in s.items():
        c = g.representative_point(); lat, lon = round(c.y, 5), round(c.x, 5)
        istekler = {
            'tmy': ('tmy', {'outputformat': 'json'}),
            'ufuk': ('printhorizon', {'outputformat': 'json'}),
            'aylik_isinim': ('MRcalc', {'horirrad': 1, 'optrad': 1, 'mr_dni': 1, 'avtemp': 1,
                                        'startyear': 2005, 'endyear': 2023, 'outputformat': 'json'}),
            # duz cati senaryolari: yatay(0), 10 derece guney, optimum aci
            'pv_egim10_guney': ('PVcalc', {'peakpower': 1, 'loss': 14, 'angle': 10, 'aspect': 0, 'outputformat': 'json'}),
            # 2026-11-07: uretim hesabinin ikinci duz cati senaryosu (ekip arkadasinin defteri: 10 ve 15 derece)
            'pv_egim15_guney': ('PVcalc', {'peakpower': 1, 'loss': 14, 'angle': 15, 'aspect': 0, 'outputformat': 'json'}),
            'pv_optimum': ('PVcalc', {'peakpower': 1, 'loss': 14, 'optimalangles': 1, 'outputformat': 'json'}),
            # dogu (-90) ve bati (+90) ayri: Izmir'de fark <%0,1, dogu-bati sistem = ikisinin ortalamasi
            'pv_dogu_bati_10': ('PVcalc', {'peakpower': 1, 'loss': 14, 'angle': 10, 'aspect': -90, 'outputformat': 'json'}),
            'pv_bati_10': ('PVcalc', {'peakpower': 1, 'loss': 14, 'angle': 10, 'aspect': 90, 'outputformat': 'json'}),
            # yukaridakiler 'free' (acik saha, iyi havalanma); cati ustune yakin montaj = 'building' (sicak, ~%4 dusuk)
            'pv_egim10_guney_cati': ('PVcalc', {'peakpower': 1, 'loss': 14, 'angle': 10, 'aspect': 0,
                                                'mountingplace': 'building', 'outputformat': 'json'}),
            # saatlik 1 kWp uretim serisi (oz tuketim / saatlik mahsuplasma icin)
            'saatlik_egim10_guney': ('seriescalc', {'pvcalculation': 1, 'peakpower': 1, 'loss': 14, 'angle': 10,
                                                    'aspect': 0, 'startyear': 2020, 'endyear': 2023,
                                                    'components': 1, 'outputformat': 'json'}),
        }
        for ad, (uc, par) in istekler.items():
            p = os.path.join(d, '%s_%s.json' % (k, ad))
            if os.path.exists(p) and os.path.getsize(p) > 500: continue
            r = requests.get(PVGIS + uc, params=dict(par, lat=lat, lon=lon), headers=UA, timeout=180)
            if r.status_code != 200:
                raise RuntimeError('PVGIS %s %s: HTTP %d %s' % (k, ad, r.status_code, r.text[:200]))
            open(p, 'w', encoding='utf-8').write(r.text)
            print('   %s %-22s %7.0f KB' % (k, ad, len(r.content) / 1024)); time.sleep(1.5)
        envanter('pvgis_' + k, kaynak='PVGIS 5.3 API (JRC), SARAH3', lisans='JRC, serbest kullanim + atif',
                 dosya='veri/ham/pvgis/%s_*.json' % k, nokta=[lat, lon],
                 not_='aspect: PVGIS 0=guney (pvlib 0=kuzey!). saatlik seri 2020-2023, 1 kWp, kayip %14')


# ------------------------------------------------------------------ 6) goruntu
Z = 19
ESRI = 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'


def deg2tile(lat, lon, z=Z):
    n = 1 << z
    return (int((lon + 180.0) / 360.0 * n),
            int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n))


def tile_poly(x, y, z=Z):
    n = 1 << z
    def ll(x, y):
        return x / n * 360.0 - 180.0, math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    (a, b), (c, e) = ll(x, y), ll(x + 1, y + 1)
    return Polygon([(a, b), (c, b), (c, e), (a, e)])


def karolar_icin(g, tampon_m=40):
    """g'yi (tamponlu) kesen z19 karolari."""
    gb = g.buffer(tampon_m / 111000.0)
    b = gb.bounds
    x0, y0 = deg2tile(b[3], b[0]); x1, y1 = deg2tile(b[1], b[2])
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if gb.intersects(tile_poly(x, y))}


def adim_goruntu():
    s = sinirlar()
    isler = {'ataturk_osb': karolar_icin(s['ataturk_osb'])}
    # 2026-10-15: yalniz kapsamdaki devlet okul + hastaneleri (+ MEB kontrol listesi); once scripts/kamu_okul_hastane.py
    k = set()
    for ad in ('kamu_okul_hastane_cigli.geojson', 'kamu_belirsiz_kontrol.geojson'):
        kp = os.path.join(KOK, 'veri', 'islenmis', ad)
        if os.path.exists(kp):
            for f in json.load(open(kp, encoding='utf-8'))['features']:
                k |= karolar_icin(shape(f['geometry']), 60)
    if k: isler['cigli_kamu'] = k - isler['ataturk_osb']
    for ad, karo in isler.items():
        d = klasor('goruntu', ad)
        print('-- %s: %d karo (z%d, ~0,23 m/piksel)' % (ad, len(karo), Z))
        def al(xy):
            x, y = xy; p = os.path.join(d, '%d_%d_%d.jpg' % (Z, x, y))
            if os.path.exists(p) and os.path.getsize(p) > 1000: return True
            for _ in range(3):
                try:
                    r = requests.get(ESRI.format(z=Z, x=x, y=y), headers=UA, timeout=45)
                    if r.status_code == 200 and len(r.content) > 1000:
                        open(p, 'wb').write(r.content); return True
                except Exception: time.sleep(2)
            return False
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            sonuc = list(ex.map(al, sorted(karo)))
        eksik = [xy for xy, ok in zip(sorted(karo), sonuc) if not ok]
        json.dump({'zoom': Z, 'karolar': sorted(karo), 'eksik': eksik},
                  open(os.path.join(d, '_karo_listesi.json'), 'w'))
        print('   indirilen %d / %d, EKSIK %d' % (len(karo) - len(eksik), len(karo), len(eksik)))
        envanter('goruntu_' + ad, kaynak='Esri World Imagery (ArcGIS Online tile servisi)',
                 lisans='Esri kullanim kosullari — akademik/ticari olmayan, atif zorunlu; cekim tarihi karoya gore degisir',
                 dosya='veri/ham/goruntu/%s/' % ad, kayit=len(karo), eksik=len(eksik))


ADIMLAR = {'sinir': adim_sinir, 'osm': adim_osm, 'kamu': adim_kamu, 'ms': adim_ms,
           'pvgis': adim_pvgis, 'goruntu': adim_goruntu}

if __name__ == '__main__':
    sec = sys.argv[1:] or ['hepsi']
    for a in (list(ADIMLAR) if 'hepsi' in sec else sec):
        print('\n===== %s =====' % a); ADIMLAR[a]()
