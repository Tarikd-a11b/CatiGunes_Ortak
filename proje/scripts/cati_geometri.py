# -*- coding: utf-8 -*-
"""Her catinin SON cati geometrisi (2026-10-24): insan cizimi > SAM > ayak izi.
  python scripts/cati_geometri.py aktar   -> Cizim_Paketi (LabelMe) cizimlerini veri/elle/insan_cizimleri.geojson'a alir
  python scripts/cati_geometri.py         -> Model_Verisi: catilar.gpkg 'cati_son' katmani + catilar'a geometri_kaynagi, cati_alan_m2
Kurallar:
  insan    : cizim varsa (oncelik: 7_yeniden > 6_eksik_test > 1_test_referans > 2_kamu_ek/3_supheli_ek > 4_panel > 5_ikinci_cizim).
             bina_belirsiz isaretli cati insan cizimi almaz. Insan poligonu komsu bir catinin ayak izinin > %15'ini
             kapliyorsa kullanilmaz (cift sayim; ayak_izi_duzeltme.py ile ayni esik).
  sam      : insan yoksa ve SAM supheli degilse.
  ayak_izi : SAM supheli (ya da SAM poligonu yok) ve insan cizimi yok.
'geometry' (ayak izi) DEGISMEZ: SAM kesitleri ve zincirin geri kalani ona bagli."""
import glob, json, math, os, sys
import numpy as np, pandas as pd, geopandas as gpd
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
from shapely.validation import make_valid

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda *p: os.path.join(KOK, 'veri', *p)
MV = os.path.join(os.path.expanduser('~'), 'Desktop', 'CatiGunes_Model_Verisi')
PAKET = os.path.join(os.path.expanduser('~'), 'Desktop', 'Toplantı', 'Cizim_Paketi')
SAM = V('ham', 'sam', 'birlesik_2026-10-30')   # 2026-10-30: GES paketi + c1388 dahil 20 cati yeniden kosuldu
INSAN = V('elle', 'insan_cizimleri.geojson')
SORUN = V('elle', 'test_referans', 'ayakizi_duzeltme_listesi.csv')
PANELSIZ = V('elle', 'panelsiz_cizimleri.geojson')
R = 6378137.0
CAKISMA_ESIK = 0.15
# (klasor, set, cizen) - ust satir oncelikli
KAYNAKLAR = [('7_yeniden_cizim/cizimler_donusturulmus', '7_yeniden_cizim', 'bilal'),
             ('6_eksik_test/cizimler_donusturulmus', '6_eksik_test', 'bilal'),
             ('1_test_referans/cizimler_donusturulmus', '1_test_referans', 'arkadas'),
             ('2_kamu_ek/cizimler_donusturulmus', '2_kamu_ek', 'bilal'),
             ('3_supheli_ek/cizimler_donusturulmus', '3_supheli_ek', 'bilal'),
             ('4_panel/cizimler_cati_donusturulmus', '4_panel', 'bilal'),
             ('5_ikinci_cizim/cizimler_donusturulmus', '5_ikinci_cizim', 'bilal')]


def px_lonlat(kesit, pts):
    """kesit pikseli -> lon/lat (ayak_izi_duzeltme.py ile ayni: .jgw piksel merkezi, poligon kose tabanli)."""
    a, _, _, e, c, f = [float(x) for x in open(os.path.join(MV, 'cati_kesitleri', kesit[:-4] + '.jgw')).read().split()]
    return [(math.degrees((c - a / 2 + x * a) / R), math.degrees(math.atan(math.sinh((f - e / 2 + y * e) / R))))
            for x, y in pts]


