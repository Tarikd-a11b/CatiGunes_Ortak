"""LabelMe insan cizimleri <-> SAM maskesi / ayak izi IoU.

Girdi : Desktop/Toplantı/Cizim_Paketi/<set>/cizimler*/ (LabelMe 7.9 masaustu: linestrip, etiket numara)
        veri/ham/sam/birlesik_2026-10-22/ (sam_sonuc_tam.csv + sam_maskeler/)
Cikti : <set>/cizimler_donusturulmus/ (poligon + 'cati'; orijinallere dokunulmaz)
        veri/elle/test_referans/iou_sonuc.csv, iou_insan_insan.csv
Koşu  : python scripts/cizim_iou.py [arkadas_zip]   (zip verilirse 1. cizimler cizimler/ yuvasina kopyalanir)
"""
import ast, glob, json, os, shutil, sys, zipfile

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASA = os.path.join(os.path.expanduser('~'), 'Desktop')
PAKET = os.path.join(MASA, 'Toplantı', 'Cizim_Paketi')
SAM = os.path.join(KOK, 'veri', 'ham', 'sam', 'birlesik_2026-10-22')
CIK = os.path.join(KOK, 'veri', 'elle', 'test_referans')
# set -> (orijinal cizim klasoru, donusturulmus klasor, cizen)
SETLER = {
    '1_test_referans': ('cizimler', 'cizimler_donusturulmus', 'arkadas'),
    '2_kamu_ek': ('goruntuler', 'cizimler_donusturulmus', 'bilal'),
    '3_supheli_ek': ('goruntuler', 'cizimler_donusturulmus', 'bilal'),
    '5_ikinci_cizim': ('goruntuler', 'cizimler_donusturulmus', 'bilal'),
    '6_eksik_test': ('goruntuler', 'cizimler_donusturulmus', 'bilal'),  # arkadasin cizmedigi test catilari
}
RAPOR_SETI = {'6_eksik_test': '1_test_referans'}
# cizen SAM maskesini gordu -> bagimsiz degil, test puanindan cikar
BAGIMSIZ_DEGIL = {'c0286'}
# kayitli ayak izi/kutu baska yeri gosteriyor -> insan baska bina cizdi; SAM puanina girmez, veri duzeltmesi bekler
# kutu birden cok yapiyi kapsiyor, hedef bina belirlenemiyor -> SAM puanina girmez, veride isaretlenir
BINA_BELIRSIZ = {'c0485'}
AYAKIZI_HATALI = {'c0833', 'c1076', 'c1141', 'c0828', 'c1068', 'c0465', 'c1080', 'c1449'}
# kutu disina >%15 tasan cizimler (SAM'den bagimsiz olcut) burada yeniden cizildi; varsa eskisinin yerine gecer
YENIDEN = os.path.join(PAKET, '7_yeniden_cizim')


def zipten_al(zp):
    hedef = os.path.join(PAKET, '1_test_referans', 'cizimler')
    with zipfile.ZipFile(zp) as z:
        for ad in z.namelist():
            if ad.endswith('.json') and '/goruntuler/' in ad:
                yol = os.path.join(hedef, os.path.basename(ad))
                if not os.path.exists(yol):
                    with z.open(ad) as k, open(yol, 'wb') as h:
                        shutil.copyfileobj(k, h)


