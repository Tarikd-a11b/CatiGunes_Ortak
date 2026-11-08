# -*- coding: utf-8 -*-
"""Son hali (Desktop/CatiGunes_Model_Verisi) ILK INDIRILEN ham veriden tek komutla kurar (2026-10-16).
Kalici olan yalniz iki hal var: veri/ham (indirilen ana veri) + veri/elle (insan kararlari) -> Model_Verisi.
Ara klasorler (veri/islenmis, veri/inceleme) zincir sirasinda olusur, sonunda silinir.
  python scripts/kur.py"""
import os, shutil, subprocess, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZINCIR = ['kamu_okul_hastane.py', 'cati_listesi.py', 'cati_kesit.py', 'model_verisi.py', 'cati_geometri.py', 'uretim_hesabi.py', 'npv_hesabi.py', 'monte_carlo.py', 'veri_dogrulama.py', 'kamu_klasoru.py']
os.makedirs(os.path.join(KOK, 'veri', 'inceleme'), exist_ok=True)
for b in ZINCIR:
    print('==>', b, flush=True)
    r = subprocess.run([sys.executable, os.path.join(KOK, 'scripts', b)], cwd=KOK)
    if r.returncode: sys.exit('HATA: %s (kod %d) - ara klasorler incelemek icin birakildi' % (b, r.returncode))
for d in ('islenmis', 'inceleme'):
    shutil.rmtree(os.path.join(KOK, 'veri', d), ignore_errors=True)
print('tamam -> Desktop/CatiGunes_Model_Verisi (ara klasorler silindi)')
