# engines/panchang_engine.py

import swisseph as swe
import ephem
from datetime import datetime, timedelta

def get_panchang_data(target_dt_ist, is_today):
    try:
        dt_utc = target_dt_ist - timedelta(hours=5, minutes=30)
        jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        res_sun, _ = swe.calc_ut(jd_ut, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        res_moon, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        sun_lon, moon_lon = res_sun[0], res_moon[0]

        tithi_names = ["प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा", "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी", "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "अमावस्या"]
        tithi_idx = int(((moon_lon - sun_lon) % 360) / 12.0)
        paksha = "शुक्ल" if tithi_idx < 15 else "कृष्ण"
        tithi = tithi_names[tithi_idx]

        nak_names = ["अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा", "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"]
        nakshatra = nak_names[int(moon_lon / (360/27.0))]
        z_names = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
        moon_rashi = z_names[int(moon_lon / 30)]
        days = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]

        # 🌟 नया चंद्र मास (Lunar Month) लॉजिक 🌟
        moon_sun_diff = (moon_lon - sun_lon) % 360
        days_since_amavasya = moon_sun_diff / 12.190749
        amavasya_sun_lon = (sun_lon - (days_since_amavasya * 0.9856)) % 360
        amavasya_sun_rashi_idx = int(amavasya_sun_lon / 30)
        
        maas_names = ["वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद", "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन", "चैत्र"]
        hindu_maas = maas_names[amavasya_sun_rashi_idx]

        obs = ephem.Observer()
        obs.lat, obs.long = '28.5839', '77.2090'
        obs.elevation = 216
        obs.horizon = '-0:50'
        sun = ephem.Sun()

        dt_midnight_ist = datetime(target_dt_ist.year, target_dt_ist.month, target_dt_ist.day, 0, 0, 0)
        obs.date = dt_midnight_ist - timedelta(hours=5, minutes=30)

        sr_utc = obs.next_rising(sun).datetime()
        ss_utc = obs.next_setting(sun).datetime()
        sr_ist = sr_utc + timedelta(hours=5, minutes=30)
        ss_ist = ss_utc + timedelta(hours=5, minutes=30)

        obs.date = ss_utc
        next_sr_ist = obs.next_rising(sun).datetime() + timedelta(hours=5, minutes=30)

        obs.date = sr_utc
        prev_ss_utc = obs.previous_setting(sun).datetime()
        prev_ss_ist = prev_ss_utc + timedelta(hours=5, minutes=30) if prev_ss_utc else sr_ist - timedelta(hours=12)

        day_duration_sec = (ss_ist - sr_ist).total_seconds()
        part_dur = day_duration_sec / 8
        wd = target_dt_ist.weekday()

        rahu_map = [2, 7, 5, 6, 4, 3, 8]
        yama_map = [4, 3, 2, 1, 7, 6, 5]
        guli_map = [6, 5, 4, 3, 2, 1, 7]

        def get_muhurat_time(part_no):
            start = sr_ist + timedelta(seconds=(part_no - 1) * part_dur)
            end = start + timedelta(seconds=part_dur)
            return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

        rahukaal = get_muhurat_time(rahu_map[wd])
        yamaganda = get_muhurat_time(yama_map[wd])
        gulika = get_muhurat_time(guli_map[wd])

        mid_day = sr_ist + timedelta(seconds=day_duration_sec / 2)
        ab_start = mid_day - timedelta(minutes=24)
        ab_end = mid_day + timedelta(minutes=24)
        abhijit = f"{ab_start.strftime('%H:%M')} - {ab_end.strftime('%H:%M')}"

        day_names_seq = {
            0: ["अमृत", "काल", "शुभ", "रोग", "उद्वेग", "चल", "लाभ", "अमृत"], 1: ["रोग", "उद्वेग", "चल", "लाभ", "अमृत", "काल", "शुभ", "रोग"],
            2: ["लाभ", "अमृत", "काल", "शुभ", "रोग", "उद्वेग", "चल", "लाभ"], 3: ["शुभ", "रोग", "उद्वेग", "चल", "लाभ", "अमृत", "काल", "शुभ"],
            4: ["चल", "लाभ", "अमृत", "काल", "शुभ", "रोग", "उद्वेग", "चल"], 5: ["काल", "शुभ", "रोग", "उद्वेग", "चल", "लाभ", "अमृत", "काल"],
            6: ["उद्वेग", "चल", "लाभ", "अमृत", "काल", "शुभ", "रोग", "उद्वेग"]
        }
        night_names_seq = {
            0: ["चल", "रोग", "काल", "लाभ", "उद्वेग", "शुभ", "अमृत", "चल"], 1: ["काल", "लाभ", "उद्वेग", "शुभ", "अमृत", "चल", "रोग", "काल"],
            2: ["उद्वेग", "शुभ", "अमृत", "चल", "रोग", "काल", "लाभ", "उद्वेग"], 3: ["अमृत", "चल", "रोग", "काल", "लाभ", "उद्वेग", "शुभ", "अमृत"],
            4: ["रोग", "काल", "लाभ", "उद्वेग", "शुभ", "अमृत", "चल", "रोग"], 5: ["लाभ", "उद्वेग", "शुभ", "अमृत", "चल", "रोग", "काल", "लाभ"],
            6: ["शुभ", "अमृत", "चल", "रोग", "काल", "लाभ", "उद्वेग", "शुभ"]
        }

        all_day_choghadiya = []
        all_night_choghadiya = []
        current_choghadiya = "--- (अन्य दिन) ---"

        for idx in range(8):
            cg_s = sr_ist + (timedelta(seconds=part_dur) * idx)
            cg_e = cg_s + timedelta(seconds=part_dur)
            all_day_choghadiya.append({"name": day_names_seq[wd][idx], "time": f"{cg_s.strftime('%H:%M')} - {cg_e.strftime('%H:%M')}"})

        night_len_sec = (next_sr_ist - ss_ist).total_seconds() / 8
        for idx in range(8):
            cg_s = ss_ist + (timedelta(seconds=night_len_sec) * idx)
            cg_e = cg_s + timedelta(seconds=night_len_sec)
            all_night_choghadiya.append({"name": night_names_seq[wd][idx], "time": f"{cg_s.strftime('%H:%M')} - {cg_e.strftime('%H:%M')}"})

        # 🚀 यहाँ नया फिक्स लागू किया गया है
        if is_today:
            curr_time_str = target_dt_ist.strftime('%H:%M')
            
            # दिन के चौघड़िये चेक करें
            for cg in all_day_choghadiya:
                s, e = cg['time'].split(' - ')
                if s <= curr_time_str < e:
                    current_choghadiya = f"{cg['name']} (दिन) | {cg['time']}"
                    break
            
            # अगर दिन में नहीं मिला, तो रात के चेक करें
            if "---" in current_choghadiya:
                for cg in all_night_choghadiya:
                    s, e = cg['time'].split(' - ')
                    # रात का विशेष लॉजिक: अगर एंड टाइम स्टार्ट से छोटा है (जैसे 23:00 - 01:00)
                    if s <= curr_time_str or curr_time_str < e if e < s else s <= curr_time_str < e:
                        current_choghadiya = f"{cg['name']} (रात्रि) | {cg['time']}"
                        break

        return {
            "date_str": target_dt_ist.strftime("%d %b %Y"),
            "prev_date": (target_dt_ist - timedelta(days=1)).strftime("%Y-%m-%d"),
            "next_date": (target_dt_ist + timedelta(days=1)).strftime("%Y-%m-%d"),
            "day": days[wd],
            "tithi": tithi, "paksha": paksha, "nakshatra": nakshatra, "moon_rashi": moon_rashi,
            "sunrise": sr_ist.strftime('%H:%M'),
            "sunset": ss_ist.strftime('%H:%M'),
            "rahukaal": rahukaal, "yamaganda": yamaganda, "gulika": gulika, "abhijit": abhijit,
            "choghadiya": current_choghadiya, "all_day_choghadiya": all_day_choghadiya, "all_night_choghadiya": all_night_choghadiya,
            "samvat": target_dt_ist.year + 57, "hindu_maas": hindu_maas
        }
    except Exception as e:
        print(f"Panchang Error: {e}")
        return {}
