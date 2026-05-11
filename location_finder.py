"""Konum cikarma ve geocoding - ilce merkez fallback + offset"""
import os, re, random, requests
from dotenv import load_dotenv
from database import geocode_cache_al, geocode_cache_kaydet
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Kocaeli ilce merkez koordinatlari
ILCE_MERKEZLERI = {
    "İzmit":     (40.7654, 29.9408),
    "Gebze":     (40.8027, 29.4304),
    "Darıca":    (40.7693, 29.3753),
    "Çayırova":  (40.8262, 29.3709),
    "Dilovası":  (40.7897, 29.5350),
    "Körfez":    (40.776252, 29.738705),
    "Derince":   (40.7553, 29.8140),
    "Gölcük":    (40.7172, 29.8364),
    "Karamürsel":(40.6910, 29.6158),
    "Başiskele": (40.713007, 29.920691),
    "Kartepe":   (40.6840, 30.0350),
    "Kandıra":   (41.0714, 30.1528),
}

ILCELER = list(ILCE_MERKEZLERI.keys())

# Slug/URL'lerde Turkce karakter olmayan ilce yazilimlari
ILCE_SLUG_MAP = {
    "izmit": "İzmit", "gebze": "Gebze", "darica": "Darıca",
    "cayirova": "Çayırova", "dilovasi": "Dilovası", "korfez": "Körfez",
    "derince": "Derince", "golcuk": "Gölcük", "karamursel": "Karamürsel",
    "basiskele": "Başiskele", "kartepe": "Kartepe", "kandira": "Kandıra",
    # Turkce karakterli versiyonlar da ekle
    "İzmit": "İzmit", "Gebze": "Gebze", "Darıca": "Darıca",
    "Çayırova": "Çayırova", "Dilovası": "Dilovası", "Körfez": "Körfez",
    "Derince": "Derince", "Gölcük": "Gölcük", "Karamürsel": "Karamürsel",
    "Başiskele": "Başiskele", "Kartepe": "Kartepe", "Kandıra": "Kandıra",
}

KOCAELI_MERKEZ = (40.7654, 29.9408)


def ilce_bul(metin):
    """Metinden ilce adi bul - hem Turkce hem slug formati destekler."""
    if not metin: return None
    m = metin.lower()
    # Oncelik: tam Turkce isim
    for ilce in ILCELER:
        if ilce.lower() in m: return ilce
    # Slug formati (turkce karaktersiz)
    for slug, ilce in ILCE_SLUG_MAP.items():
        if slug.lower() in m: return ilce
    return None


def offset_ekle(lat, lng):
    """Ust uste binmesin diye ~50-150m rastgele offset ekle."""
    lat += random.uniform(-0.0015, 0.0015)
    lng += random.uniform(-0.0015, 0.0015)
    return lat, lng


def konum_cikar(metin):
    if not metin: return None, None
    ilce = ilce_bul(metin)
    parcalar = []
    for m in re.findall(r'([A-ZÇĞİÖŞÜa-zçğıöşü]+)\s+[Mm]ahallesi', metin):
        parcalar.append(f"{m} Mahallesi")
    for m in re.findall(r'([A-ZÇĞİÖŞÜa-zçğıöşü\s]{3,30})\s+(?:[Ss]okak|[Cc]addesi|[Bb]ulvarı)', metin):
        parcalar.append(m.strip())
    for yer in ["D-100","TEM","E-80","Yahyakaptan","Şekerpınar","Hereke",
                "Değirmendere","Maşukiye","Bahçecik","Osmangazi Köprüsü","Yuvacık"]:
        if yer.lower() in metin.lower(): parcalar.append(yer)
    parcalar = list(dict.fromkeys(parcalar))
    if parcalar or ilce:
        if ilce:
            k = ", ".join(parcalar+[ilce,"Kocaeli"]) if parcalar else f"{ilce}, Kocaeli"
        else:
            k = ", ".join(parcalar+["Kocaeli"])
        return k, ilce
    if "kocaeli" in metin.lower(): return "Kocaeli", None
    return None, None


def geocode(adres):
    if not adres or not API_KEY or "BURAYA" in API_KEY: return None, None
    e, b = geocode_cache_al(adres)
    if e: return e, b
    try:
        r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
            params={"address":adres,"key":API_KEY,"language":"tr","region":"tr",
                    "bounds":"40.6,29.2|40.9,30.2"}, timeout=10)
        data = r.json()
        if data["status"]=="OK" and data["results"]:
            loc = data["results"][0]["geometry"]["location"]
            lat, lng = loc["lat"], loc["lng"]
            if 40.5<=lat<=41.0 and 29.0<=lng<=30.5:
                geocode_cache_kaydet(adres, lat, lng)
                return lat, lng
    except: pass
    return None, None


def koordinat_bul(konum_metin, ilce):
    """
    3 asamali koordinat bulma:
    1. Geocoding API ile tam adres
    2. Bulamazsa ilce merkezini kullan
    3. Ilce de yoksa Kocaeli merkezini kullan
    Her durumda offset ekle
    """
    if konum_metin:
        lat, lng = geocode(konum_metin)
        if lat and lng:
            return offset_ekle(lat, lng)

    if ilce and ilce in ILCE_MERKEZLERI:
        lat, lng = ILCE_MERKEZLERI[ilce]
        return offset_ekle(lat, lng)

    lat, lng = KOCAELI_MERKEZ
    return offset_ekle(lat, lng)
