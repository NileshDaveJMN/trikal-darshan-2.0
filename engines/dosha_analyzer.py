# engines/dosha_analyzer.py
import urllib.parse
import swisseph as swe
from datetime import datetime

# 🌟 NAYA SMART ROUTER: Ab ye mandir ke hisab se sahi rasta chusega
def fetch_booking_link(item_type, keyword, default_price, temple_slug=None):
    """Render par host kiye gaye 'Mera Mandir / Vedic Store' ka direct link"""
    
    # DHYAN DEIN: Yahan apna asli live Render URL lagayein
    base_url = "https://mera-mandir-live.onrender.com" 
    
    # 1. Agar Ratna (Gemstone) hai, to seedha Store page par bhejo
    if item_type == "Gemstone":
        return f"{base_url}/store"
        
    # 2. Agar koi specific mandir diya hai, to ab booking form nahi, balki MANDIR KE PAGE par bhejo
    if temple_slug:
        return f"{base_url}/mandir/{temple_slug}"
    
    # 3. Agar koi mandir nahi hai, to Render ke home page par bhej do
    return f"{base_url}/"

def check_sadesati(planet_details):
    """वर्तमान शनि गोचर के आधार पर लाइव साढ़ेसाती और ढैय्या कैलकुलेटर"""
    try:
        # 1. यूज़र की जन्म चंद्र राशि निकालें
        z_names = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
        moon_rashi_name = next((p['rashi'] for p in planet_details if p['name'] in ['चंद्र', 'Moon']), None)
        if not moon_rashi_name: return None
        
        m_idx = z_names.index(moon_rashi_name)
        
        # 2. आज का लाइव शनि गोचर (Transit) निकालें
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        now = datetime.utcnow()
        jd_now = swe.julday(now.year, now.month, now.day, 0)
        sat_pos, _ = swe.calc_ut(jd_now, swe.SATURN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        s_idx = int(sat_pos[0] / 30)
        
        # 3. दूरी निकालें (शनि चंद्र से कितना दूर है)
        diff = (s_idx - m_idx) % 12
        
        status, desc = None, ""
        remedy = "हर शनिवार शनि मंदिर में सरसों के तेल का दीपक जलाएं। विशेष: नवग्रह शांति पूजा करवाएं या 'नीलम' रत्न धारण करें।"
        
        if diff == 11:
            status = "शनि की साढ़ेसाती (प्रथम चरण)"
            desc = "वर्तमान में आप पर शनि की साढ़ेसाती का पहला चरण चल रहा है। यह मानसिक तनाव, स्थान परिवर्तन और अधिक खर्च का समय होता है।"
        elif diff == 0:
            status = "शनि की साढ़ेसाती (द्वितीय चरण / शिखर)"
            desc = "वर्तमान में आप पर शनि की साढ़ेसाती का दूसरा (मुख्य) चरण चल रहा है। यह संघर्ष, स्वास्थ्य संबंधी परेशानियां और कड़ी परीक्षा का समय है।"
        elif diff == 1:
            status = "शनि की साढ़ेसाती (अंतिम चरण)"
            desc = "वर्तमान में आप पर शनि की साढ़ेसाती का अंतिम चरण (उतरती साढ़ेसाती) चल रहा है। यह जाते हुए शनि का प्रभाव है, जो धीरे-धीरे राहत और स्थिरता लाएगा।"
        elif diff == 3:
            status = "शनि की ढैय्या (कंटक शनि)"
            desc = "वर्तमान में आप पर शनि की 'कंटक ढैय्या' (चतुर्थ भाव) चल रही है। यह पारिवारिक जीवन में कलह, माता के कष्ट और मानसिक अशांति दे सकती है।"
        elif diff == 7:
            status = "शनि की ढैय्या (अष्टम शनि)"
            desc = "वर्तमान में आप पर शनि की 'अष्टम ढैय्या' चल रही है। यह करियर में अचानक बाधाएं, गुप्त चिंताएं और स्वास्थ्य संबंधी समस्याएं दे सकती है।"
            
        if status:
            return {
                'name': status,
                'severity': 'High',
                'description': desc,
                'remedy': remedy,
                'temple_name': 'शनि शिंगणापुर / शनि शांति',
                # 🚀 SMART ROUTER: सीधा स्टोर (नीलम रत्न) पर भेजें
                'booking_url': fetch_booking_link("Gemstone", "नीलम", 6299)
            }
    except Exception as e:
        print("Sade Sati Error:", e)
    return None

def analyze_doshas(houses_data, planet_details):
    doshas = []
    
    # 1. सभी ग्रहों के भाव (House Number) का पता लगाएं
    p_house = {}
    for h_num, h_data in houses_data.items():
        text = h_data.get('planets_full', '') + h_data.get('planets', '')
        if 'Sun' in text or 'सूर्य' in text: p_house['Sun'] = int(h_num)
        if 'Moon' in text or 'चंद्र' in text: p_house['Moon'] = int(h_num)
        if 'Mars' in text or 'मंगल' in text: p_house['Mars'] = int(h_num)
        if 'Mercury' in text or 'बुध' in text: p_house['Mercury'] = int(h_num)
        if 'Jupiter' in text or 'गुरु' in text: p_house['Jupiter'] = int(h_num)
        if 'Venus' in text or 'शुक्र' in text: p_house['Venus'] = int(h_num)
        if 'Saturn' in text or 'शनि' in text: p_house['Saturn'] = int(h_num)
        if 'Rahu' in text or 'राहु' in text: p_house['Rahu'] = int(h_num)
        if 'Ketu' in text or 'केतु' in text: p_house['Ketu'] = int(h_num)

    # ==========================================
    # 3. पितृ दोष (Pitra Dosha) का लॉजिक
    # ==========================================
    sun_house = p_house.get('Sun')
    rahu_house = p_house.get('Rahu')
    ketu_house = p_house.get('Ketu')
    
    is_pitra_dosh = False
    pd_reason = ""
    
    if sun_house and rahu_house and sun_house == rahu_house:
        is_pitra_dosh = True
        pd_reason = f"सूर्य और राहु दोनों {sun_house}वें भाव में एक साथ बैठे हैं, जिससे सूर्य-राहु ग्रहण और पितृ दोष बन रहा है।"
    elif sun_house and ketu_house and sun_house == ketu_house:
        is_pitra_dosh = True
        pd_reason = f"सूर्य और केतु दोनों {sun_house}वें भाव में एक साथ बैठे हैं, जिससे सूर्य-केतु ग्रहण और पितृ दोष बन रहा है।"
    elif rahu_house == 9:
        is_pitra_dosh = True
        pd_reason = "राहु नवम (पिता और भाग्य) भाव में स्थित है, जो कुंडली में पितृ दोष का निर्माण कर रहा है।"
        
    if is_pitra_dosh:
        pd_link = fetch_booking_link("Pooja", "नारायण नागबलि (पितृ दोष) पूजा", 5100, "trimbakeshwar")
        doshas.append({
            'name': 'पितृ दोष (Pitra Dosha)',
            'severity': 'High',
            'description': f"आपकी कुंडली में पितृ दोष मौजूद है। कारण: {pd_reason} इससे जीवन में अकारण संघर्ष, कार्यों में रुकावट और पारिवारिक अशांति हो सकती है।",
            'remedy': "अमावस्या के दिन  पितृ  के निमित्त दान करें। विशेष: त्र्यंबकेश्वर (नासिक) में नारायण नागबलि पूजा करवाएं।",
            'temple_name': 'त्र्यंबकेश्वर ज्योतिर्लिंग, नासिक',
            'booking_url': pd_link
        })

    # 2. मांगलिक दोष (Manglik Dosha)
    mars_h = p_house.get('Mars')
    if mars_h in [1, 4, 7, 8, 12]:
        if mars_h == 8:
            sev, severity_level = "अत्यधिक (कठोर)", "High"
            desc = "मंगल अष्टम (8वें) भाव में है। यह सबसे प्रबल मांगलिक दोष है जो वैवाहिक जीवन में गंभीर बाधाएं या स्वास्थ्य समस्याएं दे सकता है।"
            remedy = "विवाह से पूर्व 'कुंभ विवाह' या 'अर्क विवाह' अवश्य करें और उज्जैन के मंगलनाथ मंदिर में भात पूजा कराएं।"
        elif mars_h == 7:
            sev, severity_level = "उच्च (High)", "High"
            desc = "मंगल सप्तम (7वें) भाव में है। यह वैवाहिक जीवन और पार्टनरशिप में भारी तनाव उत्पन्न कर सकता है।"
            remedy = "नियमित रूप से हनुमान चालीसा का पाठ करें और मंगलनाथ (उज्जैन) में विशेष भात पूजा कराएं।"
        elif mars_h == 1:
            sev, severity_level = "मध्यम (Medium)", "Partial"
            desc = "मंगल लग्न (प्रथम) भाव में है। यह जातक को क्रोधी और आक्रामक बना सकता है, जिससे रिश्तों में खटास आती है।"
            remedy = "मंगलवार का व्रत रखें और शिवलिंग पर लाल चंदन अर्पित करें। मंगलनाथ मंदिर में मंगल शांति पूजा लाभकारी है।"
        elif mars_h == 4:
            sev, severity_level = "आंशिक (Low)", "Partial"
            desc = "मंगल चतुर्थ (4थे) भाव में है। यह पारिवारिक सुख में कमी और माता के स्वास्थ्य को प्रभावित कर सकता है।"
            remedy = "बरगद के पेड़ की जड़ में मीठा दूध चढ़ाएं और उज्जैन स्थित मंगलनाथ मंदिर में शांति पूजा कराएं।"
        elif mars_h == 12:
            sev, severity_level = "आंशिक (Low)", "Partial"
            desc = "मंगल द्वादश (12वें) भाव में है। यह धन का अपव्यय, नींद की कमी और गुप्त शत्रु दे सकता है।"
            remedy = "रोजाना सूर्य देव को जल अर्पित करें और मंगलनाथ (उज्जैन) में भात पूजा करवाएं।"
            
        # 🚀 SMART ROUTING: Yahan slug "mangalnath" lagaya hai (dhyan rakhein admin panel me yahi slug ho)
        booking_link = fetch_booking_link("Pooja", "Mangal Bhat Pooja", 2100, temple_slug="mangalnath")
            
        doshas.append({
            'name': 'मांगलिक दोष',
            'status': sev,
            'severity': severity_level,
            'description': desc,
            'remedy': remedy,
            'temple_name': 'मंगलनाथ मंदिर, उज्जैन',
            'booking_url': booking_link 
        })

    # 3. कालसर्प दोष (Kaalsarp Dosha)
    r_h = p_house.get('Rahu')
    k_h = p_house.get('Ketu')
    
    if r_h and k_h:
        side1_clear = True
        side2_clear = True
        planets_to_check = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
        
        for p in planets_to_check:
            if p not in p_house: continue
            ph = p_house[p]
            dist_r = (ph - r_h) % 12
            dist_k = (ph - k_h) % 12
            if not (0 <= dist_r <= 6): side1_clear = False
            if not (0 <= dist_k <= 6): side2_clear = False

        is_kaalsarp = side1_clear or side2_clear
        
        if is_kaalsarp:
            kaalsarp_types = {
                1: ("अनंत कालसर्प दोष", "राहु प्रथम और केतु सप्तम भाव में है।", "भगवान शिव का रुद्राभिषेक कराएं।"),
                2: ("कुलिक कालसर्प दोष", "राहु द्वितीय और केतु अष्टम भाव में है।", "शिवलिंग पर दूध अर्पित करें।"),
                3: ("वासुकि कालसर्प दोष", "राहु तृतीय और केतु नवम भाव में है।", "नवनाग स्तोत्र का पाठ करें।"),
                4: ("शंखपाल कालसर्प दोष", "राहु चतुर्थ और केतु दशम भाव में है।", "घर में मोरपंख रखें।"),
                5: ("पद्म कालसर्प दोष", "राहु पंचम और केतु एकादश भाव में है।", "जरूरतमंद छात्रों को स्टेशनरी बांटें।"),
                6: ("महापद्म कालसर्प दोष", "राहु षष्ठम और केतु द्वादश भाव में है।", "शिव पंचाक्षर मंत्र का जाप करें।"),
                7: ("तक्षक कालसर्प दोष", "राहु सप्तम और केतु प्रथम भाव में है।", "चांदी का नाग-नागिन नदी में प्रवाहित करें।"),
                8: ("कर्कोटक कालसर्प दोष", "राहु अष्टम और केतु द्वितीय भाव में है।", "शनिवार के दिन बहते जल में कोयला प्रवाहित करें।"),
                9: ("शंखचूड़ कालसर्प दोष", "राहु नवम और केतु तृतीय भाव में है।", "राहु-केतु के मंत्रों का जाप करें।"),
                10: ("घातक कालसर्प दोष", "राहु दशम और केतु चतुर्थ भाव में है।", "पीतल के बर्तन में गंगाजल भरकर घर में रखें।"),
                11: ("विषधर कालसर्प दोष", "राहु एकादश और केतु पंचम भाव में है।", "पीपल के पेड़ के नीचे सरसों के तेल का दीपक जलाएं।"),
                12: ("शेषनाग कालसर्प दोष", "राहु द्वादश और केतु षष्ठम भाव में है।", "लाल कपड़े में नारियल बांधकर जल में प्रवाहित करें।")
            }
            
            if r_h in kaalsarp_types:
                ks_name, ks_desc, ks_remedy = kaalsarp_types[r_h]
                
                # 🚀 SMART ROUTING: Yahan slug "trimbakeshwar" lagaya hai
                ks_link = fetch_booking_link("Pooja", "Kaalsarp Shanti Pooja", 5100, temple_slug="trimbakeshwar")
                
                doshas.append({
                    'name': ks_name,
                    'status': 'Present (पूर्ण)',
                    'severity': 'High',
                    'description': ks_desc,
                    'remedy': ks_remedy + " विशेष: नासिक के त्र्यंबकेश्वर ज्योतिर्लिंग में कालसर्प शांति पूजा कराएं।",
                    'temple_name': 'त्र्यंबकेश्वर ज्योतिर्लिंग, नासिक',
                    'booking_url': ks_link 
                })
    # ==========================================
    # 4. शनि की साढ़ेसाती और ढैय्या का लाइव चेक
    # ==========================================
    sadesati_data = check_sadesati(planet_details)
    if sadesati_data:
        doshas.append(sadesati_data)
        
    return doshas # (यह लाइन पहले से होगी)
    
    return doshas

def recommend_gemstone(lagna_name):
    gem_data = {
        "मेष": {"stone": "मूंगा (Red Coral)", "planet": "मंगल"},
        "वृषभ": {"stone": "हीरा / ओपल (Opal)", "planet": "शुक्र"},
        "मिथुन": {"stone": "पन्ना (Emerald)", "planet": "बुध"},
        "कर्क": {"stone": "मोती (Pearl)", "planet": "चंद्र"},
        "सिंह": {"stone": "माणिक्य (Ruby)", "planet": "सूर्य"},
        "कन्या": {"stone": "पन्ना (Emerald)", "planet": "बुध"},
        "तुला": {"stone": "हीरा / ओपल (Opal)", "planet": "शुक्र"},
        "वृश्चिक": {"stone": "मूंगा (Red Coral)", "planet": "मंगल"},
        "धनु": {"stone": "पुखराज (Yellow Sapphire)", "planet": "गुरु"},
        "मकर": {"stone": "नीलम (Blue Sapphire)", "planet": "शनि"},
        "कुंभ": {"stone": "नीलम (Blue Sapphire)", "planet": "शनि"},
        "मीन": {"stone": "पुखराज (Yellow Sapphire)", "planet": "गुरु"}
    }
    
    default_gem = {"stone": "पंचमुखी रुद्राक्ष", "planet": "शिव"}
    gem = gem_data.get(lagna_name, default_gem)
    
    # 🚀 SMART ROUTING: Ratna ke liye seedha store page khulega
    gem['booking_url'] = fetch_booking_link("Gemstone", gem['stone'], 15000)
    
    return gem
