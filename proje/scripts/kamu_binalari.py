# -*- coding: utf-8 -*-
"""KAMU BINALARI - OSM'den ilce bazinda kamu hizmeti binalari (GEOMETRI ILE).

NEDEN YENIDEN INDIRILIYOR: data/osm_izmir_kamu.json'un uc eksigi var.
  1. Geometri yok ('out center') -> cati alani cikarilamiyor, yalnizca sayilabiliyor.
     Onceliklendirmede kamu binasi 0/1 bayragi olarak kaliyor; oysa 400 m2 okul cati
     ile 4.000 m2 hastane catisi ayni sey degil.
  2. Izmir geneli, ilceye ayrilmamis.
  3. Etiket kumesi dar: okul / hastane / klinik / kutuphane / muhtarlik / kres.
     Izmir BB'nin KENDI GES tesisleri (cache/acikveri/lisanssiz_ges.csv) ise itfaiye,
     kultur merkezi, spor salonu, hayvan barinagi, mezbaha, kati atik tesisi.
     Yani belediyenin fiilen panel koydugu bina turlerinin cogu eski kumede YOK.

!! ONEMLI SINIR: OSM etiketleri MULKIYET degil ISLEV soyler. 'amenity=hospital'
   ozel hastane de olabilir. Bu kume 'kamu HIZMETI binasi'dir, 'kamu MULKU' degil.
   operator / operator:type etiketi varsa cikti tabloya yazilir; cogunda yoktur.
   Kamu yatirimi hedefi olarak kullanilmadan once bu ayiklama yapilmalidir.

Kullanim
  python scripts/kamu_binalari.py                # varsayilan: ÇİĞLİ
  python scripts/kamu_binalari.py ÇİĞLİ KARŞIYAKA

Girdi
  cache/mahalle_sinirlari.geojson    ilce/mahalle sinirlari
  cache/osm_binalar_cigli.geojsonl   nokta kayitlara bina eslestirmek icin (varsa)

Cikti
  cache/kamu_<ilce>.geojson          poligon + nokta, mahalle ve alan bilgisiyle
  cache/kamu_<ilce>.csv              duz tablo
"""
import csv, io, json, os, sys, time, unicodedata, urllib.parse
import numpy as np, requests
from shapely.geometry import shape, Polygon, MultiPolygon, Point, mapping
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:32635', always_xy=True).transform
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/1.0 (akademik arastirma)'}

ILCELER = [a.upper() for a in sys.argv[1:]] or ['ÇİĞLİ']
NOKTA_YARICAP = 30.0        # m; nokta kayda en yakin bina poligonunu bu yaricapta ara

# Etiket kumesi. Her satirin yaninda neden dahil edildigi yazili; teze
# 'kamu binasi neye deniyor' sorusunun cevabi olarak bu liste girecek.
ETIKETLER = [
    # --- egitim ---
    ('amenity', 'school'),            ('amenity', 'kindergarten'),
    ('amenity', 'college'),           ('amenity', 'university'),
    ('building', 'school'),           ('building', 'kindergarten'),
    ('building', 'university'),
    # --- saglik ---
    ('amenity', 'hospital'),          ('amenity', 'clinic'),
    ('amenity', 'doctors'),           ('building', 'hospital'),
    ('healthcare', 'centre'),
    # --- idari ---
    ('amenity', 'townhall'),          ('amenity', 'courthouse'),
    ('amenity', 'police'),            ('amenity', 'fire_station'),  # Izmir BB GES'te var
    ('amenity', 'post_office'),       ('office', 'government'),
    ('building', 'civic'),            ('building', 'government'),
    ('building', 'public'),
    # --- sosyal / kultur ---  (Izmir BB GES'te 'Kultur Merkezi' cok sayida)
    ('amenity', 'community_centre'),  ('amenity', 'social_facility'),
    ('amenity', 'library'),           ('amenity', 'arts_centre'),
    ('amenity', 'theatre'),
    # --- spor ---  (Izmir BB GES'te 'Cok Amacli Spor Salonu')
    ('leisure', 'sports_centre'),     ('leisure', 'stadium'),
    ('building', 'sports_hall'),
    # --- diger belediye tesisi ---  (GES listesindeki barinak/mezbaha/atik tesisi)
    ('amenity', 'animal_shelter'),    ('amenity', 'marketplace'),
]
GRUP = {  # raporlama icin kaba siniflandirma
    'school': 'egitim', 'kindergarten': 'egitim', 'college': 'egitim',
    'university': 'egitim',
    'hospital': 'saglik', 'clinic': 'saglik', 'doctors': 'saglik', 'centre': 'saglik',
    'townhall': 'idari', 'courthouse': 'idari', 'police': 'idari',
    'fire_station': 'idari', 'post_office': 'idari', 'government': 'idari',
    'civic': 'idari', 'public': 'idari',
    'community_centre': 'sosyal-kultur', 'social_facility': 'sosyal-kultur',
    'library': 'sosyal-kultur', 'arts_centre': 'sosyal-kultur', 'theatre': 'sosyal-kultur',
    'sports_centre': 'spor', 'stadium': 'spor', 'sports_hall': 'spor',
    'animal_shelter': 'diger', 'marketplace': 'diger',
}
AYNALAR = ['https://overpass-api.de/api/interpreter',
           'https://overpass.kumi.systems/api/interpreter']

