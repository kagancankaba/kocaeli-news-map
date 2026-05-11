"""MongoDB islemleri"""
import os
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv
load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGODB_DB", "kocaeli_haberler")]
haberler_col = db["haberler"]
geocode_cache_col = db["geocode_cache"]

def init_db():
    haberler_col.create_index("link", unique=True, sparse=True)
    haberler_col.create_index([("yayin_tarihi", DESCENDING)])
    haberler_col.create_index("haber_turu")
    geocode_cache_col.create_index("adres", unique=True)

def haber_var_mi(link):
    return haberler_col.find_one({"link": link}) is not None

def haber_kaydet(data):
    try:
        haberler_col.update_one({"link": data["link"]}, {"$set": data}, upsert=True)
        return True
    except Exception as e:
        print(f"[DB] {e}")
        return False

def haberleri_getir(filtreler=None):
    q = {"enlem": {"$ne": None}, "boylam": {"$ne": None}}
    if filtreler:
        if filtreler.get("haber_turu") and filtreler["haber_turu"] != "Tümü":
            q["haber_turu"] = filtreler["haber_turu"]
        if filtreler.get("ilce") and filtreler["ilce"] != "Tümü":
            q["ilce"] = filtreler["ilce"]
        if filtreler.get("baslangic"):
            q.setdefault("yayin_tarihi", {})["$gte"] = filtreler["baslangic"]
        if filtreler.get("bitis"):
            q.setdefault("yayin_tarihi", {})["$lte"] = filtreler["bitis"]
    sonuc = list(haberler_col.find(q, {"_id": 0}).sort("yayin_tarihi", DESCENDING))
    for h in sonuc:
        for k in ["yayin_tarihi"]:
            if isinstance(h.get(k), datetime):
                h[k] = h[k].strftime("%Y-%m-%d %H:%M")
    return sonuc

def tum_haberler_benzerlik():
    return list(haberler_col.find({}, {"_id":1,"baslik":1,"icerik":1,"kaynak":1}))

def birlestir(ana_id, kopya_id, ek_kaynak):
    haberler_col.update_one({"_id": ana_id}, {"$addToSet": {"kaynaklar": ek_kaynak}})
    haberler_col.delete_one({"_id": kopya_id})

def haber_sayisi():
    return haberler_col.count_documents({"enlem": {"$ne": None}})

def ilceleri_getir():
    return sorted([i for i in haberler_col.distinct("ilce") if i])

def geocode_cache_al(adres):
    r = geocode_cache_col.find_one({"adres": adres})
    return (r["enlem"], r["boylam"]) if r else (None, None)

def geocode_cache_kaydet(adres, enlem, boylam):
    geocode_cache_col.update_one({"adres": adres},
        {"$set": {"adres": adres, "enlem": enlem, "boylam": boylam}}, upsert=True)

def veritabanini_temizle():
    haberler_col.delete_many({})
    print("[DB] Veritabani sifirlandi.")
