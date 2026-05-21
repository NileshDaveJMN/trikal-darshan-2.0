# engines/milan_data.py

# 1. 27 Nakshatra Data (Varna, Vashya, Yoni, Gana, Nadi)
NAKSHATRA_DATA = {
    "Ashwini": {"varna": "Kshatriya", "vashya": "Chatushpad", "yoni": "Ashwa", "gana": "Deva", "nadi": "Aadi"},
    "Bharani": {"varna": "Kshatriya", "vashya": "Manav", "yoni": "Gaja", "gana": "Manushya", "nadi": "Madhya"},
    "Krittika": {"varna": "Brahmin", "vashya": "Chatushpad", "yoni": "Mesha", "gana": "Rakshasa", "nadi": "Antya"},
    "Rohini": {"varna": "Shudra", "vashya": "Chatushpad", "yoni": "Sarpa", "gana": "Manushya", "nadi": "Antya"},
    "Mrigashira": {"varna": "Vaishya", "vashya": "Chatushpad", "yoni": "Sarpa", "gana": "Deva", "nadi": "Madhya"},
    "Ardra": {"varna": "Shudra", "vashya": "Manav", "yoni": "Shvan", "gana": "Manushya", "nadi": "Aadi"},
    "Punarvasu": {"varna": "Vaishya", "vashya": "Manav", "yoni": "Marjar", "gana": "Deva", "nadi": "Aadi"},
    "Pushya": {"varna": "Kshatriya", "vashya": "Jalchar", "yoni": "Mesha", "gana": "Deva", "nadi": "Madhya"},
    "Ashlesha": {"varna": "Brahmin", "vashya": "Jalchar", "yoni": "Marjar", "gana": "Rakshasa", "nadi": "Antya"},
    "Magha": {"varna": "Shudra", "vashya": "Keet", "yoni": "Mushak", "gana": "Rakshasa", "nadi": "Antya"},
    "Purva Phalguni": {"varna": "Brahmin", "vashya": "Manav", "yoni": "Mushak", "gana": "Manushya", "nadi": "Madhya"},
    "Uttara Phalguni": {"varna": "Kshatriya", "vashya": "Manav", "yoni": "Gau", "gana": "Manushya", "nadi": "Aadi"},
    "Hasta": {"varna": "Vaishya", "vashya": "Manav", "yoni": "Mahish", "gana": "Deva", "nadi": "Aadi"},
    "Chitra": {"varna": "Shudra", "vashya": "Manav", "yoni": "Vyaghra", "gana": "Rakshasa", "nadi": "Madhya"},
    "Swati": {"varna": "Shudra", "vashya": "Manav", "yoni": "Mahish", "gana": "Deva", "nadi": "Antya"},
    "Vishakha": {"varna": "Shudra", "vashya": "Keet", "yoni": "Vyaghra", "gana": "Rakshasa", "nadi": "Antya"},
    "Anuradha": {"varna": "Shudra", "vashya": "Keet", "yoni": "Mriga", "gana": "Deva", "nadi": "Madhya"},
    "Jyeshtha": {"varna": "Brahmin", "vashya": "Keet", "yoni": "Mriga", "gana": "Rakshasa", "nadi": "Aadi"},
    "Mula": {"varna": "Kshatriya", "vashya": "Chatushpad", "yoni": "Shvan", "gana": "Rakshasa", "nadi": "Aadi"},
    "Purva Ashadha": {"varna": "Brahmin", "vashya": "Manav", "yoni": "Vanar", "gana": "Manushya", "nadi": "Madhya"},
    "Uttara Ashadha": {"varna": "Kshatriya", "vashya": "Chatushpad", "yoni": "Nakul", "gana": "Manushya", "nadi": "Antya"},
    "Shravana": {"varna": "Mleccha", "vashya": "Jalchar", "yoni": "Vanar", "gana": "Deva", "nadi": "Antya"},
    "Dhanishta": {"varna": "Shudra", "vashya": "Jalchar", "yoni": "Simha", "gana": "Rakshasa", "nadi": "Madhya"},
    "Shatabhisha": {"varna": "Shudra", "vashya": "Manav", "yoni": "Ashwa", "gana": "Rakshasa", "nadi": "Aadi"},
    "Purva Bhadrapada": {"varna": "Brahmin", "vashya": "Manav", "yoni": "Simha", "gana": "Manushya", "nadi": "Aadi"},
    "Uttara Bhadrapada": {"varna": "Kshatriya", "vashya": "Jalchar", "yoni": "Gau", "gana": "Manushya", "nadi": "Madhya"},
    "Revati": {"varna": "Shudra", "vashya": "Jalchar", "yoni": "Gaja", "gana": "Deva", "nadi": "Antya"},
}

# 2. Graha Maitri (Grahon ki Dosti - 5 Points)
GRAHA_MAITRI = {
    "Sun": {"Sun": 5, "Moon": 5, "Mars": 5, "Mercury": 4, "Jupiter": 5, "Venus": 0, "Saturn": 0},
    "Moon": {"Sun": 5, "Moon": 5, "Mars": 4, "Mercury": 4, "Jupiter": 4, "Venus": 1, "Saturn": 1},
    "Mars": {"Sun": 5, "Moon": 5, "Mars": 5, "Mercury": 0, "Jupiter": 5, "Venus": 1, "Saturn": 1},
    "Mercury": {"Sun": 4, "Moon": 1, "Mars": 0, "Mercury": 5, "Jupiter": 1, "Venus": 5, "Saturn": 5},
    "Jupiter": {"Sun": 5, "Moon": 5, "Mars": 5, "Mercury": 0, "Jupiter": 5, "Venus": 0, "Saturn": 4},
    "Venus": {"Sun": 0, "Moon": 0, "Mars": 1, "Mercury": 5, "Jupiter": 1, "Venus": 5, "Saturn": 5},
    "Saturn": {"Sun": 0, "Moon": 0, "Mars": 0, "Mercury": 5, "Jupiter": 1, "Venus": 5, "Saturn": 5},
}

# 3. Rashi Lord (Rashi ka swami)
RASHI_LORD = {
    "मेष": "Mars", "वृषभ": "Venus", "मिथुन": "Mercury", "कर्क": "Moon", 
    "सिंह": "Sun", "कन्या": "Mercury", "तुला": "Venus", "वृश्चिक": "Mars", 
    "धनु": "Jupiter", "मकर": "Saturn", "कुंभ": "Saturn", "मीन": "Jupiter"
}
