"""Haber turu siniflandirma"""
import re

KEYWORDS = {
    "Trafik Kazası": [r"kaza", r"çarpıştı", r"devrildi", r"şarampole", r"zincirleme"],
    "Yangın": [r"yangın", r"alev", r"kundak", r"itfaiye"],
    "Elektrik Kesintisi": [r"elektrik", r"sedaş", r"trafo"],
    "Hırsızlık": [r"hırsız", r"gasp", r"soygun", r"çaldı", r"çalındı"],
    "Kültürel Etkinlikler": [r"konser", r"tiyatro", r"sergi", r"festival", r"etkinlik", r"gösteri"],
}

ONCELIK = ["Trafik Kazası", "Yangın", "Elektrik Kesintisi", "Hırsızlık", "Kültürel Etkinlikler"]

RENKLER = {
    "Trafik Kazası": "#ef4444", "Yangın": "#f97316",
    "Elektrik Kesintisi": "#eab308", "Hırsızlık": "#a855f7",
    "Kültürel Etkinlikler": "#22c55e",
}

EMOJILER = {
    "Trafik Kazası": "🚗", "Yangın": "🔥", "Elektrik Kesintisi": "⚡",
    "Hırsızlık": "🔒", "Kültürel Etkinlikler": "🎭",
}

def siniflandir(baslik, icerik=""):
    metin = f"{baslik} {icerik}".lower()
    skorlar = {}
    for tur, kelimeler in KEYWORDS.items():
        skor = 0
        for k in kelimeler:
            if re.search(k, metin, re.IGNORECASE):
                skor += 3 if re.search(k, baslik.lower(), re.IGNORECASE) else 1
        if skor > 0:
            skorlar[tur] = skor
    if not skorlar: return None
    mx = max(skorlar.values())
    adaylar = [t for t, s in skorlar.items() if s == mx]
    if len(adaylar) == 1: return adaylar[0]
    for t in ONCELIK:
        if t in adaylar: return t
    return adaylar[0]
