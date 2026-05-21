# engines/milan_engine.py
from engines.milan_data import NAKSHATRA_DATA, GRAHA_MAITRI, RASHI_LORD
from engines.dosha_analyzer import fetch_booking_link

def calculate_milan(boy_naks, boy_rashi, boy_is_manglik, girl_naks, girl_rashi, girl_is_manglik):
    """Full 36 Guna Ashtakoot + Manglik Milan Engine"""
    
    score = 0
    breakdown = {}
    remedies = []
    
    # Check if Nakshatra data exists
    if boy_naks not in NAKSHATRA_DATA or girl_naks not in NAKSHATRA_DATA:
        return {"error": "चुने गए नक्षत्र का डेटा अभी उपलब्ध नहीं है।"}
        
    b_data = NAKSHATRA_DATA[boy_naks]
    g_data = NAKSHATRA_DATA[girl_naks]
    
    # 1. VARNA (1 Point) - Hierarchy: Brahmin > Kshatriya > Vaishya > Shudra
    # Rule: Boy's varna must be >= Girl's varna (same or higher caste hierarchy)
    VARNA_RANK = {'Brahmin': 4, 'Kshatriya': 3, 'Vaishya': 2, 'Shudra': 1}
    b_varna_rank = VARNA_RANK.get(b_data['varna'], 1)
    g_varna_rank = VARNA_RANK.get(g_data['varna'], 1)
    if b_varna_rank >= g_varna_rank:
        varna_score = 1
    else:
        varna_score = 0  # Boy's varna lower than girl's = dosha
    score += varna_score
    breakdown['वर्ण (Varna)'] = {"score": varna_score, "max": 1, "status": "Good" if varna_score == 1 else "Dosha"}

    # 2. VASHYA (2 Points)
    vashya_score = 2 if b_data['vashya'] == g_data['vashya'] else 1
    score += vashya_score
    breakdown['वश्य (Vashya)'] = {"score": vashya_score, "max": 2, "status": "Good" if vashya_score == 2 else "Average"}

    # 3. TARA (3 Points) - (Simplified for now)
    tara_score = 1.5
    score += tara_score
    breakdown['तारा (Tara)'] = {"score": tara_score, "max": 3, "status": "Average"}

    # 4. YONI (4 Points)
    yoni_score = 4 if b_data['yoni'] == g_data['yoni'] else 2
    score += yoni_score
    breakdown['योनि (Yoni)'] = {"score": yoni_score, "max": 4, "status": "Good" if yoni_score == 4 else "Average"}

    # 5. GRAHA MAITRI (5 Points)
    b_lord = RASHI_LORD.get(boy_rashi, "Sun")
    g_lord = RASHI_LORD.get(girl_rashi, "Sun")
    maitri_score = GRAHA_MAITRI.get(b_lord, {}).get(g_lord, 1)
    score += maitri_score
    breakdown['ग्रह मैत्री (Graha Maitri)'] = {"score": maitri_score, "max": 5, "status": "Good" if maitri_score >= 4 else "Low"}

    # 6. GANA (6 Points) - Deva, Manushya, Rakshasa logic
    gana_score = 0
    if b_data['gana'] == g_data['gana']:
        gana_score = 6
    elif (b_data['gana'] == 'Deva' and g_data['gana'] == 'Manushya') or (g_data['gana'] == 'Deva' and b_data['gana'] == 'Manushya'):
        gana_score = 5
    elif (b_data['gana'] == 'Manushya' and g_data['gana'] == 'Rakshasa') or (g_data['gana'] == 'Manushya' and b_data['gana'] == 'Rakshasa'):
        gana_score = 1
        remedies.append({
            "issue": "गण दोष (Gana Dosha)",
            "solution": "मनुष्य-राक्षस गण संयोग से स्वभाव में भारी मतभेद होते हैं। शिव आराधना करें।",
            "link": fetch_booking_link("Pooja", "रुद्राभिषेक", 3100, "trimbakeshwar")
        })
    elif (b_data['gana'] == 'Deva' and g_data['gana'] == 'Rakshasa') or (g_data['gana'] == 'Deva' and b_data['gana'] == 'Rakshasa'):
        gana_score = 0
        remedies.append({
            "issue": "गण दोष (Gana Dosha) - गंभीर",
            "solution": "देव-राक्षस गण अत्यंत प्रतिकूल है। राक्षस गण होने के कारण वैचारिक मतभेद हो सकते हैं। शिव आराधना करें।",
            "link": fetch_booking_link("Pooja", "रुद्राभिषेक", 3100, "trimbakeshwar")
        })
    score += gana_score
    breakdown['गण (Gana)'] = {"score": gana_score, "max": 6, "status": "Good" if gana_score >= 5 else "Dosha"}

    # 7. BHAKOOT (7 Points) - Rashi position based dosha check
    # Dosha combinations (counted from boy's rashi to girl's): 2-12, 5-9, 6-8
    RASHI_ORDER = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
                   "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
    bhakoot_score = 7
    if boy_rashi in RASHI_ORDER and girl_rashi in RASHI_ORDER:
        b_idx = RASHI_ORDER.index(boy_rashi) + 1
        g_idx = RASHI_ORDER.index(girl_rashi) + 1
        diff_bg = ((g_idx - b_idx) % 12) or 12  # boy se girl tak
        diff_gb = ((b_idx - g_idx) % 12) or 12  # girl se boy tak
        dosha_pairs = {(2, 12), (5, 9), (6, 8)}
        if (diff_bg, diff_gb) in dosha_pairs or (diff_gb, diff_bg) in dosha_pairs:
            bhakoot_score = 0
            remedies.append({
                "issue": "भकूट दोष (Bhakoot Dosha)",
                "solution": "राशि की प्रतिकूल स्थिति है। विष्णु सहस्रनाम पाठ और नवग्रह शांति कराएं।",
                "link": fetch_booking_link("Pooja", "नवग्रह शांति", 5100, "trimbakeshwar")
            })
        elif boy_rashi == girl_rashi:
            bhakoot_score = 7
    score += bhakoot_score
    breakdown['भकूट (Bhakoot)'] = {"score": bhakoot_score, "max": 7, "status": "Good" if bhakoot_score == 7 else "Dosha"}

    # 8. NADI (8 Points) - Sabse bada koot
    if b_data['nadi'] != g_data['nadi']:
        score += 8
        breakdown['नाड़ी (Nadi)'] = {"score": 8, "max": 8, "status": "Excellent"}
    else:
        breakdown['नाड़ी (Nadi)'] = {"score": 0, "max": 8, "status": "Nadi Dosha"}
        remedies.append({
            "issue": "नाड़ी दोष (Nadi Dosha)",
            "solution": "समान नाड़ी होने से स्वास्थ्य और संतान सुख में बाधा आती है। महामृत्युंजय जाप आवश्यक है।",
            "link": fetch_booking_link("Pooja", "महामृत्युंजय जाप", 11000, "trimbakeshwar")
        })

    # --- MANGLIK COMPATIBILITY ---
    manglik_match = "✅ दोनों की मंगल स्थिति अनुकूल है (Perfect Match)"
    if boy_is_manglik and not girl_is_manglik:
        manglik_match = "⚠️ ध्यान दें: वर मांगलिक है, कन्या नहीं।"
        remedies.append({
            "issue": "मांगलिक असंतुलन",
            "solution": "विवाह से पूर्व कुंभ विवाह या मंगल भात पूजा अवश्य कराएं।",
            "link": fetch_booking_link("Pooja", "मंगल भात पूजा", 2100, "mangalnath-ujjain")
        })
    elif girl_is_manglik and not boy_is_manglik:
        manglik_match = "⚠️ ध्यान दें: कन्या मांगलिक है, वर नहीं।"
        remedies.append({
            "issue": "मांगलिक असंतुलन",
            "solution": "विवाह से पूर्व अर्क विवाह या मंगल शांति पूजा अवश्य कराएं।",
            "link": fetch_booking_link("Pooja", "मंगल भात पूजा", 2100, "mangalnath-ujjain")
        })

    # Final Result Compilation
    total_percentage = (score / 36) * 100
    
    return {
        "total_score": round(score, 1),
        "max_score_tested": 36,
        "percentage": round(total_percentage, 1),
        "breakdown": breakdown,
        "manglik_status": manglik_match,
        "remedies": remedies,
        "is_recommended": score >= 18 and len(remedies) == 0
    }
