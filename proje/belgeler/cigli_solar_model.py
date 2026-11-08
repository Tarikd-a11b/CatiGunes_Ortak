"""
Social Solar: Çiğli Yapay Zekâ Destekli Çatı GES Uygunluk ve Toplumsal Önceliklendirme Modeli
"""

import pandas as pd
import numpy as np

def calculate_solar_potential(roof_area_m2, usable_ratio=0.6, panel_efficiency=0.20):
    """
    Çatı alanından DC kurulu güç ve PVGIS bantlarına göre yıllık üretim tahmini.
    PVGIS İzmir Bandı:
    - Alt Sınır (Düz Çatı 0°): 1375 kWh/kWp
    - Medyan Saha Değeri (İzmir BB Tesisleri): 1453 kWh/kWp
    - Üst Sınır (Güney 30° İdeal Eğim): 1579 kWh/kWp
    """
    usable_area = roof_area_m2 * usable_ratio
    installed_capacity_kw = usable_area * panel_efficiency # 1 m2 ~ 0.2 kWp
    
    annual_yield_min_kwh = installed_capacity_kw * 1375
    annual_yield_median_kwh = installed_capacity_kw * 1453
    annual_yield_max_kwh = installed_capacity_kw * 1579
    
    return {
        "usable_area_m2": round(usable_area, 2),
        "capacity_kw": round(installed_capacity_kw, 2),
        "annual_yield_min_kwh": round(annual_yield_min_kwh, 2),
        "annual_yield_median_kwh": round(annual_yield_median_kwh, 2),
        "annual_yield_max_kwh": round(annual_yield_max_kwh, 2)
    }

def get_reliability_grade(overlap_rate):
    """
    Microsoft MS Footprints vs OSM binalarının örtüşme oranına göre mahalle güvenilirlik kademesi:
    - A (Güvenilir): Örtüşme >= 0.65
    - B (Orta): 0.50 <= Örtüşme < 0.65
    - C (Güvenilmez): Örtüşme < 0.50
    """
    if overlap_rate >= 0.65:
        return "A - Güvenilir"
    elif overlap_rate >= 0.50:
        return "B - Orta"
    else:
        return "C - Güvenilmez"

def calculate_priority_score(building_data, weights=None):
    """
    Çok kriterli karar destek önceliklendirme skoru (0 - 100 arası).
    
    Ağırlıklar (Varsayılan):
    - w_teknik (0.50): Çatı alanı, PVGIS üretim potansiyeli
    - w_sosyal (0.50): Kamu binası statüsü (0.30) + Sosyo-ekonomik ihtiyaç skoru (0.20)
    """
    if weights is None:
        weights = {
            "w_tech_area": 0.20,
            "w_tech_yield": 0.30,
            "w_social_public": 0.30,
            "w_social_need": 0.20
        }
    
    # Teknik Alt Skorlar (Normalize edilmiş)
    # Çatı Alanı Skoru (örnek maks 1000 m2 referans alınarak)
    s_area = min(building_data["roof_area_m2"] / 1000.0, 1.0) * 100
    # Üretim Skoru (Medyan kWh bazında, maks 200.000 kWh referans)
    s_yield = min(building_data["solar_stats"]["annual_yield_median_kwh"] / 200000.0, 1.0) * 100
    
    # Sosyal Alt Skorlar
    s_public = 100.0 if building_data["is_public_building"] else 0.0
    s_need = building_data["socioeconomic_need_score"] # 0-100 arası ölçek
    
    final_score = (
        weights["w_tech_area"] * s_area +
        weights["w_tech_yield"] * s_yield +
        weights["w_social_public"] * s_public +
        weights["w_social_need"] * s_need
    )
    
    return round(final_score, 2)

# --- ÖRNEK ÇİĞLİ VERİSİ İLE SİMÜLASYON ---
if __name__ == "__main__":
    buildings = [
        {
            "name": "Çiğli Aile Danışma Merkezi (Referans Kamu)",
            "roof_area_m2": 210,
            "is_public_building": True,
            "socioeconomic_need_score": 75,
            "neighborhood": "Ataşehir",
            "ms_osm_overlap_rate": 0.89
        },
        {
            "name": "Şirintepe İlkokulu (Kamu Okul)",
            "roof_area_m2": 850,
            "is_public_building": True,
            "socioeconomic_need_score": 90,
            "neighborhood": "Şirintepe",
            "ms_osm_overlap_rate": 0.62
        },
        {
            "name": "EVKA-5 Bitişik Nizam Konut Bloğu",
            "roof_area_m2": 320,
            "is_public_building": False,
            "socioeconomic_need_score": 60,
            "neighborhood": "EVKA-5",
            "ms_osm_overlap_rate": 0.50
        },
        {
            "name": "Kaklıç Kırsal Depo Yapısı",
            "roof_area_m2": 1200,
            "is_public_building": False,
            "socioeconomic_need_score": 30,
            "neighborhood": "Kaklıç",
            "ms_osm_overlap_rate": 0.38
        }
    ]
    
    results = []
    for b in buildings:
        solar_stats = calculate_solar_potential(b["roof_area_m2"])
        b["solar_stats"] = solar_stats
        reliability = get_reliability_grade(b["ms_osm_overlap_rate"])
        score = calculate_priority_score(b)
        
        results.append({
            "Bina Adı": b["name"],
            "Mahalle": b["neighborhood"],
            "Çatı (m²)": b["roof_area_m2"],
            "Kapasite (kWp)": solar_stats["capacity_kw"],
            "Medyan Üretim (kWh/yıl)": solar_stats["annual_yield_median_kwh"],
            "Veri Güvenilirliği": reliability,
            "Nihai Öncelik Skoru": score
        })
        
    df = pd.DataFrame(results).sort_values(by="Nihai Öncelik Skoru", ascending=False)
    print("--- ÇİĞLİ SOLAR MODEL ÖNCELİKLENDİRME TABLOSU ---")
    print(df.to_string(index=False))
