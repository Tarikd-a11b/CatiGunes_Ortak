# -*- coding: utf-8 -*-
"""Izmir Buyuksehir Acik Veri portalindan ihtiyac analizi veri setlerini indirir.

Kaynak: https://acikveri.bizizmir.com (CKAN API)
Lisans: portal genelinde acik veri; her set icin lisans alani ayrica kaydedilir.

Cikti: cache/acikveri/<kisa_ad>.csv  +  cache/acikveri/_envanter.json
"""
import io, json, os, re, sys
import requests

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def yol(*p): return os.path.join(KOK, *p)
HEDEF = yol('cache', 'acikveri')
os.makedirs(HEDEF, exist_ok=True)

UA = {'User-Agent': 'Mozilla/5.0 YBS-bitirme-cati-gunes/0.1 (akademik)'}
API = 'https://acikveri.bizizmir.com/api/3/action/'

# kisa_ad -> portal basligindaki arama ifadesi
ISTENEN = {
    'mahalle_bina_sayisi': 'İlçelere Ait Mahalle Bazlı Bina Sayıları',
    'mahalle_nufus':       'Cinsiyete Göre Mahalle Nüfus Bilgileri',
    'mahalle_su_tuketim':  'Yıllık İlçe ve Mahalle Bazlı Su Tüketim Miktarları',
    'sosyal_yardim':       'İzmir Büyükşehir Belediyesine Sosyal Yardım Başvuruları',
    'askida_fatura':       'Askıda Fatura Rakamları ve Başvurular',
    'lisanssiz_ges':       'Lisanssız Güneş Enerji Santralleri Listesi',
    'ilce_kat_sayisi':     'İlçelere ait Bina Kat Sayıları',
    'okuma_yazma':         'İlçelere Göre Okuma Yazma Oranları',
    'saglik_kurumlari':    'Sağlık Kurumları',
    'muhtarliklar':        'Muhtarlıklar',
}


def ara(baslik):
    r = requests.get(API + 'package_search',
                     params={'q': baslik, 'rows': 10}, headers=UA, timeout=90)
    r.raise_for_status()
    sonuc = r.json()['result']['results']
    # birebir baslik esleşmesini tercih et
    for p in sonuc:
        if p['title'].strip().lower() == baslik.strip().lower():
            return p
    return sonuc[0] if sonuc else None


def kaynak_sec(paket):
    """CSV > XLSX > XLS onceligi."""
    for f in ('CSV', 'XLSX', 'XLS'):
        for r in paket.get('resources', []):
            if (r.get('format') or '').upper() == f and r.get('url'):
                return r
    return None


def main():
    envanter = {}
    for kisa, baslik in ISTENEN.items():
        try:
            p = ara(baslik)
        except Exception as e:
            print('%-22s ARAMA HATASI %s' % (kisa, e)); continue
        if not p:
            print('%-22s bulunamadi' % kisa); continue
        r = kaynak_sec(p)
        if not r:
            print('%-22s indirilebilir kaynak yok (%s)' % (kisa, p['title'][:40])); continue

        uzanti = (r.get('format') or 'csv').lower()
        dosya = os.path.join(HEDEF, '%s.%s' % (kisa, uzanti))
        try:
            resp = requests.get(r['url'], headers=UA, timeout=180)
            resp.raise_for_status()
            open(dosya, 'wb').write(resp.content)
            boyut = len(resp.content)
        except Exception as e:
            print('%-22s INDIRME HATASI %s' % (kisa, e)); continue

        envanter[kisa] = {'baslik': p['title'], 'paket_id': p['id'],
                          'lisans': p.get('license_title'),
                          'guncelleme': p.get('metadata_modified'),
                          'kaynak_url': r['url'], 'format': uzanti,
                          'dosya': os.path.relpath(dosya, KOK), 'boyut': boyut,
                          'notlar': (p.get('notes') or '')[:400]}
        print('%-22s %-7s %8.1f KB  %s' % (kisa, uzanti, boyut / 1024, p['title'][:44]))

    json.dump(envanter, open(os.path.join(HEDEF, '_envanter.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('\n-> %s  (%d set)' % (os.path.relpath(HEDEF, KOK), len(envanter)))


if __name__ == '__main__':
    main()