def aktar():
    s = pd.read_csv(os.path.join(SAM, 'sam_sonuc_tam.csv'))
    s['dosya'] = s.maske_dosyasi.str.split('/').str[-1].str[:-4]
    s = s.set_index('dosya')
    hatali = set(pd.read_csv(SORUN).query("sorun == 'ayakizi_hatali'").cati_id) if os.path.exists(SORUN) else set()
    kayit, gorulen, yanlis = [], set(), []
    for klasor, set_, kim in KAYNAKLAR:
        for f in sorted(glob.glob(os.path.join(PAKET, klasor, 'c*.json'))):
            d = os.path.basename(f)[:-5]
            j = json.load(open(f, encoding='utf-8'))
            if d in gorulen or not j['shapes']:
                continue
            r = s.loc[d]
            # 2026-10-24: kendi ayak izinin < %5'ini kaplayan cizim baska binaya cizilmis (c1307) -> siradaki kaynaga gec.
            # Ayak izinin hatali oldugu bilinen catilar haric (orada insan dogru binayi cizmis olabilir).
            ayak = Polygon(json.loads(r.poligon_px)).buffer(0)
            ciz = make_valid(Polygon(j['shapes'][0]['points']))
            for sh in j['shapes'][1:]:
                ciz = ciz.union(make_valid(Polygon(sh['points'])))
            if int(r.cati_id) not in hatali and ciz.intersection(ayak).area < 0.05 * ayak.area:
                yanlis.append('%s/%s' % (set_, d))
                continue
            gorulen.add(d)
            g = make_valid(Polygon(px_lonlat(r.kesit, j['shapes'][0]['points'])))
            for sh in j['shapes'][1:]:
                g = g.union(make_valid(Polygon(px_lonlat(r.kesit, sh['points']))))
            kayit.append(dict(cati_id=int(r.cati_id), dosya=d, set=set_, cizen=kim, geometry=g))
    gpd.GeoDataFrame(kayit, crs=4326).to_file(INSAN, driver='GeoJSON')
    print('%d insan cizimi -> %s' % (len(kayit), INSAN))
    print('ayak izine dokunmayan (baska bina) cizimler atlandi:', yanlis)
    # 4_panel: kismi GES'li catida panel OLMAYAN (kullanilabilir) alan; etiket 'panelsiz', bir catida birden cok parca olabilir
    pk = []
    for f in sorted(glob.glob(os.path.join(PAKET, '4_panel', 'cizimler_donusturulmus', 'c*.json'))):
        d = os.path.basename(f)[:-5]
        j = json.load(open(f, encoding='utf-8'))
        if not j['shapes']:
            continue
        r = s.loc[d]
        g = None
        for sh in j['shapes']:
            p = make_valid(Polygon(px_lonlat(r.kesit, sh['points'])))
            g = p if g is None else g.union(p)
        pk.append(dict(cati_id=int(r.cati_id), dosya=d, geometry=g))
    gpd.GeoDataFrame(pk, crs=4326).to_file(PANELSIZ, driver='GeoJSON')
    print('%d panelsiz alan cizimi -> %s' % (len(pk), PANELSIZ))


def lonlat_px(kesit, pts):
    """px_lonlat'in tersi."""
    a, _, _, e, c, f = [float(x) for x in open(os.path.join(MV, 'cati_kesitleri', kesit[:-4] + '.jgw')).read().split()]
    return [((R * math.radians(lo) - (c - a / 2)) / a,
             (R * math.log(math.tan(math.pi / 4 + math.radians(la) / 2)) - (f - e / 2)) / e) for lo, la in pts]


