# engines/ashtakvarg_engine.py

# सर्वाष्टकवर्ग (SAV) के 337 बिंदुओं का मानक नियम (Bhinnashtakvarga Rules)
BAV_RULES = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [3, 4, 6, 10, 11, 12]
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [3, 6, 10, 11]
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 3, 6, 10, 11]
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 2, 4, 6, 8, 10, 11]
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11]
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Lagna": [1, 2, 3, 4, 5, 8, 9, 11]
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [1, 3, 4, 6, 10, 11]
    }
}

def get_ashtakvarg_data(p_pos, l_idx):
    """
    ग्रहों की स्थिति (p_pos) और लग्न (l_idx) के आधार पर 
    भाव के अनुसार 12 भावों का सर्वाष्टकवर्ग (SAV) स्कोर निकालता है।
    """
    # 12 राशियों के लिए एक खाली ऐरे (0 से 11)
    sav_rashi_points = [0] * 12
    
    # 7 ग्रहों के लिए गणना (राहु-केतु अष्टकवर्ग में नहीं गिने जाते)
    planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    
    # अष्टकवर्ग में दान देने वाले और प्राप्त करने वाले हर ग्रह का लूप
    for giving_planet in planets:
        for ref_planet in planets + ["Lagna"]:
            # संदर्भ ग्रह या लग्न की राशि प्राप्त करें
            if ref_planet == "Lagna":
                ref_rashi = l_idx
            else:
                ref_rashi = p_pos.get(ref_planet)
                
            # यदि कोई ग्रह मौजूद नहीं है तो छोड़ दें
            if ref_rashi is None:
                continue
                
            # नियम सूची से स्थान प्राप्त करें
            points_positions = BAV_RULES[giving_planet][ref_planet]
            
            for pos in points_positions:
                # 1-आधारित इंडेक्स को 0-आधारित में बदलें और राशि निकालें
                target_rashi = (ref_rashi + pos - 1) % 12
                sav_rashi_points[target_rashi] += 1
                
    # अब राशियों के इन बिंदुओं को लग्न (भाव 1) के अनुसार अलाइन करें
    sav_bhav_points = [0] * 12
    for i in range(12):
        # लग्न राशि से शुरू करके 1 से 12 भावों में पॉइंट्स भरें
        current_rashi = (l_idx + i) % 12
        sav_bhav_points[i] = sav_rashi_points[current_rashi]
        
    return sav_bhav_points
