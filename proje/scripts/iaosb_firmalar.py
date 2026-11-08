# -*- coding: utf-8 -*-
"""IAOSB firma rehberi (iaosb.org.tr/iaosb-firmalar) -> firma adi, NACE kodu, adres.
Iletisim (tel/e-posta) BILEREK alinmiyor. Cikti: veri/ham/iaosb/iaosb_firmalar.csv"""
import csv, html, os, re, time, requests
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(KOK, 'veri', 'ham', 'iaosb'); os.makedirs(os.path.join(D, 'firma'), exist_ok=True)
UA = {'User-Agent': 'YBS-bitirme-cati-gunes/2.0 (akademik arastirma)'}
B = 'https://www.iaosb.org.tr'
liste = open(os.path.join(D, 'iaosb-firmalar.html'), 'rb').read().decode('utf-8', 'ignore')
slugs = sorted(set(re.findall(r'href="/firma/([^"]+)"', liste)))
satirlar = []
for i, s in enumerate(slugs):
    p = os.path.join(D, 'firma', s + '.html')
    if not os.path.exists(p):
        r = requests.get(B + '/firma/' + s, headers=UA, timeout=60); r.raise_for_status()
        open(p, 'wb').write(r.content); time.sleep(0.4)
    t = open(p, 'rb').read().decode('utf-8', 'ignore')
    ad = html.unescape(re.search(r'<title>(.*?)</title>', t, re.S).group(1)).rsplit(' - ', 1)[0].strip()
    m = re.search(r'Nace Kodu:\s*([0-9.]+)', t)
    duz = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'(?s)<(script|style).*?</\1>', '', t)))
    adres = ''
    for sat in (x.strip() for x in duz.split('\n')):
        if re.search(r'SOKAK|SOK\.|CAD|BULVAR|NO[:.]', sat, re.I) and 'ORGAN' in sat.upper():
            adres = re.sub(r'\s+', ' ', sat); break
    nace = m.group(1) if m else ''
    satirlar.append({'firma': ad, 'nace': nace, 'nace_bolum': nace[:2], 'adres': adres, 'url': B + '/firma/' + s})
    if i % 100 == 0: print(i, ad, nace, adres)
with open(os.path.join(D, 'iaosb_firmalar.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0]), delimiter=';'); w.writeheader(); w.writerows(satirlar)
print('toplam', len(satirlar), '| NACE dolu', sum(1 for r in satirlar if r['nace']), '| adres dolu', sum(1 for r in satirlar if r['adres']))
