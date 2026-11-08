# -*- coding: utf-8 -*-
"""Notlandirilmis dogrulama orneginden tabaka agirlikli dogruluk.

Girdi : notebooks/dogrulama/ornek.csv ('not_' sutunu doldurulmus)
        notebooks/cigli_kosu/calisma/cikti/cigli_catilar_ornek20.geojson (tabaka nufuslari)
Cikti : ekrana tablo + notebooks/dogrulama/metrik.csv

Not kategorileri:
  dogru    - cati sinirini kabul edilebilir dogrulukta veriyor
  tasmis   - cati disina belirgin tasma (bahce, yol, komsu cati)
  eksik    - catinin belirgin bir kismi disarida
  kaymis   - maske yanlis yere oturmus (bina degil komsusu/avlu)
  yanlis   - goruntude bina yok ya da tamamen alakasiz yer
  belirsiz - goruntu cozunurlugu/bulanikligi karar vermeye yetmiyor

Agirlik: ornek tabakalari orantili degil (supheli bant bilerek fazla orneklendi),
bu yuzden her cati (tabaka nufusu / tabaka ornegi) ile agirliklandirilir.
"""
import os, csv, io, json, collections

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEK = os.path.join(KOK, 'notebooks', 'dogrulama', 'ornek.csv')
GEOJSON = os.path.join(KOK, 'notebooks', 'cigli_kosu', 'calisma', 'cikti', 'cigli_catilar_ornek20.geojson')
CIKTI = os.path.join(KOK, 'notebooks', 'dogrulama', 'metrik.csv')
IYI = ('dogru',)


def alan_sinifi(a):
    return '<150' if a < 150 else '150-300' if a < 300 else '>=300'


def tabaka_of(cekim, alan, oturtma):
    return (cekim, alan_sinifi(alan), 'supheli' if oturtma < 0.4 else 'normal')


def main():
    nufus = collections.Counter()
    for f in json.load(open(GEOJSON, encoding='utf-8'))['features']:
        p = f['properties']
        nufus[tabaka_of(p['cekim'], p['alan_m2'], p['oturtma_orani'])] += 1
    toplam_nufus = sum(nufus.values())

    satirlar = list(csv.DictReader(io.open(ORNEK, encoding='utf-8-sig'), delimiter=';'))
    eksik_not = [r['sira'] for r in satirlar if not r.get('not_')]
    if eksik_not:
        raise SystemExit('notlandirilmamis %d satir var: %s' % (len(eksik_not), eksik_not[:10]))
    ornek_say = collections.Counter(tabaka_of(r['cekim'], float(r['alan_m2']), float(r['oturtma_orani'])) for r in satirlar)
    for r in satirlar:
        t = tabaka_of(r['cekim'], float(r['alan_m2']), float(r['oturtma_orani']))
        r['_t'] = t
        r['_w'] = nufus[t] / ornek_say[t]

    def oran(kume, pay_kosul):
        a = sum(r['_w'] for r in kume)
        b = sum(r['_w'] for r in kume if pay_kosul(r))
        return (100 * b / a if a else float('nan')), a

    print('\nOrneklem: %d cati / %d (tabaka agirlikli tahminler 540 catinin tamamina genellenir)' % (len(satirlar), toplam_nufus))
    print('\nHAM NOT DAGILIMI')
    d = collections.Counter(r['not_'] for r in satirlar)
    for k, n in d.most_common():
        print('   %-9s %3d  (%%%.1f ham)' % (k, n, 100 * n / len(satirlar)))

    kesin = [r for r in satirlar if r['not_'] != 'belirsiz']
    g_tum, _ = oran(satirlar, lambda r: r['not_'] in IYI)
    g_kesin, _ = oran(kesin, lambda r: r['not_'] in IYI)
    print('\nTABAKA AGIRLIKLI DOGRULUK')
    print('   belirsizler hatali sayilirsa (alt sinir) : %%%.1f' % g_tum)
    print('   belirsizler disarida birakilirsa         : %%%.1f' % g_kesin)

    print('\nOTURTMA BANDINA GORE (modelin kendi supheli bayragi calisiyor mu?)')
    cikti_satir = []
    for band in ('normal', 'supheli'):
        kume = [r for r in satirlar if r['_t'][2] == band]
        if not kume:
            continue
        g, w = oran(kume, lambda r: r['not_'] in IYI)
        bel = 100 * sum(1 for r in kume if r['not_'] == 'belirsiz') / len(kume)
        print('   %-8s n=%3d  agirlikli pay %%%4.1f  dogru %%%.1f  belirsiz %%%.0f'
              % (band, len(kume), 100 * w / toplam_nufus, g, bel))
        cikti_satir.append(dict(kirilim='oturtma', deger=band, n=len(kume), dogru_yuzde=round(g, 1)))

    print('\nALAN SINIFINA GORE')
    for sinif in ('<150', '150-300', '>=300'):
        kume = [r for r in satirlar if r['_t'][1] == sinif]
        if not kume:
            continue
        g, w = oran(kume, lambda r: r['not_'] in IYI)
        print('   %-8s n=%3d  agirlikli pay %%%4.1f  dogru %%%.1f' % (sinif, len(kume), 100 * w / toplam_nufus, g))
        cikti_satir.append(dict(kirilim='alan', deger=sinif, n=len(kume), dogru_yuzde=round(g, 1)))

    print('\nCEKIME GORE')
    for cekim in sorted({r['_t'][0] for r in satirlar}):
        kume = [r for r in satirlar if r['_t'][0] == cekim]
        g, w = oran(kume, lambda r: r['not_'] in IYI)
        print('   %-16s n=%3d  agirlikli pay %%%4.1f  dogru %%%.1f' % (cekim, len(kume), 100 * w / toplam_nufus, g))
        cikti_satir.append(dict(kirilim='cekim', deger=cekim, n=len(kume), dogru_yuzde=round(g, 1)))

    print('\nCATI TIPINE GORE')
    for tip in sorted({r['tip'] for r in satirlar}):
        kume = [r for r in satirlar if r['tip'] == tip]
        g, _ = oran(kume, lambda r: r['not_'] in IYI)
        print('   %-34s n=%3d  dogru %%%.1f' % (tip, len(kume), g))
        cikti_satir.append(dict(kirilim='tip', deger=tip, n=len(kume), dogru_yuzde=round(g, 1)))

    # oturtma_orani esigi gercekten ayirici mi? hatalarin esige gore dagilimi
    print('\nOTURTMA ESIGININ AYIRICILIGI')
    for lo, hi in ((0.0, 0.4), (0.4, 0.7), (0.7, 1.01)):
        kume = [r for r in satirlar if lo <= float(r['oturtma_orani']) < hi]
        if not kume:
            continue
        hata = sum(1 for r in kume if r['not_'] not in IYI and r['not_'] != 'belirsiz')
        bel = sum(1 for r in kume if r['not_'] == 'belirsiz')
        print('   ot %.1f-%.1f  n=%3d  hata %2d  belirsiz %2d  ham dogru %%%.0f'
              % (lo, hi, len(kume), hata, bel, 100 * (len(kume) - hata - bel) / len(kume)))

    with io.open(CIKTI, 'w', newline='', encoding='utf-8-sig') as fh:
        w_ = csv.DictWriter(fh, fieldnames=['kirilim', 'deger', 'n', 'dogru_yuzde'], delimiter=';')
        w_.writeheader(); w_.writerows(cikti_satir)
    print('\n-> %s' % CIKTI)


if __name__ == '__main__':
    main()
