# -*- coding: utf-8 -*-
"""TUIK SOSYOEKONOMIK SEVIYE (SES) 2023 - il/ilce tablosunu isle.

NEDEN: SEGE 2022 Cigli ile Karsiyaka'yi AYIRAMIYOR (ikisi de kademe 1, skor 2,046
ve 2,222). SES 2023 ise idari kayitlardan, 26 milyondan fazla hanenin TAMAMI icin
hesaplanmis ve bilesenlerinden biri dogrudan HANE GELIRI. Mahalle kirilimi
yayimlanmiyor ama ilce kirilimi var; pilot ilce secimini resmi ve guncel bir
kaynaga dayandirmak icin kullanilir.

Kaynak: TUIK Haber Bulteni 57942, 'Sosyoekonomik Seviye, 2023' (18 Agustos 2025).
        Referans donemi 2023 (2022-2024 verileriyle). Sonraki bulten: Agustos 2028.
Girdi : cache/tuik_ses2023_il_ilce.xls   (bultenin 'Tablolar' bolumundeki dosya)
Cikti : cache/ses2023_ilce.csv           tum ilceler, Turkiye ve il sirasiyla
        ekrana Izmir tablosu + Cigli/Karsiyaka karsilastirmasi
"""
import csv, io, json, os, sys, unicodedata
import numpy as np
import xlrd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)

ODAK = ['ÇİĞLİ', 'KARŞIYAKA']
IL = 'İzmir'


def sadelestir(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.translate(str.maketrans('ıİşŞğĞçÇöÖüÜ', 'iIsSgGcCoOuU')).lower()
    return ''.join(ch for ch in s if ch.isalnum())


# ---------------------------------------------------------------- oku
sh = xlrd.open_workbook(yol('cache/tuik_ses2023_il_ilce.xls')).sheet_by_index(0)
SUT = ['il', 'ilce', 'ses', 'toplam', 'ust_A', 'ust_alti_B', 'orta_C', 'alt_D', 'en_alt_E']

satir, turkiye, iller = [], None, {}
for i in range(5, sh.nrows):
    il = str(sh.cell_value(i, 0)).strip()
    ilce = str(sh.cell_value(i, 1)).strip()
    if not il:
        continue
    try:
        d = dict(il=il, ilce=ilce,
                 **{SUT[j]: float(sh.cell_value(i, j)) for j in range(2, 9)})
    except (ValueError, TypeError):
        continue
    if il.startswith('Toplam'):
        turkiye = d
    elif not ilce:
        iller[il] = d                 # il toplami (ilce sutunu bos)
    else:
        satir.append(d)

print('Turkiye ortalama SES skoru : %.2f' % turkiye['ses'])
print('il toplami satiri          : %d' % len(iller))
print('ilce satiri                : %d' % len(satir))

# ---------------------------------------------------------------- siralamalar
satir.sort(key=lambda d: -d['ses'])
for n, d in enumerate(satir, 1):
    d['tr_sira'] = n
for il in {d['il'] for d in satir}:
    g = [d for d in satir if d['il'] == il]
    for n, d in enumerate(sorted(g, key=lambda x: -x['ses']), 1):
        d['il_sira'] = n

izmir = sorted([d for d in satir if d['il'] == IL], key=lambda d: -d['ses'])
print('\n%s: %d ilce, il ortalamasi SES %.2f (Turkiye %.2f)'
      % (IL, len(izmir), iller[IL]['ses'], turkiye['ses']))

print('\n%-4s %-16s %8s %7s %7s %8s %8s %8s'
      % ('sira', 'ilce', 'SES', 'TR sira', 'ust %', 'orta %', 'alt %', 'en alt %'))
for d in izmir:
    yildiz = ' <<<' if d['ilce'].upper() in [x.upper() for x in ODAK] else ''
    print('%-4d %-16s %8.2f %7d %7.1f %8.1f %8.1f %8.1f%s'
          % (d['il_sira'], d['ilce'][:16], d['ses'], d['tr_sira'],
             d['ust_A'], d['orta_C'], d['alt_D'], d['en_alt_E'], yildiz))

# ---------------------------------------------------------------- odak ilceler
print('\n' + '=' * 74)
print('  ODAK: %s' % ' vs '.join(ODAK))
print('=' * 74)
o = {}
for ad in ODAK:
    d = next((x for x in satir if x['il'] == IL and sadelestir(x['ilce']) == sadelestir(ad)),
             None)
    if not d:
        print('  %s BULUNAMADI' % ad); continue
    o[ad] = d
    print('  %-11s SES %.2f | Turkiye %d./%d | %s %d./%d'
          % (ad, d['ses'], d['tr_sira'], len(satir), IL, d['il_sira'], len(izmir)))
    print('              ust[A+/A] %%%.1f · ust-alti[B] %%%.1f · orta[C] %%%.1f '
          '· alt[D] %%%.1f · en alt[E] %%%.1f'
          % (d['ust_A'], d['ust_alti_B'], d['orta_C'], d['alt_D'], d['en_alt_E']))

if len(o) == 2:
    a, b = o[ODAK[0]], o[ODAK[1]]
    print('\n  FARK (%s - %s)' % (ODAK[1], ODAK[0]))
    print('    SES skoru       : %+.2f puan' % (b['ses'] - a['ses']))
    print('    ust seviye payi : %+.1f puan  (%%%.1f -> %%%.1f)'
          % (b['ust_A'] - a['ust_A'], a['ust_A'], b['ust_A']))
    print('    en alt pay      : %+.1f puan  (%%%.1f -> %%%.1f)'
          % (b['en_alt_E'] - a['en_alt_E'], a['en_alt_E'], b['en_alt_E']))
    yay = max(d['ses'] for d in izmir) - min(d['ses'] for d in izmir)
    print('    Izmir ici yayilim %.2f puan; iki ilce arasindaki fark bunun %%%.0f\'i'
          % (yay, 100 * abs(b['ses'] - a['ses']) / yay))

# ---------------------------------------------------------------- SEGE ile
p = yol('cache/izka/sege_ilce.json')
if os.path.exists(p):
    sege = {sadelestir(r['ilce']): r for r in json.load(open(p, encoding='utf-8'))}
    print('\n  SEGE 2022 ILE KARSILASTIRMA')
    print('  %-11s %-26s %s' % ('ilce', 'SEGE 2022', 'SES 2023'))
    for ad in ODAK:
        s = sege.get(sadelestir(ad)); d = o.get(ad)
        if s and d:
            print('  %-11s TR %-4s skor %-7s kademe %s   SES %.2f, TR %d.'
                  % (ad, s['s2022_tr'], s['s2022_skor'], s['s2022_kademe'],
                     d['ses'], d['tr_sira']))
    print('  -> SEGE ikisini de kademe 1 sayiyor; SES ise ayirt ediyor.')

# ---------------------------------------------------------------- cikti
with io.open(yol('cache/ses2023_ilce.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=SUT + ['tr_sira', 'il_sira'], delimiter=';')
    w.writeheader()
    for d in sorted(satir, key=lambda x: (x['il'], -x['ses'])):
        w.writerow({k: (round(v, 3) if isinstance(v, float) else v)
                    for k, v in d.items() if k in SUT + ['tr_sira', 'il_sira']})
print('\n-> cache/ses2023_ilce.csv  (%d ilce)' % len(satir))
