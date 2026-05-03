# engines/utils.py

# Hindi Names Constants
P_HINDI_FULL = {"Sun":"सूर्य", "Moon":"चंद्र", "Mars":"मंगल", "Mercury":"बुध", "Jupiter":"गुरु", "Venus":"शुक्र", "Saturn":"शनि", "Rahu":"राहु", "Ketu":"केतु"}
P_HINDI_SHORT = {"Sun":"सू", "Moon":"चं", "Mars":"मं", "Mercury":"बु", "Jupiter":"गु", "Venus":"शु", "Saturn":"श", "Rahu":"रा", "Ketu":"के"}
HINDI_MONTHS = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]

def get_formatted_degree(decimal_deg):
    """Decimal degree ko Rashi aur DMS (Degree Minute Second) format mein badalne ke liye"""
    z_names = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
    rashi_idx = int(decimal_deg / 30)
    rashi_name = z_names[rashi_idx]

    deg_in_rashi = decimal_deg % 30
    d, m = int(deg_in_rashi), int((deg_in_rashi % 1) * 60)
    s = int(((deg_in_rashi * 60) % 1) * 60)

    return {"rashi": rashi_name, "degree": f"{d:02d}° {m:02d}' {s:02d}\""}
