# Üretim ve NPV yöntemi

1.085 çatı için kurulu güç, yıllık üretim ve ekonomik getirinin (NPV/IRR/geri ödeme/LCOE) nasıl hesaplandığının kalıcı özeti. Taban senaryo: **177,7 MWp, 263 GWh/yıl, yatırım 4,40 milyar TL, NPV 4,17 milyar TL** (8 Kasım, OSB dağıtım bedeli düzeltmesi sonrası; 7 Kasım'daki 5,73 geçersiz), tüm 1.021 üretim yapan çatıda NPV > 0. **Monte Carlo: medyan 2,47, P10–P90 0,71–4,47 milyar TL, P(toplam NPV>0) %96,6.** Kod `proje/scripts/uretim_hesabi.py` + `npv_hesabi.py` + `monte_carlo.py` (hepsi `kur.py` zincirinde), çıktı `model_verisi/uretim/` + `model_verisi/ekonomi/`.

## Üretim zinciri (ekip arkadaşının `tahmin_modeli.ipynb`'i temel)
1. **Alan:** `catilar.gpkg` katman `uygun_alan` (son çatı geometrisi, mevcut GES düşülmüş). Arkadaşın defteri SAM maskesini kullanıyordu → değiştirildi.
2. **Net alan:** poligon kenar boşluğu kadar içeri tamponlanır (kamu 1,2 m, sanayi/sanayi_dışı 2,0 m).
3. **Modül alanı** = net × engel payı (0,70–0,80) × GCR / cos β. GCR: 21 Aralık 10:00'da sıra gölgesi düşmeyecek aralık, panel boyu 1,7 m → 10° %72,5, 15° %63,4.
4. **kWp** = modül alanı × 0,20 kWp/m².
5. **kWh** = kWp × PVGIS PVcalc E_y (bölgenin kendi noktası, free-standing, kayıp %14): OSB 10° 1.477 / 15° 1.516; Çiğli 10° 1.514 / 15° 1.555 kWh/kWp.
6. Bant = {10°,15°} × {0,70, 0,80} min/max; **merkez = 10° + 0,75**.

Çapraz kontrol: defterin kendi ışınım motoru (Duffie-Beckman izotropik + albedo + sıcaklık + PR 0,80) aynı TMY ile PVGIS'ten %1,9–2,6 düşük. Yıllar arası sapma SD_y ≈ 30 kWh/kWp (±%2) → Monte Carlo girdisi. Sentetik açık-gök yolu kaldırıldı (dosya yoksa betik durur).

**Bant neden ~%25:** engel payı (~%14) + eğim (~%12, 15°'de daha az panel ama panel başı +%2,6). Eğim belirsizlik değil tasarım kararı → öneri: 10° sabit, bant yalnız engel payından (±%7).

## PVGIS verisi (veri/ham/pvgis, 14–16 Eki; 15° 7 Kas)
PVcalc yıllık/aylık ortalama 2005–2023 (asıl girdi) · seriescalc saatlik 2020–2023 (35.064 saat, eksiksiz; yedekte) · TMY saatlik 8.760 · MRcalc aylık 228 ay · ufuk. SARAH3 (Meteosat 15–30 dk → saatlik), ~5 km hücre (OSB tek hücre), sıcaklık/rüzgâr ERA5, uzak ufuk gölgesi dahil, bina-bina gölgesi hariç.

## NPV (ara rapor 4.7 formülü), REEL
NPV = −C₀·P + Σ₁²⁵ [E(1−d)^(t−1)·c − O&M − evirici(t=13)] / (1+r)^t, sabit Nisan 2026 TL.
- **%100 öz tüketim**, kaçınılan bedel, vergi hariç. Atatürk OSB katılımcısı ulusal dağıtım bedeli ödemez → EPDK 04.04.2026 enerji + OSB dağıtım bedeli (EPDK 18.12.2025 tarihli 14049-111, RG 28.12.2025/33121; TT-OG 43,7328, TT-AG 46,6483 kr/kWh, sanayi ve sanayi harici aynı; görsel `veri/ham/tarife/epdk_14049-111_izmir_ataturk_osb_2026.png`): OSB sanayi 334,70, OSB sanayi dışı 369,94; OSB dışı Çiğli kamu OG çift terim 493,04 kr/kWh. enerjigunlugu'ndaki 0,3424 değeri resmî kararla çelişiyor, kullanılmadı.
- **Yasal kurulum sınırı yok** (sözleşme gücü yok).
- Taban: kur 50,07 (TCMB 06.11.2026) · capex kademeli <100 kWp 550 / 100–1.000 500 / ≥1.000 450 $/kWp · O&M %1,5/yıl · evirici %8 yıl 13 · bozunma %0,5 · 25 yıl · reel iskonto %8 · reel fiyat artışı 0. Aralıklar `ekonomi/npv_varsayimlar.csv`.
- Kaynak zayıflığı: capex = TR kurulumcu siteleri (400–850 $/kWp, tutarsız; IRENA 2024 dünya ort. 691 $/kW). O&M/iskonto/bozunma = varsayım. Raporda "gösterge" denmeli.

## Sonuçlar
| | Çatı | MWp | Yatırım | NPV | Medyan IRR | Geri ödeme |
|---|---|---|---|---|---|---|
| OSB sanayi | 933 | 161,5 | 4,00 milyar | 3,42 milyar | %15,3 | 7 yıl |
| Kamu (80) | 80 | 15,2 | 374 M | 718 M | ~%25 | 4 yıl |
| Toplam | 1.021 | 177,7 | 4,40 milyar | 4,17 milyar | %15,3 | 4–7 yıl |

LCOE medyan ~2,16 TL/kWh (şebekenin ~yarısı). Kamu üretiminin %64'ü İKÇÜ. Şüpheli SAM çatıları üretimin %5,1'i.

**AS3:** toplam NPV sırası ≈ üretim sırası (Spearman 0,989, ilk 50'de 43 ortak; sanayi içinde 1,000). NPV/yatırım sırasında ilk 50'nin tamamı Çiğli kamu (tarife grubu etkisi). Kademe eşiklerinde (100/1.000 kWp) sıçrama.

## Monte Carlo (2026-11-08, `scripts/monte_carlo.py`, `ekonomi/mc_*.csv`)
10.000 tur, tohum 20261108, üçgen dağılım. Ortak: kur, tarife, capex, O&M, evirici, bozunma, iskonto, fiyat artışı, ömür. Çatı başına: engel 0,70–0,85, yön/montaj 0,92–1, öz tüketim 0,714–1, alan hatası (test setinden gözlenen insan/SAM ve insan/ayak izi oranı).

| Kurgu (milyar TL) | P10 | P50 | P90 | P(NPV>0) |
|---|---|---|---|---|
| Tam | 0,71 | 2,47 | 4,47 | %96,6 |
| %100 öz tüketim | 1,50 | 3,38 | 5,52 | %99,2 |
| Yalnız ortak | 1,60 | 3,50 | 5,68 | %99,4 |

Çatı başına P(NPV>0) ort.: sanayi %85, kamu ≥%99,8. Tornado sırası: iskonto (1,96–6,82), capex (1,58–5,16), tarife (2,77–6,15), fiyat artışı (2,83–5,88), öz tüketim (1,48–4,17). Kararlılık (tam kurgu): NPV ilk 50 %82, sanayi ilk 50 %77, kamu ilk 20 %96; NPV/yatırım sanayi ilk 50 %31 (kararsız). Yalnız ortak girdiyle %96–100 (yapay kararlılık). Bütçe 500 M: NPV'ye göre 13 çatı 687 M; NPV/yatırıma göre 85 çatı (80 kamu) 851 M.

Duyarlılık: çatı montajı (1.420) 253 GWh → NPV 3,80; öz tüketim %90 3,23, %80 2,29, %71,4 1,48 milyar TL. İKÇÜ'süz kamu NPV 258 M (ile 718 M), kamu üretimi 8,4 GWh (ile 23,0).

## Açık konular
**Kapananlar (08.11):** OSB dağıtım tarifesi; engel/kenar çift düşümü (Ni vd. 2024 engel %14,9, 0,5 m kenar ayrı düşülüyor → kanıt yok); öz tüketim ve çatı tipi MC girdisi oldu. **Duruyor:** capex'in resmî/Türkiye'ye özgü kaynağı yok (gösterge, sınırlılıkta yazılı); capex kademe sıçraması. **Kapandı (08.11, kullanıcı):** son EPDK tarifesi Nisan 2026 (hazırlık 2 Nisan, geçerlilik 4 Nisan), İKÇÜ kapsamı, firma onayı, Monte Carlo.

**Denetim (08.11):** PVGIS ham JSON, geometri yeniden tamponlama, kWp, tarife toplamları, NPV (betikten bağımsız), TCMB kuru, 15 DOI (Crossref), Kutlu 2022 kenar boşlukları tuttu. Rapor dili: GCR = panelin yatay izdüşümü / sıra aralığı = 0,7247, raporda "sıra yerleşim oranı (yaklaşık 0,74)"; panel/zemin oranı 0,736 ayrı şeydir. Kutlu'da 2 m "commercial" için; sanayiye uyarlama bizim. 0,20 kWp/m² ve engel 0,75 varsayım. IRENA (dünya geneli şebeke ölçeği) rapordan çıktı. Çatı bazında olmayanlar: engel payı, PVGIS (2 nokta), yön/eğim (güney 10°), %100 öz tüketim.