def donustur(kaynak, hedef):
    """linestrip/polygon -> tek etiketli polygon; yalniz hedefe yazar."""
    os.makedirs(hedef, exist_ok=True)
    for f in glob.glob(os.path.join(kaynak, 'c*.json')):
        yol = os.path.join(hedef, os.path.basename(f))
        if os.path.exists(yol) and os.path.getmtime(yol) >= os.path.getmtime(f):
            continue  # yeniden cizilen dosya tekrar donusturulur
        j = json.load(open(f, encoding='utf-8'))
        sekiller = []
        for s in j['shapes']:
            p = s['points']
            if s['shape_type'] in ('linestrip', 'polygon') and len(p) >= 3:
                if s['shape_type'] == 'linestrip' and np.hypot(*np.subtract(p[0], p[-1])) <= 5:
                    p = p[:-1]
                sekiller.append(dict(label='cati', points=p, group_id=None, description='',
                                     shape_type='polygon', flags={}, mask=None))
        j.update(shapes=sekiller, imageData=None,
                 imagePath='../goruntuler/' + os.path.basename(f)[:-5] + '.jpg')
        json.dump(j, open(yol, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def maske(sekiller, boy):
    im = Image.new('L', boy, 0)
    d = ImageDraw.Draw(im)
    for p in sekiller:
        d.polygon([tuple(x) for x in p], fill=1)
    return np.array(im, bool)


def cizim_oku(f):
    j = json.load(open(f, encoding='utf-8'))
    return [s['points'] for s in j['shapes']], (j['imageWidth'], j['imageHeight'])


def iou(a, b):
    b_ = a | b
    return (a & b).sum() / b_.sum() if b_.any() else np.nan


def main():
    if len(sys.argv) > 1:
        zipten_al(sys.argv[1])
    s = pd.read_csv(os.path.join(SAM, 'sam_sonuc_tam.csv'))
    s['dosya'] = s.maske_dosyasi.str.split('/').str[-1].str[:-4]
    s = s.set_index('dosya')
    satir, ciz = [], {}
    yd = os.path.join(YENIDEN, 'cizimler_donusturulmus')
    if os.path.isdir(YENIDEN):
        donustur(os.path.join(YENIDEN, 'goruntuler'), yd)
    for ad, (org, don, kim) in SETLER.items():
        donustur(os.path.join(PAKET, ad, org), os.path.join(PAKET, ad, don))
        for f in sorted(glob.glob(os.path.join(PAKET, ad, don, 'c*.json'))):
            d = os.path.basename(f)[:-5]
            yf = os.path.join(yd, d + '.json')
            if os.path.exists(yf):   # 5_ikinci de: test'e 1. cizim olarak girdiginde yeniden cizim gecerli
                f = yf
            sek, boy = cizim_oku(f)
            if not sek:
                continue
            h = maske(sek, boy)
            # insan-insan uyumu iki bagimsiz kisinin ozgun cizimleriyle olculur (yeniden cizim degil)
            ciz[(ad, d)] = maske(*cizim_oku(os.path.join(PAKET, ad, don, d + '.json'))) if f == yf else h
            kim_ = kim
            if ad == '5_ikinci_cizim':
                if ('1_test_referans', d) in ciz:
                    continue
                kim_ = 'bilal'  # 1. cizim yoksa 2. cizim test referansi sayilir
            rs = '1_test_referans' if ad == '5_ikinci_cizim' else RAPOR_SETI.get(ad, ad)
            if d in BAGIMSIZ_DEGIL:
                rs += '_bagimsiz_degil'
            elif d in BINA_BELIRSIZ:
                rs += '_bina_belirsiz'
            elif d in AYAKIZI_HATALI:
                rs += '_ayakizi_hatali'
            elif f == yf:
                # yeniden cizimde hala kutu disina >%15 tasiyorsa bina kayittan buyuk: SAM'e eksik kutu verilmis
                x0, y0, x1, y1 = ast.literal_eval(s.loc[d].kutu_px)
                k = np.zeros_like(h)
                k[max(0, int(y0 - 10)):int(y1 + 10), max(0, int(x0 - 10)):int(x1 + 10)] = True
                if (h & ~k).sum() / h.sum() > .15:
                    rs += '_ayakizi_eksik'
            r = s.loc[d]
            m = np.array(Image.open(os.path.join(SAM, r.maske_dosyasi)).convert('L').resize(boy, Image.NEAREST)) > 0
            a = maske([ast.literal_eval(r.poligon_px)], boy)
            satir.append(dict(set=rs, cizen=kim_, dosya=d, cati_id=r.cati_id, bolge=r.bolge, tur=r.tur,
                              alan_sinifi=r.alan_sinifi, supheli=r.supheli,
                              iou_sam_insan=iou(m, h), iou_ayakizi_insan=iou(a, h),
                              insan_px=int(h.sum()), sam_px=int(m.sum())))
    t = pd.DataFrame(satir)
    os.makedirs(CIK, exist_ok=True)
    t.to_csv(os.path.join(CIK, 'iou_sonuc.csv'), index=False, encoding='utf-8-sig')
    x = t[t.set.str.contains('ayakizi|belirsiz')].copy()
    x['sorun'] = x.set.str.extract(r'(ayakizi_eksik|ayakizi_hatali|bina_belirsiz)')
    x[['dosya', 'cati_id', 'sorun', 'set', 'tur', 'iou_ayakizi_insan']].sort_values(['sorun', 'dosya']).round(3).to_csv(
        os.path.join(CIK, 'ayakizi_duzeltme_listesi.csv'), index=False, encoding='utf-8-sig')
    ii = [dict(dosya=d, iou_insan_insan=iou(ciz[('1_test_referans', d)], h))
          for (ad, d), h in ciz.items() if ad == '5_ikinci_cizim' and ('1_test_referans', d) in ciz]
    ii = pd.DataFrame(ii)
    ii.to_csv(os.path.join(CIK, 'iou_insan_insan.csv'), index=False, encoding='utf-8-sig')

    def ozet(g):
        return pd.Series(dict(n=len(g), sam_medyan=g.iou_sam_insan.median(), sam_ort=g.iou_sam_insan.mean(),
                              sam_ge070=(g.iou_sam_insan >= .7).mean(),
                              ayakizi_medyan=g.iou_ayakizi_insan.median()))
    pd.set_option('display.width', 200)
    print(t.groupby('set').apply(ozet, include_groups=False).round(3))
    print(t.groupby(['tur']).apply(ozet, include_groups=False).round(3))
    print(t.groupby(['supheli']).apply(ozet, include_groups=False).round(3))
    tr = t[t.set == '1_test_referans']
    print('test_referans (yansiz orneklem):\n', ozet(tr).round(3).to_string())
    print('insan-insan:', len(ii), 'cift, medyan', round(ii.iou_insan_insan.median(), 3),
          'ort', round(ii.iou_insan_insan.mean(), 3), 'min', round(ii.iou_insan_insan.min(), 3))
    print('en dusuk SAM:\n', t.nsmallest(10, 'iou_sam_insan')[['set', 'dosya', 'tur', 'supheli',
                                                                 'iou_sam_insan', 'iou_ayakizi_insan']].round(3))


if __name__ == '__main__':
    main()