def referans_paketi(cat):
    """Model ekibi icin: insan cizimli catilar -> goruntu + insan maskesi + bolum (ayar / test / dislandi).
    test = SAM veri setinin test_referans bolumu (yalniz OLCUM, ayara kullanilmaz); dislandi = insan ile kayit ayni
    binaya bakmiyor (ayakizi_eksik/hatali, bina_belirsiz, SAM'i gorerek cizildi, komsuya tasiyor)."""
    import shutil, numpy as np
    from PIL import Image, ImageDraw
    ins = gpd.read_file(INSAN)
    s = pd.read_csv(os.path.join(SAM, 'sam_sonuc_tam.csv')).set_index('cati_id')
    iou = pd.read_csv(V('elle', 'test_referans', 'iou_sonuc.csv')).set_index('cati_id')
    notu = cat.set_index('cati_id').geometri_notu
    H = os.path.join(MV, 'insan_referans')
    import time
    for _ in range(10):   # Windows (Gezgin/indeksleyici) klasoru kisa sure kilitleyebiliyor -> tekrar dene
        if not os.path.exists(H): break
        shutil.rmtree(H, ignore_errors=True); time.sleep(1)
    for d in ('goruntuler', 'insan_maske'):
        os.makedirs(os.path.join(H, d), exist_ok=True)
    satir = []
    for r in ins.itertuples():
        q = s.loc[r.cati_id]
        im = Image.open(os.path.join(MV, 'cati_kesitleri', q.kesit)).convert('RGB')
        m = Image.new('L', im.size, 0)
        dr = ImageDraw.Draw(m)
        for p in getattr(r.geometry, 'geoms', [r.geometry]):
            dr.polygon(lonlat_px(q.kesit, p.exterior.coords), fill=255)
            for ic in p.interiors:
                dr.polygon(lonlat_px(q.kesit, ic.coords), fill=0)
        im.save(os.path.join(H, 'goruntuler', r.dosya + '.jpg'), quality=95)
        m.save(os.path.join(H, 'insan_maske', r.dosya + '.png'))
        neden = []
        iset = iou.set.get(r.cati_id, '')
        for k in ('ayakizi_eksik', 'ayakizi_hatali', 'bina_belirsiz', 'bagimsiz_degil'):
            if k in iset:
                neden.append(k)
        if 'komsuya tasiyor' in str(notu.get(r.cati_id, '')):
            neden.append('komsuya_tasiyor')
        bolum = 'dislandi' if neden else ('test' if q.bolum == 'test_referans' else 'ayar')
        satir.append(dict(cati_id=r.cati_id, dosya=r.dosya, bolum=bolum, dislama=';'.join(neden) or None,
                          cizim_seti=r.set, cizen=r.cizen, tur=q.tur, alan_sinifi=q.alan_sinifi, sam_supheli=q.supheli,
                          kutu_px=q.kutu_px, poligon_px=q.poligon_px, yer_m_px=q.yer_m_px))
    t = pd.DataFrame(satir).sort_values('cati_id')
    t.to_csv(os.path.join(H, 'liste.csv'), index=False, encoding='utf-8-sig')
    open(os.path.join(H, 'BENIOKU.md'), 'w', encoding='utf-8').write(
        '# İnsan referansı (SAM ayarı / değerlendirme)\n\n'
        '`goruntuler/cNNNN.jpg` = SAM girdisiyle aynı kesit; `insan_maske/cNNNN.png` = LabelMe insan çizimi (255 = çatı). '
        '`liste.csv`: `bolum` **ayar** (kural/ince ayar burada denenir), **test** (yalnız son ölçüm — ayara KULLANMA), '
        '**dislandi** (insan ile kayıt aynı binaya bakmıyor; `dislama` sütunu). `kutu_px` = SAM\'e verilen kutu.\n\n'
        'Dağılım: %s. Üretici: `scripts/cati_geometri.py`.\n' % ', '.join('%s %d' % kv for kv in t.bolum.value_counts().items()))
    shutil.make_archive(H, 'zip', H)
    print('insan_referans:', t.bolum.value_counts().to_dict())
    return t