# --------------------------------------------------------------- mulkiyet
# OSM etiketi ISLEV soyler, MULKIYET soylemez. Kamu yatirimi hedefi belirlerken
# ozel okul / ozel hastane elenmelidir. Once operator:type etiketine bakilir
# (kayitlarin ~%21'inde var), sonra Turkiye'ye ozgu isim kaliplarina.
# Bu bir SEZGISEL siniflandirmadir; 'belirsiz' kalanlar kamu SAYILMAZ, ayri raporlanir.
OP_KAMU  = {'government', 'public', 'university', 'municipality', 'state'}
OP_OZEL  = {'private', 'private_for_profit', 'private_non_profit', 'religious'}

AD_OZEL = [  # ozel oldugunu gosteren isim kaliplari
    'ozel ', 'koleji', 'kolej', 'akademi', 'bilfen', 'doga koleji', 'ted ',
    'cakabey', 'medical park', 'acibadem', 'tinaztepe', 'ekol hastane',
    'sifa hastane', 'kent hastane', 'can hastane', 'poliklinik',
    'tip merkezi', 'muayenehane', 'dis klinigi', 'agiz ve dis poliklinigi',
    'vakif', 'dernegi', 'plaza',
]
AD_KAMU = [  # kamu oldugunu gosteren isim kaliplari
    'ilkokul', 'ortaokul', 'anadolu lisesi', 'fen lisesi', 'imam hatip',
    'mesleki ve teknik', 'meslek lisesi', 'cok programli', 'halk egitim',
    'ogretmenevi', 'bilim ve sanat merkezi', 'rehberlik ve arastirma',
    'aile sagligi', 'asm', 'devlet hastanesi', 'egitim ve arastirma hastanesi',
    'toplum sagligi', 'agiz ve dis sagligi merkezi', 'saglik ocagi',
    'belediye', 'kaymakamlik', 'muhtarlik', 'itfaiye', 'emniyet', 'karakol',
    'ptt', 'nufus mudurlugu', 'adliye', 'vergi dairesi', 'kutuphane',
    'kultur merkezi', 'semt merkezi', 'genclik merkezi', 'huzurevi',
    'universitesi', 'fakultesi', 'kapali pazar', 'pazaryeri', 'pazar yeri',
    'mudurlugu', 'baskanligi', 'halk kutuphanesi',
]


def mulkiyet_bul(ad, etiketler):
    """'kamu' / 'ozel' / 'belirsiz' + hangi kanittan geldigi."""
    ot = (etiketler.get('operator:type') or '').strip().lower()
    if ot in OP_OZEL:
        return 'ozel', 'operator:type=%s' % ot
    if ot in OP_KAMU:
        return 'kamu', 'operator:type=%s' % ot
    op = sadelestir(etiketler.get('operator') or '')
    if op:
        if any(sadelestir(k) in op for k in ('Milli Egitim', 'Saglik Bakanligi',
                                             'Belediye', 'Universite', 'PTT')):
            return 'kamu', 'operator=%s' % (etiketler.get('operator') or '')[:30]
    a = sadelestir(ad)
    for k in AD_OZEL:
        if sadelestir(k) in a:
            return 'ozel', 'isim~%s' % k.strip()
    for k in AD_KAMU:
        if sadelestir(k) in a:
            return 'kamu', 'isim~%s' % k.strip()
    return 'belirsiz', ''


