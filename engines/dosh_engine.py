# engines/dosh_engine.py

def check_manglik(p_pos, l_idx):
    """Manglik dosh check karne ka logic"""
    rel_mars = ((p_pos["Mars"] - l_idx) % 12) + 1
    is_manglik = rel_mars in [1, 4, 7, 8, 12]
    return is_manglik, "मंगल दोष है" if is_manglik else "मंगल दोष नहीं है"

def check_kaalsarp(p_pos, l_idx):
    """रियल कालसर्प दोष चेक करने का सटीक लॉजिक"""
    r_idx = p_pos["Rahu"]
    k_idx = p_pos["Ketu"]

    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

    # हम चेक करेंगे कि क्या सारे ग्रह राहु से केतु की तरफ हैं (Side 1)
    # या केतु से राहु की तरफ हैं (Side 2)
    side1_clear = True
    side2_clear = True

    for p in planets:
        p_house = p_pos[p]

        # राहु और केतु से ग्रहों की दूरी (0 से 11 के बीच)
        dist_from_rahu = (p_house - r_idx) % 12
        dist_from_ketu = (p_house - k_idx) % 12

        # अगर कोई ग्रह राहु से 6 घर से ज्यादा दूर है, तो वह दूसरी तरफ चला गया
        if not (0 <= dist_from_rahu <= 6):
            side1_clear = False

        # अगर कोई ग्रह केतु से 6 घर से ज्यादा दूर है, तो वह दूसरी तरफ चला गया
        if not (0 <= dist_from_ketu <= 6):
            side2_clear = False

    # अगर दोनों तरफ से चेन टूट गई (जैसे नीलेश जी की कुंडली में गुरु के कारण), तो दोष नहीं है
    has_kaalsarp = side1_clear or side2_clear

    if has_kaalsarp:
        rahu_rel_house = ((r_idx - l_idx) % 12) + 1
        kaalsarp_names = {
            1:"अनंत", 2:"कुलिक", 3:"वासुकी", 4:"शंखपाल",
            5:"पद्म", 6:"महापद्म", 7:"तक्षक", 8:"कर्कोटक",
            9:"शंखचूड़", 10:"घातक", 11:"विषधर", 12:"शेषनाग"
        }
        return f"{kaalsarp_names.get(rahu_rel_house, '')} कालसर्प दोष"
    else:
        return "कालसर्प दोष नहीं है"
