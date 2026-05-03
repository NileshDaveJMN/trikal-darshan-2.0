import swisseph as swe
from datetime import datetime, timedelta
from engines.utils import P_HINDI_FULL, P_HINDI_SHORT, get_formatted_degree
from engines.dosh_engine import check_manglik, check_kaalsarp
from engines.ashtakvarg_engine import get_ashtakvarg_data

D_HINDI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}

def get_vimshottari_dasha(moon_degree, birth_date):
    dasha_order = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    dasha_years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
    nakshatra_span = 360 / 27 
    total_nakshatras = moon_degree / nakshatra_span
    nakshatra_index = int(total_nakshatras)
    rem_degree = (total_nakshatras - nakshatra_index) * nakshatra_span
    start_dasha_idx = nakshatra_index % 9
    consumed_ratio = rem_degree / nakshatra_span
    consumed_years = dasha_years[start_dasha_idx] * consumed_ratio
    current_md_start = birth_date - timedelta(days=int(consumed_years * 365.2425))
    
    dasha_list, idx = [], start_dasha_idx
    today = datetime.now()
    curr_dasha_info = {"md": "", "ad": ""}
    
    for i in range(9):
        md_planet = dasha_order[idx]
        md_years = dasha_years[idx]
        md_end = current_md_start + timedelta(days=int(md_years * 365.2425))
        is_curr_md = current_md_start <= today <= md_end
        
        antardasha_list = []
        ad_start, ad_idx = current_md_start, idx 
        
        for j in range(9):
            ad_planet = dasha_order[ad_idx]
            ad_years = (md_years * dasha_years[ad_idx]) / 120.0
            ad_end = ad_start + timedelta(days=int(ad_years * 365.2425))
            is_curr_ad = ad_start <= today <= ad_end
            
            if is_curr_ad:
                curr_dasha_info["md"], curr_dasha_info["ad"] = D_HINDI.get(md_planet, md_planet), D_HINDI.get(ad_planet, ad_planet)
            
            antardasha_list.append({
                "planet": D_HINDI.get(ad_planet, ad_planet), "start": ad_start.strftime('%d-%m-%Y'),
                "end": ad_end.strftime('%d-%m-%Y'), "is_current": is_curr_ad
            })
            ad_start = ad_end
            ad_idx = (ad_idx + 1) % 9
        
        dasha_list.append({
            "planet": D_HINDI.get(md_planet, md_planet), "start": current_md_start.strftime('%d-%m-%Y'),
            "end": md_end.strftime('%d-%m-%Y'), "antardashas": antardasha_list, "is_current": is_curr_md
        })
        current_md_start = md_end
        idx = (idx + 1) % 9
        
    return dasha_list, curr_dasha_info

def get_kundali_data(name, gender, dd, mm, yyyy, hh, m_m, ss, city, lat, lon, need_ai=False, selected_topics=None, custom_question=""):
    try:
        dt_ist = datetime(yyyy, mm, dd, hh, m_m, ss)
        dt_utc = dt_ist - timedelta(hours=5, minutes=30)
        jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd_ut)

        cusps, ascmc = swe.houses(jd_ut, lat, lon, b'W')
        asc_sid = (ascmc[0] - ayan) % 360
        l_idx = int(asc_sid / 30)

        p_pos, p_degrees_raw, planet_details = {}, {}, []
        planets_to_calc = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}

        for p_n, p_id in planets_to_calc.items():
            res_p, _ = swe.calc_ut(jd_ut, p_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
            p_pos[p_n] = int(res_p[0] / 30)
            p_degrees_raw[p_n] = res_p[0]
            info = get_formatted_degree(res_p[0])
            planet_details.append({"name": P_HINDI_FULL.get(p_n, p_n), "rashi": info["rashi"], "degree": info["degree"]})

        res_r, _ = swe.calc_ut(jd_ut, swe.TRUE_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        p_pos["Rahu"], p_pos["Ketu"] = int(res_r[0] / 30), int((res_r[0] + 180) % 360 / 30)
        p_degrees_raw["Rahu"], p_degrees_raw["Ketu"] = res_r[0], (res_r[0] + 180) % 360
        r_info, k_info = get_formatted_degree(res_r[0]), get_formatted_degree((res_r[0] + 180) % 360)
        planet_details.extend([{"name": "राहु", "rashi": r_info["rashi"], "degree": r_info["degree"]}, {"name": "केतु", "rashi": k_info["rashi"], "degree": k_info["degree"]}])

        sav_data = get_ashtakvarg_data(p_pos, l_idx)
        dasha_data, curr_dasha_info = get_vimshottari_dasha(p_degrees_raw["Moon"], dt_ist)
        is_manglik, manglik_text = check_manglik(p_pos, l_idx)
        kaalsarp_text = check_kaalsarp(p_pos, l_idx)

        # AI Call Logic
        predictions_data, current_dasha_text = None, None
        if need_ai:
            from engines.prediction_engine import get_bhav_phal
            predictions_data, current_dasha_text = get_bhav_phal(p_degrees_raw, l_idx, sav_data, curr_dasha_info, selected_topics, custom_question)

        z_names = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
        houses = []
        for i in range(1, 13):
            curr = (l_idx + i - 1) % 12
            p_short = [P_HINDI_SHORT.get(k, k) for k, v in p_pos.items() if v == curr]
            p_full_hindi = [P_HINDI_FULL.get(k, k) for k, v in p_pos.items() if v == curr]
            houses.append({"num": i, "r_num": curr + 1, "rashi": z_names[curr], "planets": " ".join(p_short), "planets_full": ", ".join(p_full_hindi) if p_full_hindi else "---"})

        # 🌟 पंचांग लॉजिक (सूर्य और चंद्र की डिग्री के आधार पर) 🌟
        moon_deg = p_degrees_raw["Moon"]
        sun_deg = p_degrees_raw["Sun"]
        
        # 1. चन्द्र राशि
        chandra_rashi_name = z_names[int(moon_deg / 30)]
        
        # 2. नक्षत्र
        nakshatras_list = ["अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा", "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"]
        nakshatra_name = nakshatras_list[int(moon_deg / (360/27))]
        
        # 3. तिथि और पक्ष
        angle_diff = (moon_deg - sun_deg) % 360
        tithis_list = ["प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा", "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "अमावस्या"]
        tithi_name = tithis_list[int(angle_diff / 12)]
        paksha_name = "शुक्ल" if angle_diff < 180 else "कृष्ण"
        
        # 4. हिन्दू मास (अमांत सिस्टम के अनुसार)
        hindu_months = ["चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद", "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन"]
        new_moon_deg = (sun_deg - angle_diff) % 360
        hindu_month_name = hindu_months[(int(new_moon_deg / 30) + 1) % 12]

        greeting = "श्री" if gender == "पुरुष" else "सुश्री"
        
        return {
            "name": name, "greeting": greeting, "city": city, "lagna": z_names[l_idx], "houses": houses,
            "planet_details": planet_details, "manglik": manglik_text, "kaalsarp": kaalsarp_text,
            "predictions": predictions_data, "current_dasha_text": current_dasha_text, 
            "dasha": dasha_data, "sav_points": sav_data,
            # 👇 नया पंचांग डेटा जो HTML में भेजा जा रहा है 👇
            "chandra_rashi": chandra_rashi_name,
            "nakshatra": nakshatra_name,
            "tithi": tithi_name,
            "paksha": paksha_name,
            "hindu_month": hindu_month_name
        }
    except Exception as e:
        print(f"Kundali Error: {e}")
        return None