def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


def overpass(sorgu, deneme=5):
    for i in range(deneme):
        uc = AYNALAR[i % len(AYNALAR)]
        try:
            r = requests.get(uc + '?data=' + urllib.parse.quote(sorgu),
                             headers=UA, timeout=180)
            if r.status_code == 200:
                return r.json()
            print('   HTTP %d (%s)' % (r.status_code, uc.split('/')[2]))
        except Exception as e:
            print('   hata: %s' % str(e)[:70])
        b = 10 * (i + 1)
        print('   %d s bekleniyor...' % b); time.sleep(b)
    return None


# ---------------------------------------------------------------- sinirlar
fc = json.load(open(yol('cache/mahalle_sinirlari.geojson'), encoding='utf-8'))


def poligonlastir(e):
    """Overpass elemanindan shapely geometri (way/relation) uret."""
    if e['type'] == 'way':
        hat = [(p['lon'], p['lat']) for p in e.get('geometry', [])]
        return Polygon(hat) if len(hat) >= 4 else None
    dis = [Polygon([(p['lon'], p['lat']) for p in u['geometry']])
           for u in e.get('members', [])
           if u.get('role') == 'outer' and len(u.get('geometry') or []) >= 4]
    if not dis:
        return None
    return MultiPolygon(dis) if len(dis) > 1 else dis[0]


