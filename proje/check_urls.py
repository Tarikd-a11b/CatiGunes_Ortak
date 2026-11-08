# -*- coding: utf-8 -*-
"""Aday veri seti / API uclarinin gercekten ayakta olup olmadigini test eder."""
import requests, concurrent.futures as cf

H = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 YBS-arastirma/0.1'}

URLS = {
 # --- segmentasyon veri setleri ---
 'INRIA Aerial (proje sayfasi)' : 'https://project.inria.fr/aerialimagelabeling/',
 'INRIA files (Kaggle ayna)'    : 'https://www.kaggle.com/datasets/sagar100rathod/inria-aerial-image-labeling-dataset',
 'WHU Building (Wuhan Univ)'    : 'http://gpcv.whu.edu.cn/data/building_dataset.html',
 'Massachusetts Bldg (Kaggle)'  : 'https://www.kaggle.com/datasets/balraj98/massachusetts-buildings-dataset',
 'SpaceNet'                     : 'https://spacenet.ai/datasets/',
 'RID mediaTUM'                 : 'https://mediatum.ub.tum.de/1655470',
 'RID GitHub'                   : 'https://github.com/TUMFTM/RID',
 # --- panel tespiti ---
 'NREL PV Array (figshare)'     : 'https://figshare.com/articles/dataset/Distributed_Solar_Photovoltaic_Array_Location_and_Extent_Data_Set_for_Remote_Sensing_Object_Identification/3385780',
 'DeepSolar (Stanford)'         : 'https://web.stanford.edu/group/deepsolar/home',
 # --- bina ayak izi ---
 'MS Global ML Footprints'      : 'https://github.com/microsoft/GlobalMLBuildingFootprints',
 'MS Footprints dataset-links'  : 'https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv',
 'Google Open Buildings'        : 'https://sites.research.google/gr/open-buildings/',
 'Overture Maps buildings'      : 'https://docs.overturemaps.org/guides/buildings/',
 # --- gunes / isinim ---
 'PVGIS v5.3 API'               : 'https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=38.42&lon=27.14&peakpower=1&loss=14&outputformat=json',
 'GEPA'                         : 'https://gepa.enerji.gov.tr/MyCalculator/',
 'Global Solar Atlas'           : 'https://globalsolaratlas.info/',
 # --- goruntu kaynagi (D0) ---
 'Izmir Acik Veri'              : 'https://acikveri.bizizmir.com/',
 'Izmir CBS Kent Rehberi'       : 'https://cbs.izmir.bel.tr/',
 'Esri World Imagery (tile)'    : 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/17/48000/74000',
 # --- sosyal ---
 'SEGE (Sanayi Bakanligi)'      : 'https://www.sanayi.gov.tr/merkez-birimi/b94224510b7b/sege',
 'TUIK'                         : 'https://data.tuik.gov.tr/',
 # --- model agirliklari ---
 'SAM ViT-B ckpt'               : 'https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth',
 'MobileSAM repo'               : 'https://github.com/ChaoningZhang/MobileSAM',
 'FastSAM repo'                 : 'https://github.com/CASIA-IVA-Lab/FastSAM',
}

def probe(item):
    ad, url = item
    try:
        r = requests.get(url, headers=H, timeout=40, stream=True, allow_redirects=True)
        size = r.headers.get('Content-Length','?')
        ct = (r.headers.get('Content-Type','?') or '?').split(';')[0]
        r.close()
        return (ad, r.status_code, ct, size)
    except Exception as e:
        return (ad, 'ERR', type(e).__name__, '-')

with cf.ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(probe, URLS.items()))

print(f'{"kaynak":32s} {"kod":>5s}  {"tip":22s} {"boyut":>14s}')
print('-'*80)
for ad, code, ct, size in res:
    try: size = f'{int(size)/1e6:,.1f} MB'
    except: size = str(size)
    print(f'{ad:32s} {str(code):>5s}  {ct:22s} {size:>14s}')
