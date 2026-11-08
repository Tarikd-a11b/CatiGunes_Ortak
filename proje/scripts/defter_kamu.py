"""Kamu kipli Çiğli defterini üretir: Overpass'e bağımlı olmadan, tesis + bina verisi gömülü.

Neden: Colab IP'sinde Overpass 429/504 veriyor; 2026-09-14'te yerel IP'den de tıkalıydı.
Tesisler cache/kamu_cigli.geojson'dan (kamu_cati_eslestir.py ile AYNI küme), binalar
cache/osm_binalar_cigli.geojsonl önbelleğinden, tesis çevresi (defterdeki odak yarıçapı) kadar alınır.

Çalıştırma:  python scripts/defter_cigli_segmentasyon.py   (önce ana defteri üret)
             python scripts/defter_kamu.py
Çıktı:       notebooks/CatiGunes_Cigli_Kamu.ipynb
"""
import base64, gzip, json, math, os
import nbformat as nbf
from shapely.geometry import shape, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
yol = lambda *p: os.path.join(KOK, *p)
LAT_C = 38.49

tesis_fc = json.load(open(yol('cache', 'kamu_cigli.geojson'), encoding='utf-8'))
tesisler, kutular = [], []
for f in tesis_fc['features']:
    g, p = shape(f['geometry']), f['properties']
    kimlik = int(p['osm_id'])
    if g.geom_type == 'Point':
        tesisler.append({'type': 'node', 'id': kimlik, 'lat': g.y, 'lon': g.x})
        la, lo, r = g.y, g.x, 60.0
    else:
        g = max(getattr(g, 'geoms', [g]), key=lambda q: q.area)
        tesisler.append({'type': p['osm_tip'] if p['osm_tip'] != 'node' else 'way', 'id': kimlik,
                         'geometry': [{'lat': y, 'lon': x} for x, y in g.exterior.coords]})
        bx = g.bounds
        yari = max(111320 * (bx[3] - bx[1]), 111320 * math.cos(math.radians(LAT_C)) * (bx[2] - bx[0])) / 2
        la, lo, r = g.centroid.y, g.centroid.x, min(max(yari + 80, 80), 400)
    dx, dy = r / (111320 * math.cos(math.radians(la))), r / 111320
    kutular.append(box(lo - dx, la - dy, lo + dx, la + dy))

alan = unary_union(kutular)
agac = STRtree(list(getattr(alan, 'geoms', [alan])))
binalar = []
with open(yol('cache', 'osm_binalar_cigli.geojsonl'), encoding='utf-8') as fh:
    for satir in fh:
        f = json.loads(satir)
        g = shape(f['geometry'])
        if not len(agac.query(g, predicate='intersects')):
            continue
        halkalar = [[{'lat': round(y, 7), 'lon': round(x, 7)} for x, y in q.exterior.coords] for q in getattr(g, 'geoms', [g])]
        tip, kimlik = f['properties']['osm_tip'], int(f['properties']['osm_id'])
        if tip == 'way' and len(halkalar) == 1:
            binalar.append({'type': 'way', 'id': kimlik, 'geometry': halkalar[0]})
        else:
            binalar.append({'type': 'relation', 'id': kimlik, 'members': [{'type': 'way', 'role': 'outer', 'geometry': h} for h in halkalar]})

meta = f"tesis {len(tesisler)} ({tesis_fc['meta'].get('uretim')}), bina {len(binalar)} (OSM önbelleği cache/osm_binalar_cigli.geojsonl)"
yuk = base64.b64encode(gzip.compress(json.dumps({'meta': meta, 'tesisler': tesisler, 'binalar': binalar},
                                                separators=(',', ':')).encode(), 9)).decode()
print(meta, '| gömülü', len(yuk) // 1024, 'kB')

nb = nbf.read(yol('notebooks', 'CatiGunes_Cigli_Segmentasyon.ipynb'), as_version=4)
nb.cells[0].source = f'''# Çiğli kamu binaları: çatı segmentasyonu ve üretim potansiyeli

Bu defter, Çiğli geneli defterinin **kamu kipi**dir: ilçenin tamamı yerine yalnız **kamu tesislerine düşen binalar** işlenir (okul, sağlık ocağı, muhtarlık, itfaiye, kültür merkezi, spor salonu…).

* Tesis kümesi `kamu_binalari.py` çıktısıdır (`cache/kamu_cigli.geojson`); `kamu_cati_eslestir.py` ile aynı küme.
* **Tesisler ve çevrelerindeki binalar deftere gömülüdür** (bölüm 2'den önceki hücre): Overpass Colab IP'sinde 429/504 verdiği için bina adımı Overpass'e gitmez. Gömülü veri: {meta}.
* Mülkiyet/grup/isim zenginleştirmesi bu defterde değil, `scripts/kamu_cati_eslestir.py` ile çıktı üzerinde yapılır.

**Çalıştırma:** Çalışma zamanı türü **T4 GPU** → Tümünü çalıştır. Yaklaşık 5–10 dakika. Çıktı dosyalarını almak için 13. bölümde `INDIR = True` olmalı.

⚠️ Üretim toplamlarında mülkiyeti 'özel' çıkan tesisler dışarıda bırakılmalı; 166 tesisin 77'sinde mülkiyet 'belirsiz'.'''
for c in nb.cells:
    if c.cell_type == 'code':
        c.source = c.source.replace('INDIR = False', 'INDIR = True')
        c.source = c.source.replace('HEDEF_KAMU = False', 'HEDEF_KAMU = True')
yer = next(i for i, c in enumerate(nb.cells) if c.cell_type == 'markdown' and c.source.startswith('## 2 · Bina ayak izleri'))
nb.cells.insert(yer, nbf.v4.new_code_cell(
    '# Gömülü kamu verisi (scripts/defter_kamu.py üretti) — Overpass yerine bunu kullanır\n'
    f'# {meta}\nKAMU_VERI = "{yuk}"\nprint(len(KAMU_VERI) // 1024, "kB gömülü veri")'))
hedef = yol('notebooks', 'CatiGunes_Cigli_Kamu.ipynb')
nbf.write(nb, hedef)
print('yazıldı:', hedef, os.path.getsize(hedef) // 1024, 'kB')