for ILCE in ILCELER:
    print('\n' + '=' * 74)
    print('  %s - OSM kamu hizmeti binalari' % ILCE)
    print('=' * 74)

    mahalleler = [dict(mahalle=f['properties']['mahalle'], geom=shape(f['geometry']))
                  for f in fc['features'] if f['properties']['ilce'] == ILCE]
    if not mahalleler:
        print('  sinir yok, atlandi'); continue
    AGAC = STRtree([m['geom'] for m in mahalleler])
    lon0 = min(m['geom'].bounds[0] for m in mahalleler)
    lat0 = min(m['geom'].bounds[1] for m in mahalleler)
    lon1 = max(m['geom'].bounds[2] for m in mahalleler)
    lat1 = max(m['geom'].bounds[3] for m in mahalleler)
    print('  %d mahalle, bbox %.4f %.4f %.4f %.4f' % (len(mahalleler), lon0, lat0, lon1, lat1))

    def hangi(g):
        c = g.representative_point() if g.geom_type != 'Point' else g
        for i in AGAC.query(c):
            if mahalleler[int(i)]['geom'].contains(c):
                return mahalleler[int(i)]['mahalle']
        return None

    # ------------------------------------------------------------ sorgu
    # Her etiketi ayri alt sorgu yapmak URL'yi 414 (too long) sinirinin ustune
    # cikariyordu. Anahtar bazinda regex'e toplanip 'nwr' (node+way+relation)
    # kisaltmasi kullaniliyor: 93 alt sorgu -> anahtar sayisi kadar alt sorgu.
    kutu = '%.5f,%.5f,%.5f,%.5f' % (lat0, lon0, lat1, lon1)
    anahtarlar = {}
    for k, v in ETIKETLER:
        anahtarlar.setdefault(k, []).append(v)
    parcalar = ['nwr["%s"~"^(%s)$"](%s);' % (k, '|'.join(sorted(set(vs))), kutu)
                for k, vs in anahtarlar.items()]
    sorgu = '[out:json][timeout:240];(' + ''.join(parcalar) + ');out geom tags;'
    print('  %d etiket -> %d anahtar alt sorgusu (URL %d karakter)'
          % (len(ETIKETLER), len(parcalar), len(sorgu)))
    j = overpass(sorgu)
    if j is None:
        print('  INDIRILEMEDI - atlandi'); continue
    print('  Overpass dondu: %d nesne' % len(j['elements']))

    # ------------------------------------------------------------ bina poligonlari
    binalar = []
    p = yol('cache/osm_binalar_cigli.geojsonl')
    if os.path.exists(p):
        with io.open(p, encoding='utf-8') as f:
            for satir in f:
                binalar.append(shape(json.loads(satir)['geometry']))
    B_AGAC = STRtree(binalar) if binalar else None
    print('  eslestirme icin bina poligonu: %d' % len(binalar))

    # ------------------------------------------------------------ isleme
    kayit, gorulen = [], set()
    nokta_eslesen = nokta_eslesmeyen = 0
    for e in j['elements']:
        anahtar = (e['type'], e['id'])
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        t = e.get('tags', {})
        if e['type'] == 'node':
            if e.get('lat') is None:
                continue
            g = Point(e['lon'], e['lat']); kaynak = 'nokta'
        else:
            g = poligonlastir(e)
            if g is None:
                continue
            if not g.is_valid:
                g = g.buffer(0)
            if g.is_empty:
                continue
            kaynak = 'poligon'
        mah = hangi(g)
        if mah is None:
            continue                     # bbox icinde ama ilce disinda

        # TESIS ALANI != CATI ALANI. OSM'de amenity=school cogunlukla okul
        # BAHCESININ tamamina konuyor (bahce, spor sahasi, otopark dahil).
        # Olculdu: egitim grubunda poligon alani gercek cati alaninin 3,3 kati
        # (doluluk 0,31). Poligon alani cati sanilirsa kamu potansiyeli sisiyor.
        # Bu yuzden cati = poligonun ICINDEKI bina poligonlarinin toplami.
        tesis_alan = None
        bina_idx = []                  # bu kayda dusen OSM bina poligon indeksleri
        if kaynak == 'poligon':
            tesis_alan = transform(to_utm, g).area
            if B_AGAC is not None:
                bina_idx = [int(i) for i in B_AGAC.query(g)
                            if g.contains(binalar[int(i)].representative_point())]
            # bina bulunamadiysa cati BILINMIYOR - sifir degil (asagida isaretli)
        elif B_AGAC is not None:
            # Nokta POI, icinde bulundugu binaya baglanir. DIKKAT: cok amacli bir
            # blokta (universite yerleskesi gibi) noktaya KOCA BLOK yazilir ve ayni
            # blokta baska POI varsa alan CIFT SAYILIR. Bu yuzden asagida kuresel
            # bir tekillestirme yapiliyor; burada sadece aday indeks tutuluyor.
            r_der = NOKTA_YARICAP / 111000.0
            icinde = [int(i) for i in B_AGAC.query(g.buffer(r_der))
                      if binalar[int(i)].contains(g)]
            if icinde:
                bina_idx = [max(icinde, key=lambda i: binalar[i].area)]
                tesis_alan = transform(to_utm, binalar[bina_idx[0]]).area
                kaynak = 'nokta->bina'; nokta_eslesen += 1
            else:
                nokta_eslesmeyen += 1
        mlk, kanit = mulkiyet_bul(t.get('name') or '', t)

        tur = (t.get('amenity') or t.get('building') or t.get('leisure')
               or t.get('office') or t.get('healthcare') or '?')
        kayit.append(dict(
            osm_tip=e['type'], osm_id=e['id'], mahalle=mah,
            ad=t.get('name') or '(isimsiz)', tur=tur, grup=GRUP.get(tur, 'diger'),
            kaynak=kaynak, tesis_m2=round(tesis_alan, 1) if tesis_alan else None,
            bina_idx=bina_idx, bina_ic=len(bina_idx),
            mulkiyet=mlk, mulkiyet_kanit=kanit,
            kat=t.get('building:levels'),
            isletmeci=t.get('operator'), isletmeci_tur=t.get('operator:type'),
            geom=g))

    print('  %s icinde kayit: %d  (nokta->bina eslesen %d, eslesmeyen %d)'
          % (ILCE, len(kayit), nokta_eslesen, nokta_eslesmeyen))

    # --------------------------------------------------- kuresel tekillestirme
    # Bir OSM bina poligonu en fazla BIR kayda sayilir. Once poligon kayitlar
    # (kapsama iliskisi kesin), sonra nokta kayitlar bos kalan binalari alir.
    # Bu adim olmadan ayni blokta oturan POI'ler blogu tekrar tekrar sayiyor.
    sahip = {}
    for k in sorted(kayit, key=lambda x: 0 if x['kaynak'] == 'poligon' else 1):
        alinan = [i for i in k['bina_idx'] if i not in sahip]
        for i in alinan:
            sahip[i] = k
        k['_alinan'] = alinan
    bina_alan = {}
    for k in kayit:
        for i in k['_alinan']:
            if i not in bina_alan:
                bina_alan[i] = transform(to_utm, binalar[i]).area
        k['cati_m2'] = round(sum(bina_alan[i] for i in k['_alinan']), 1) or None
        ham = sum(bina_alan.get(i) or transform(to_utm, binalar[i]).area
                  for i in k['bina_idx']) if k['bina_idx'] else 0
        k['cati_ham_m2'] = round(ham, 1) or None
        k['doluluk'] = (round(k['cati_m2'] / k['tesis_m2'], 3)
                        if (k['cati_m2'] and k['tesis_m2']) else None)
    cifte = sum(1 for k in kayit if k['bina_idx'] and len(k['_alinan']) < len(k['bina_idx']))
    ham_t = sum(k['cati_ham_m2'] or 0 for k in kayit)
    tek_t = sum(k['cati_m2'] or 0 for k in kayit)
    print('  tekillestirme: %d kayit baska kaydin binasini paylasiyordu; '
          'cati %s -> %s m2 (%%%.1f dusus)'
          % (cifte, format(int(ham_t), ',d').replace(',', '.'),
             format(int(tek_t), ',d').replace(',', '.'),
             100 * (1 - tek_t / ham_t) if ham_t else 0))

    # ------------------------------------------------------------ rapor
    alanli = [k for k in kayit if k['cati_m2']]
    catisiz = [k for k in kayit if not k['cati_m2']]

    def bicim(x):
        return format(int(x), ',d').replace(',', '.')

    print('\n  GRUBA GORE   (tesis = OSM poligonu, cati = icindeki bina poligonlari)')
    print('  %-15s %5s %6s %11s %11s %8s %9s'
          % ('grup', 'adet', 'catili', 'tesis m2', 'CATI m2', 'doluluk', 'cati med.'))
    for grp in ['egitim', 'saglik', 'idari', 'sosyal-kultur', 'spor', 'diger']:
        g = [k for k in kayit if k['grup'] == grp]
        if not g:
            continue
        tt = sum(k['tesis_m2'] or 0 for k in g)
        cc = [k['cati_m2'] for k in g if k['cati_m2']]
        print('  %-15s %5d %6d %11s %11s %8s %9s'
              % (grp, len(g), len(cc), bicim(tt), bicim(sum(cc)) if cc else '-',
                 '%.2f' % (sum(cc) / tt) if cc and tt else '-',
                 '%.0f' % np.median(cc) if cc else '-'))
    TT = sum(k['tesis_m2'] or 0 for k in kayit)
    CC = [k['cati_m2'] for k in alanli]
    print('  %-15s %5d %6d %11s %11s %8s %9s'
          % ('TOPLAM', len(kayit), len(alanli), bicim(TT), bicim(sum(CC)),
             '%.2f' % (sum(CC) / TT), '%.0f' % np.median(CC)))
    print('  !! Tesis alani cati DEGILDIR: amenity=school cogunlukla okul bahcesinin')
    print('     tamamina konuyor (bahce, spor sahasi, otopark dahil).')
    if catisiz:
        print('  !! %d kayitta cati BILINMIYOR (icinde bina poligonu yok) -' % len(catisiz))
        print('     sifir degil, EKSIK olarak islenmeli.')

    print('\n  ESKI KUME ILE KARSILASTIRMA')
    try:
        eski = json.load(open(yol('data/osm_izmir_kamu.json'), encoding='utf-8'))['elements']
        ee = 0
        for x in eski:
            lo = x.get('lon') or (x.get('center') or {}).get('lon')
            la = x.get('lat') or (x.get('center') or {}).get('lat')
            if lo and hangi(Point(lo, la)):
                ee += 1
        print('    eski (data/osm_izmir_kamu.json) : %d kayit, alan YOK' % ee)
        print('    yeni                            : %d kayit, %d tanesi cati alanli'
              % (len(kayit), len(alanli)))
    except Exception as ex:
        print('    karsilastirilamadi: %s' % ex)

    print('\n  MAHALLEYE GORE (ilk 10, cati alanina gore)')
    mah_alan = {}
    for k in kayit:
        if k['mulkiyet'] != 'kamu':
            continue
        mah_alan.setdefault(k['mahalle'], [0, 0.0])
        mah_alan[k['mahalle']][0] += 1
        mah_alan[k['mahalle']][1] += k['cati_m2'] or 0
    for m, (n, a) in sorted(mah_alan.items(), key=lambda x: -x[1][1])[:10]:
        print('    %-24s %3d tesis  %9s m2 cati' % (m, n, bicim(a)))
    yok = [m['mahalle'] for m in mahalleler if m['mahalle'] not in mah_alan]
    if yok:
        print('    kamu binasi bulunmayan %d mahalle: %s' % (len(yok), ', '.join(yok)))

    print('\n  MULKIYET SINIFLANDIRMASI  (operator etiketi + Turkce isim kalibi)')
    print('  %-10s %6s %12s  %s' % ('mulkiyet', 'adet', 'cati m2', 'en buyuk iki ornek'))
    for m in ('kamu', 'ozel', 'belirsiz'):
        g = [k for k in kayit if k['mulkiyet'] == m]
        a = sum(k['cati_m2'] or 0 for k in g)
        orn = ' · '.join(k['ad'][:24] for k in
                         sorted(g, key=lambda x: -(x['cati_m2'] or 0))[:2])
        print('  %-10s %6d %12s  %s' % (m, len(g), bicim(a), orn))
    bel = [k for k in kayit if k['mulkiyet'] == 'belirsiz']
    print('  -> SKORA YALNIZCA \'kamu\' GIRER. \'belirsiz\' kamu SAYILMAZ:')
    print('     %d kayit / %s m2 disarida kaliyor.'
          % (len(bel), bicim(sum(k['cati_m2'] or 0 for k in bel))))
    print('     Bu SEZGISEL bir siniflandirma; mulkiyet_kanit sutunu her karari')
    print('     gerekcelendiriyor, en buyuk 20 tesis elle dogrulanmali.')

    # ------------------------------------------------------------ cikti
    ad = sadelestir(ILCE)
    ozellikler = [{'type': 'Feature', 'geometry': mapping(k['geom']),
                   'properties': {a: k[a] for a in k
                                  if a not in ('geom', 'bina_idx', '_alinan')}}
                  for k in kayit]
    json.dump({'type': 'FeatureCollection',
               'meta': {'ilce': ILCE, 'uretim': time.strftime('%Y-%m-%d %H:%M'),
                        'etiketler': ['%s=%s' % t for t in ETIKETLER],
                        'nokta_yaricap_m': NOKTA_YARICAP,
                        'not': 'Kamu HIZMETI binasi; mulkiyet degil islev etiketi. '
                               'tesis_m2 = OSM poligonu (okulda bahce dahil), '
                               'cati_m2 = icindeki bina poligonlarinin toplami. '
                               'Uretim hesabinda cati_m2 kullanilmali.'},
               'features': ozellikler},
              io.open(yol('cache/kamu_%s.geojson' % ad), 'w', encoding='utf-8'),
              ensure_ascii=False)
    sut = ['mahalle', 'ad', 'tur', 'grup', 'mulkiyet', 'mulkiyet_kanit',
           'cati_m2', 'cati_ham_m2', 'tesis_m2', 'doluluk', 'bina_ic', 'kat',
           'kaynak', 'isletmeci', 'isletmeci_tur', 'osm_tip', 'osm_id']
    with io.open(yol('cache/kamu_%s.csv' % ad), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=sut, delimiter=';')
        w.writeheader()
        for k in sorted(kayit, key=lambda x: (x['mahalle'], -(x['cati_m2'] or 0))):
            w.writerow({s: k.get(s) for s in sut})
    print('\n  -> cache/kamu_%s.geojson  |  cache/kamu_%s.csv' % (ad, ad))