def main():
    gp = os.path.join(MV, 'catilar.gpkg')
    cat = gpd.read_file(gp, layer='catilar')
    sam = gpd.read_file(os.path.join(SAM, 'sam_poligonlari.geojson')).set_index('cati_id')
    # geojson'da supheli metin ('hayır'/'EVET') -> mantiksal deger sonuc tablosundan
    ss = pd.read_csv(os.path.join(SAM, 'sam_sonuc_tam.csv')).set_index('cati_id')
    sam['supheli'] = ss.supheli.astype(bool)
    # 2026-10-28: ayak izi SAM kosusundan sonra elle duzeltildiyse (> %2 alan farki, or. c1388) SAM maskesi eski ayak izine
    # gore kirpilmis -> Colab yeniden kosana kadar SAM kullanilmaz (sam_birlesik_paketi.py ile ayni esik)
    # alan, paketteki gibi kesitte cizilen ayak izi maskesinden (piksel) olculur
    idx = pd.read_csv(os.path.join(MV, 'cati_kesitleri', 'indeks.csv')).set_index('osm')
    ayak_px = {}
    for cid, o in zip(cat.cati_id, cat.osm):
        r = idx.loc[o]
        mk = Image.new('L', (int(r.genislik_px), int(r.yukseklik_px)), 0)
        ImageDraw.Draw(mk).polygon([tuple(p) for p in json.loads(r.poligon_px)], fill=255)
        ayak_px[cid] = (np.array(mk) > 0).sum() * r.yer_m_px ** 2
    sam_eski = set(ss.index[(ss.ayak_izi_m2 - ss.index.map(ayak_px)).abs() > 0.02 * ss.ayak_izi_m2])
    ins = gpd.read_file(INSAN).set_index('cati_id') if os.path.exists(INSAN) else gpd.GeoDataFrame(geometry=[], crs=4326)
    sorun = pd.read_csv(SORUN).set_index('cati_id').sorun if os.path.exists(SORUN) else pd.Series(dtype=str)
    cu = cat.to_crs(32635).set_index('cati_id').geometry
    insu = ins.to_crs(32635).geometry
    samu = sam.to_crs(32635).geometry
    satir = []
    for cid in cat.cati_id:
        kaynak, g, notlar = None, None, []
        if cid in insu.index and sorun.get(cid) != 'bina_belirsiz':
            h = insu.loc[cid]
            komsu = cu.drop(cid)
            komsu = komsu[komsu.intersects(h)]
            tas = [(o, h.intersection(k).area / k.area) for o, k in komsu.items()]
            tas = [(o, p) for o, p in tas if p > CAKISMA_ESIK]
            if tas:
                notlar.append('insan cizimi komsuya tasiyor (%s), kullanilmadi' %
                              ', '.join('cati %d %%%d' % (o, 100 * p) for o, p in tas))
            else:
                kaynak, g = 'insan', h
        if kaynak is None and cid in samu.index and not sam.loc[cid, 'supheli'] and samu.loc[cid] is not None \
                and not samu.loc[cid].is_empty and cid not in sam_eski:
            kaynak, g = 'sam', samu.loc[cid]
        if kaynak is None:
            kaynak, g = 'ayak_izi', cu.loc[cid]
            if cid in sam_eski:
                notlar.append('SAM eski ayak izine gore (Colab yeniden kosulacak)')
            elif cid in sam.index and sam.loc[cid, 'supheli']:
                notlar.append('SAM supheli')
        if isinstance(sorun.get(cid), str):
            notlar.append(sorun.get(cid))
        satir.append(dict(cati_id=cid, geometri_kaynagi=kaynak, cati_alan_m2=round(g.area, 1),
                          geometri_notu='; '.join(notlar) or None, geometry=g))
    # mevcut GES: tam -> uygun alan 0; kismi -> insanin cizdigi panelsiz alan (son cati ile kesisimi); yoksa cati (not)
    pz = gpd.read_file(PANELSIZ).to_crs(32635).set_index('cati_id').geometry if os.path.exists(PANELSIZ) else {}
    ges = cat.set_index('cati_id').mevcut_ges
    # 2026-10-24 gorsel karar (4_panel/goruntuler): kismi isaretli ama cati neredeyse tamamen panelli,
    # kalan serit isiklik/oluklu kenar -> tam sayilir (ihtiyatli, uygun alan 0)
    KISMI_TAM_SAYILAN = {157, 319}
    for x in satir:
        cid, g = x['cati_id'], x['geometry']
        if ges.get(cid) == 'tam' or (ges.get(cid) == 'kismi' and cid in KISMI_TAM_SAYILAN):
            x['panel_durumu'], u = 'tam_dolu', g.buffer(0).difference(g.buffer(0))
        elif ges.get(cid) == 'kismi' and cid in pz.index:
            x['panel_durumu'], u = 'kismi_panel_dusuldu', g.buffer(0).intersection(pz.loc[cid].buffer(0))
        elif ges.get(cid) == 'kismi':
            x['panel_durumu'], u = 'kismi_panel_cizilmedi', g
        else:
            x['panel_durumu'], u = 'panel_yok', g
        x['uygun_alan_m2'] = round(u.area, 1)
        x['uygun_geom'] = u
    uyg = gpd.GeoDataFrame([dict(cati_id=x['cati_id'], panel_durumu=x['panel_durumu'], uygun_alan_m2=x['uygun_alan_m2'],
                                 geometry=x.pop('uygun_geom')) for x in satir], crs=32635).to_crs(4326)
    uyg = uyg[~uyg.geometry.is_empty]
    son = gpd.GeoDataFrame(satir, crs=32635).to_crs(4326)
    m = son.set_index('cati_id')
    for c in ('geometri_kaynagi', 'cati_alan_m2', 'geometri_notu', 'panel_durumu', 'uygun_alan_m2'):
        cat[c] = cat.cati_id.map(m[c])
    cat.to_file(gp, layer='catilar', driver='GPKG')
    son.to_file(gp, layer='cati_son', driver='GPKG')
    uyg.to_file(gp, layer='uygun_alan', driver='GPKG')
    print(son.groupby('panel_durumu').agg(cati=('cati_id', 'size'), cati_m2=('cati_alan_m2', 'sum'),
                                          uygun_m2=('uygun_alan_m2', 'sum')).round(0).to_string())
    cat.drop(columns='geometry').to_csv(os.path.join(MV, 'catilar.csv'), index=False, encoding='utf-8-sig')
    # tek duz ana tablo (2026-10-28, ekip arkadasinin master_veriseti fikri): catilar + SAM metrikleri; potansiyel = uygun_alan_m2
    ana = cat.drop(columns='geometry').merge(
        ss[['sam_alan_m2', 'kaplama', 'tasma', 'iou_ayak', 'guven', 'supheli', 'kosu']].rename(columns={'kosu': 'sam_kosu'}),
        left_on='cati_id', right_index=True, how='left')
    ana['sam_guncel'] = ~ana.cati_id.isin(sam_eski)
    ana.to_csv(os.path.join(MV, 'master_veriseti.csv'), index=False, encoding='utf-8-sig')
    print('master_veriseti.csv: %d cati, %d sutun, SAM eski %s' % (len(ana), ana.shape[1], sorted(sam_eski)))
    ozet = son.groupby('geometri_kaynagi').agg(cati=('cati_id', 'size'), alan_m2=('cati_alan_m2', 'sum'))
    print(ozet.round(0).to_string())
    print('toplam cati alani %.0f m2 (ayak izi toplami %.0f m2)' % (son.cati_alan_m2.sum(), cu.area.sum()))
    if os.path.exists(INSAN):
        referans_paketi(cat)
    bm = os.path.join(MV, 'BENIOKU.md')
    if os.path.exists(bm):
        open(bm, 'a', encoding='utf-8').write(
            '\n## Son çatı geometrisi (`catilar.gpkg` katman `cati_son`)\n'
            'Her çatı için panele esas çatı poligonu; `geometry` (katman `catilar`) ayak izi olarak kalır. '
            'Öncelik: **insan** çizimi (LabelMe, `veri/elle/insan_cizimleri.geojson`) > **sam** (şüpheli değilse) > **ayak_izi**. '
            'Komşu çatının ayak izinin >%%15\'ini kaplayan insan çizimi kullanılmaz. Sütunlar: `geometri_kaynagi`, `cati_alan_m2` '
            '(UTM 35N), `geometri_notu` (ayakizi_eksik / ayakizi_hatali / bina_belirsiz / SAM şüpheli). '
            'Dağılım: %s.\n\n'
            '**Panel düşülmüş alan** (katman `uygun_alan`, sütunlar `panel_durumu`, `uygun_alan_m2`): mevcut GES tam → 0; '
            'kısmi → elle çizilen panelsiz alan (`veri/elle/panelsiz_cizimleri.geojson`) ∩ son çatı; kısmi ama çizim yok → '
            'çatının tamamı (`kismi_panel_cizilmedi`, dikkat); c0157 ve c0319 görselle neredeyse tam dolu bulundu → tam sayıldı. PVGIS/NPV hesabında `uygun_alan_m2` kullanılmalı.\n\n'
            '**Ana tablo** (`master_veriseti.csv`): `catilar.csv` + SAM metrikleri (`sam_alan_m2`, `kaplama`, `tasma`, `iou_ayak`, '
            '`guven`, `supheli`, `sam_kosu`); `sam_guncel` = False ise ayak izi SAM koşusundan sonra düzeltildi, SAM değerleri eski. '
            'Tek satır = tek çatı; web ve NPV için bu tablo kullanılır (alan: `cati_alan_m2`, potansiyel: `uygun_alan_m2`).\n'
            % ', '.join('%s %d' % (k, v) for k, v in ozet.cati.items()))


if __name__ == '__main__':
    aktar() if sys.argv[1:] == ['aktar'] else main()
