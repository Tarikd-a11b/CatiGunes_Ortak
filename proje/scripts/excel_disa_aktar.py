# -*- coding: utf-8 -*-
"""veri/ham -> inceleme icin Excel + ornek dict (JSON).
Cikti: veri/inceleme/bina_verileri.xlsx, veri/inceleme/ornek_kayitlar.json
Her binaya merkez konumu, taban alani, OSM etiketleri eklenir.
2026-10-15: golge analizi projeden cikti -> 3D-GloBFP yuksekligi kaldirildi; kamu = yalniz devlet okul + hastane."""
import json, os, pandas as pd
from shapely.geometry import shape

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = lambda *p: os.path.join(KOK, 'veri', 'ham', *p)
OUT = os.path.join(KOK, 'veri', 'inceleme'); os.makedirs(OUT, exist_ok=True)
fc = lambda p: json.load(open(p, encoding='utf-8'))['features']


def binalar(bolge):
    F = fc(H('osm', 'binalar_%s.geojson' % bolge))
    geo = [shape(f['geometry']) for f in F]
    satir = []
    for f, g in zip(F, geo):
        p = dict(f['properties']); c = g.representative_point()
        satir.append({'osm_id': p.pop('osm'), 'lon': round(c.x, 6), 'lat': round(c.y, 6),
                      'taban_alan_m2': p.pop('alan_m2'), 'bina_turu_osm': p.pop('building', None),
                      'kat_osm': p.pop('building:levels', None),
                      'ad': p.pop('name', None),
                      'diger_etiketler': '; '.join('%s=%s' % kv for kv in sorted(p.items())) or None})
    return pd.DataFrame(satir).sort_values('taban_alan_m2', ascending=False)


def kamu():
    s = []
    for f in fc(os.path.join(KOK, 'veri', 'islenmis', 'kamu_okul_hastane_cigli.geojson')):
        p = f['properties']; c = shape(f['geometry']).representative_point()
        s.append({'osm_id': p['osm'], 'ad': p['ad'], 'tur': p['tur'], 'sahiplik_gerekcesi': p['gerekce'],
                  'geometri': f['geometry']['type'], 'tesis_alan_m2': p.get('tesis_alan_m2'),
                  'lon': round(c.x, 6), 'lat': round(c.y, 6), 'operator': p['etiketler'].get('operator')})
    return pd.DataFrame(s).sort_values(['tur', 'ad'])


def pvgis():
    oz, ay = [], []
    for b in ('ataturk_osb', 'cigli'):
        for s in ('egim10_guney', 'optimum', 'dogu_bati_10'):
            d = json.load(open(H('pvgis', '%s_pv_%s.json' % (b, s))))
            m = d['inputs']['mounting_system']['fixed']
            oz.append({'bolge': b, 'senaryo': s, 'egim': m['slope']['value'], 'azimut_pvgis(0=guney)': m['azimuth']['value'],
                       'yillik_kWh_per_kWp': d['outputs']['totals']['fixed']['E_y']})
            if s == 'egim10_guney':
                for r in d['outputs']['monthly']['fixed']:
                    ay.append({'bolge': b, 'ay': r['month'], 'aylik_kWh_per_kWp': r['E_m'], 'gunluk_isinim_kWh_m2': r['H(i)_d']})
    tmy = json.load(open(H('pvgis', 'ataturk_osb_tmy.json')))['outputs']['tmy_hourly']
    return pd.DataFrame(oz), pd.DataFrame(ay), pd.DataFrame(tmy[:24 * 7])  # TMY ilk hafta ornek


osb, cig = binalar('ataturk_osb'), binalar('cigli')
km = kamu()
firma = pd.read_csv(H('iaosb', 'iaosb_firmalar.csv'), sep=';', dtype=str)
oz, ay, tmy = pvgis()

aciklama = pd.DataFrame([
    ('OSB_binalari', 'Ataturk OSB, OSM bina poligonlari (%d). Konum = poligon ici nokta.' % len(osb)),
    ('Cigli_binalari', 'Cigli ilcesi OSM binalari (%d).' % len(cig)),
    ('Kamu_tesisleri', 'Cigli DEVLET okul + hastaneleri (%d kayit; ozel kurumlar cikarildi, karar tablosu kamu_secim_kontrol.xlsx).' % len(km)),
    ('IAOSB_firmalar', 'IAOSB firma rehberi (%d): NACE + adres. Sahis adlari kisisel veri, tezde anonim.' % len(firma)),
    ('PVGIS_ozet', 'Yillik uretim, 1 kWp, kayip %14, SARAH3.'),
    ('PVGIS_aylik', '10 derece guneye egik, aylik uretim.'),
    ('PVGIS_TMY_ornek', 'Tipik meteorolojik yil, ilk 168 saat (tamami veri/ham/pvgis).'),
    ('bina_turu_osm', '"yes" = tur girilmemis. OSB\'de %%%.0f, Cigli\'de %%%.0f.' %
     (100 * (osb.bina_turu_osm == 'yes').mean(), 100 * (cig.bina_turu_osm == 'yes').mean())),
], columns=['sayfa/sutun', 'aciklama'])

xp = os.path.join(OUT, 'bina_verileri.xlsx')
with pd.ExcelWriter(xp, engine='openpyxl') as w:
    for ad, df in [('Aciklama', aciklama), ('OSB_binalari', osb), ('Cigli_binalari', cig), ('Kamu_tesisleri', km),
                   ('IAOSB_firmalar', firma), ('PVGIS_ozet', oz), ('PVGIS_aylik', ay), ('PVGIS_TMY_ornek', tmy)]:
        df.to_excel(w, sheet_name=ad, index=False)
        ws = w.sheets[ad]; ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(60, max(10, *(len(str(c.value or '')) for c in col[:200])) + 2)

# ornek dict: her kaynaktan 3 kayit, ham haliyle (geometri kisaltilmis)
def kisalt(f):
    g = f['geometry']; k = g['coordinates']
    return {'type': 'Feature', 'properties': f['properties'],
            'geometry': {'type': g['type'], 'coordinates(ilk 3 nokta)': (k[0][:3] if g['type'] == 'Polygon' else k)}}
ornek = {
    'osm_bina_osb': [kisalt(f) for f in fc(H('osm', 'binalar_ataturk_osb.geojson'))[:3]],
    'kamu_tesisi': [kisalt(f) for f in fc(os.path.join(KOK, 'veri', 'islenmis', 'kamu_okul_hastane_cigli.geojson'))
                    if f['geometry']['type'] == 'Polygon'][:3],
    'excel_satiri_osb': osb.head(3).astype(object).where(osb.head(3).notna(), None).to_dict('records'),
    'excel_satiri_kamu': km.head(3).astype(object).where(km.head(3).notna(), None).to_dict('records'),
}
json.dump(ornek, open(os.path.join(OUT, 'ornek_kayitlar.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2, default=str)
print(xp)
print('OSB %d | Cigli %d | kamu %d | firma %d' % (len(osb), len(cig), len(km), len(firma)))
