# -*- coding: utf-8 -*-
"""Ara rapor icin donem plani ve Ek 2/3/5 gorselleri (2026-11-08).
Girdi: Desktop/CatiGunes_Model_Verisi ve veri/elle/panelsiz_cizimleri.geojson.
  python rapor/ara_rapor_gorseller_2026-11-08/gorseller.py [cati_id]"""
import os, sys, datetime as dt
import pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.lines import Line2D
from PIL import Image

BU = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(BU))
H = os.path.join(os.path.dirname(os.path.dirname(KOK)), 'CatiGunes_Model_Verisi')
GP = os.path.join(H, 'catilar.gpkg')
METIN, IKINCIL, CIZGI, ZEMIN = '#1f1f1d', '#5f5e5a', '#e6e5e0', '#d9d8d2'
MAVI, TURUNCU, YESIL = '#2a78d6', '#e8710a', '#1baf7a'
UTM = 32635


def gantt():
    D = lambda g, a: dt.date(2026, a, g)
    Y = [('Bina envanteri', D(21, 9), D(18, 10), 1), ('SAM çatı çıkarımı', D(16, 10), D(30, 10), 1), ('Elle çizim ve doğrulama', D(22, 10), D(28, 10), 1),
         ('Veri aşaması kapandı', D(30, 10), None, 1), ('Kurulu güç ve üretim', D(2, 11), D(7, 11), 1), ('NPV ve Monte Carlo', D(7, 11), D(8, 11), 1),
         ('Ara rapor teslimi', D(13, 11), None, 2), ('REST API ve web harita', D(16, 11), D(11, 12), 0), ('Tez yazımı', D(23, 11), D(21, 12), 0),
         ('LLM açıklaması', D(30, 11), D(11, 12), 0), ('Final teslimi', D(21, 12), None, 0)]
    b = D(21, 9); g = lambda d: (d - b).days
    fig, ax = plt.subplots(figsize=(6.6, 3.7), dpi=200)
    n = len(Y)
    for i, (ad, s, e, dur) in enumerate(Y):
        y = n - 1 - i
        ax.hlines(y, 0, 91, color=CIZGI, lw=.6, zorder=1)
        if e is None:
            r = {0: '#c5c4b8', 1: '#14a02e', 2: MAVI}[dur]
            ax.scatter(g(s), y, marker='D', s=46, color=r, zorder=4)
            ax.text(g(s) + 2, y, '%d %s' % (s.day, {9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'}[s.month]), va='center', ha='left', fontsize=7.5, color=METIN,
                    fontweight='bold' if dur == 2 else 'normal', zorder=5, bbox=dict(fc='white', ec='none', pad=.8))
        else:
            ge = max(g(e) - g(s), 1.6)
            ax.add_patch(FancyBboxPatch((g(s) + .2, y - .25), ge - .4, .5, boxstyle='round,pad=0,rounding_size=.25', mutation_aspect=1,
                                        fc='#cdebd0' if dur else '#f1f1ec', ec='#14a02e' if dur else '#c5c4b8', lw=1, zorder=3))
    ax.axvline(g(D(13, 11)), color=MAVI, lw=.9, ls=(0, (3, 2)), zorder=2)
    T = [(21, 9, '21 Eyl'), (5, 10, '5 Eki'), (19, 10, '19 Eki'), (2, 11, '2 Kas'), (16, 11, '16 Kas'), (30, 11, '30 Kas'), (14, 12, '14 Ara')]
    ax.set_xticks([g(D(a, c)) for a, c, _ in T]); ax.set_xticklabels([t for _, _, t in T], fontsize=7.5, color=IKINCIL)
    ax.xaxis.tick_top(); ax.tick_params(axis='x', length=0, pad=2)
    ax.set_yticks(range(n)); ax.set_yticklabels([y[0] for y in Y][::-1], fontsize=8, color=METIN)
    ax.get_yticklabels()[n - 1 - 6].set_fontweight('bold')
    ax.tick_params(axis='y', length=0); ax.set_xlim(0, 99); ax.set_ylim(-.7, n - .4)
    ax.grid(axis='x', color=CIZGI, lw=.6); ax.set_axisbelow(True)
    for s_ in ('left', 'right', 'bottom'): ax.spines[s_].set_visible(False)
    ax.spines['top'].set_color(ZEMIN)
    ax.legend(handles=[Patch(fc='#cdebd0', ec='#14a02e', label='Tamamlandı'), Patch(fc='#f1f1ec', ec='#c5c4b8', label='Planlanan')],
              loc='upper center', bbox_to_anchor=(.45, -.01), ncol=2, frameon=False, fontsize=7.5)
    fig.tight_layout(); fig.savefig(os.path.join(BU, 'donem_plani.png'), facecolor='white'); plt.close(fig)


def harita(ax, zemin, sinir):
    sinir.boundary.plot(ax=ax, color=IKINCIL, lw=.7, zorder=1)
    ax.set_axis_off(); ax.set_aspect('equal')
    x0, y0, x1, y1 = sinir.total_bounds
    ax.plot([x1 - 650, x1 - 150], [y0 + 70, y0 + 70], color=METIN, lw=2, solid_capstyle='butt', zorder=6)
    ax.text(x1 - 400, y0 + 100, '500 m', ha='center', va='bottom', fontsize=7.5, color=METIN)


def haritalar():
    c = gpd.read_file(GP, layer='catilar', engine='pyogrio')
    s = gpd.read_file(GP, layer='cati_son', engine='pyogrio')[['cati_id', 'geometry']]
    c = s.merge(c.drop(columns='geometry'), on='cati_id').to_crs(UTM)
    bn = gpd.read_file(GP, layer='sinirlar', engine='pyogrio').to_crs(UTM)
    print(bn[['etiket', 'ad']].to_string())
    osb = c[c.bolge == 'ataturk_osb']
    sin = bn[bn.etiket.astype(str).str.contains('osb', case=False)]
    # Ek 2
    fig, ax = plt.subplots(figsize=(6.6, 5.2), dpi=200); harita(ax, None, sin)
    R = [('sam', 'SAM', MAVI), ('insan', 'İnsan çizimi', TURUNCU), ('ayak_izi', 'Ayak izi', YESIL)]
    h = []
    for k, ad, r in R:
        d = osb[osb.geometri_kaynagi == k]
        d.plot(ax=ax, color=r, edgecolor='white', linewidth=.15, zorder=3)
        h.append(Patch(color=r, label='%s (%d)' % (ad, len(d))))
    fig.legend(handles=h, loc='upper left', bbox_to_anchor=(.02, .97), frameon=False, fontsize=8, title='Son geometri kaynağı', title_fontsize=8, alignment='left')
    fig.tight_layout(pad=.2); fig.savefig(os.path.join(BU, 'ek2_geometri.png'), facecolor='white'); plt.close(fig)
    # Ek 3
    fig, ax = plt.subplots(figsize=(6.6, 5.2), dpi=200); harita(ax, None, sin)
    osb[osb.panel_durumu == 'panel_yok'].plot(ax=ax, color=ZEMIN, edgecolor='white', linewidth=.15, zorder=2)
    Q = [('tam_dolu', 'Tamamen panelli', MAVI), ('kismi_panel_dusuldu', 'Kısmen panelli', TURUNCU)]
    h = [Patch(color=ZEMIN, label='Panelsiz (%d)' % (osb.panel_durumu == 'panel_yok').sum())]
    for k, ad, r in Q:
        d = osb[osb.panel_durumu == k]
        d.plot(ax=ax, color=r, edgecolor='white', linewidth=.15, zorder=3)
        h.append(Patch(color=r, label='%s (%d)' % (ad, len(d))))
    fig.legend(handles=h, loc='upper left', bbox_to_anchor=(.02, .97), frameon=False, fontsize=8, title='Mevcut GES durumu', title_fontsize=8, alignment='left')
    fig.tight_layout(pad=.2); fig.savefig(os.path.join(BU, 'ek3_ges.png'), facecolor='white'); plt.close(fig)
    print(pd.crosstab(c.bolge, c.panel_durumu).to_string())
    return c


def kesit_ax(ax, c, p, cid):
    r = c[c.cati_id == cid].iloc[0]
    f = os.path.join(H, 'cati_kesitleri', r.kesit.replace('\\', '/'))
    im = Image.open(f).convert('RGB')
    a, _, _, e, x0, y0 = [float(v) for v in open(os.path.splitext(f)[0] + '.jgw').read().split()]
    W, Hh = im.size
    ext = (x0 - a / 2, x0 - a / 2 + a * W, y0 - e / 2 + e * Hh, y0 - e / 2)
    ax.imshow(im, extent=ext)
    return ext, a


def ek5(cid=None):
    c = gpd.read_file(GP, layer='catilar', engine='pyogrio')
    s = gpd.read_file(GP, layer='cati_son', engine='pyogrio')[['cati_id', 'geometry']]
    c = s.merge(c.drop(columns='geometry'), on='cati_id')
    p = gpd.read_file(os.path.join(KOK, 'veri', 'elle', 'panelsiz_cizimleri.geojson'), engine='pyogrio')
    if cid is None:
        ids = list(p.cati_id)[:12]
        fig, axs = plt.subplots(3, 4, figsize=(11, 8), dpi=90)
        for ax, i in zip(axs.flat, ids):
            try:
                ext, a = kesit_ax(ax, c, p, i)
                print(i, c[c.cati_id == i].kesit.iloc[0], 'derece' if abs(a) < 1 and abs(ext[0]) < 180 else 'metre', round(ext[0], 5))
                crs = 4326 if abs(ext[0]) < 180 else 3857
                c[c.cati_id == i].to_crs(crs).boundary.plot(ax=ax, color='cyan', lw=1)
                p[p.cati_id == i].to_crs(crs).boundary.plot(ax=ax, color='yellow', lw=1)
                ax.set_xlim(ext[:2]); ax.set_ylim(ext[2:])
            except Exception as x:
                print(i, 'HATA', x)
            ax.set_title(str(i), fontsize=8); ax.set_axis_off()
        fig.tight_layout(); fig.savefig(os.path.join(BU, 'ek5_aday.png')); plt.close(fig); return
    fig, ax = plt.subplots(figsize=(6.6, 4.6), dpi=200)
    ext, a = kesit_ax(ax, c, p, cid)
    crs = 4326 if abs(ext[0]) < 180 else 3857
    c[c.cati_id == cid].to_crs(crs).boundary.plot(ax=ax, color='#ffffff', lw=1.3, zorder=3)
    p[p.cati_id == cid].to_crs(crs).plot(ax=ax, facecolor=(1, .55, .05, .35), edgecolor=TURUNCU, lw=1.3, zorder=4)
    ax.set_xlim(ext[:2]); ax.set_ylim(ext[2:]); ax.set_axis_off()
    ax.legend(handles=[Line2D([], [], color='#ffffff', lw=1.6, label='Son çatı sınırı'), Patch(fc=(1, .55, .05, .35), ec=TURUNCU, label='Panelsiz alan (insan çizimi)')],
              loc='lower left', fontsize=8, facecolor='#333333', edgecolor='none', labelcolor='white', framealpha=.75)
    fig.tight_layout(pad=.2); fig.savefig(os.path.join(BU, 'ek5_panelsiz.png'), facecolor='white'); plt.close(fig)


def adimlar():
    fig, ax = plt.subplots(figsize=(6.72, 2.72), dpi=200); ax.set_xlim(0, 1344); ax.set_ylim(544, 0); ax.axis('off')
    B = [(70, 120, '1. Bina envanteri', 'OSM + Microsoft, 1.085 çatı', 1), (495, 120, '2. Çatı çıkarımı', 'SAM, ayak izi kutu istemi', 1), (919, 120, '3. Doğrulama', 'Elle çizimler, IoU', 1),
         (919, 332, '4. Son geometri', 'GES düşümü, 1,96 km²', 1), (495, 332, '5. Üretim ve NPV', 'PVGIS, Monte Carlo', 1), (70, 332, '6. API ve web harita', 'FastAPI, Leaflet, LLM', 0)]
    for x, y, a, b, d in B:
        ax.add_patch(FancyBboxPatch((x, y), 354, 113, boxstyle='round,pad=0,rounding_size=14', fc='#e1f3e0' if d else 'white', ec='#14a02e' if d else '#c5c4b8', lw=1.2, ls='-' if d else (0, (4, 3))))
        ax.text(x + 177, y + 41, a, ha='center', va='center', fontsize=9.5, fontweight='bold', color=METIN); ax.text(x + 177, y + 76, b, ha='center', va='center', fontsize=8, color=IKINCIL)
    O = dict(arrowstyle='-|>', color='#c5c4b8', lw=1.1, shrinkA=0, shrinkB=0, mutation_scale=9)
    for a, b in (((424, 176), (495, 176)), ((849, 176), (919, 176)), ((1096, 233), (1096, 332)), ((919, 388), (849, 388)), ((495, 388), (424, 388))):
        ax.annotate('', xy=b, xytext=a, arrowprops=O)
    ax.text(70, 50, 'Beş adım tamamlandı, arayüz adımı ara rapordan sonra', fontsize=11, fontweight='bold', color=METIN, va='center')
    ax.add_patch(FancyBboxPatch((70, 482), 32, 17, boxstyle='round,pad=0,rounding_size=4', fc='#e1f3e0', ec='#14a02e', lw=1)); ax.text(112, 490, 'Tamamlandı (8 Kasım)', fontsize=8, color=IKINCIL, va='center')
    ax.add_patch(FancyBboxPatch((430, 482), 32, 17, boxstyle='round,pad=0,rounding_size=4', fc='white', ec='#c5c4b8', lw=1, ls=(0, (3, 2)))); ax.text(472, 490, 'Ara rapordan sonra', fontsize=8, color=IKINCIL, va='center')
    fig.subplots_adjust(0, 0, 1, 1); fig.savefig(os.path.join(BU, 'sekil1_adimlar.png'), facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    gantt(); haritalar(); adimlar()
    ek5(int(sys.argv[1]) if len(sys.argv) > 1 else None)
