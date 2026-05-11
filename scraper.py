"""
SCRAPER - Arsiv Tabanli Haber Toplama (HIZLI VERSIYON)
=======================================================
ONCEKI: Her linkin detay sayfasini indirip sonra siniflandiriyordu (YAVAS)
SIMDI:  Link slug'indan + arsiv sayfasindaki basliktan keyword kontrolu yapar,
        sadece eslesen haberlerin detay sayfasina gider (HIZLI)

4 KOGA sitesi, arsiv linkleri uzerinden son 1-3 gun
Arsiv URL: https://SITE/arsiv/YYYY-MM-DD
"""

import os, re, time, requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from preprocessor import temizle, tarih_parse
from classifier import siniflandir, KEYWORDS
from location_finder import konum_cikar, koordinat_bul, ilce_bul
from database import haber_kaydet, haber_var_mi, veritabanini_temizle

load_dotenv()

UA = os.getenv("USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0")

HEADERS = {"User-Agent": UA, "Accept": "text/html", "Accept-Language": "tr-TR,tr;q=0.9"}
BEKLEME = 1.0

SITELER = [
    ("Çağdaş Kocaeli", "https://www.cagdaskocaeli.com.tr"),
    ("Özgür Kocaeli",  "https://www.ozgurkocaeli.com.tr"),
    ("Ses Kocaeli",    "https://www.seskocaeli.com"),
    ("Bizim Yaka",     "https://www.bizimyaka.com"),
]

# Tum keyword'leri tek bir flat liste yap (hizli kontrol icin)
TUM_KEYWORDLER = []
for kelimeler in KEYWORDS.values():
    TUM_KEYWORDLER.extend(kelimeler)


def indir(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        return r.text if r.status_code == 200 else None
    except:
        return None


def meta(soup, prop):
    t = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
    return t.get("content", "").strip() if t else ""


def hizli_keyword_kontrol(metin):
    """Metinde herhangi bir keyword geciyor mu? True/False."""
    metin_lower = metin.lower()
    for kw in TUM_KEYWORDLER:
        if re.search(kw, metin_lower):
            return True
    return False


# ==============================================================
# ARSIV SAYFASINDAN LINKLERI + BASLIKLARI TOPLA
# ==============================================================

def arsiv_linklerini_topla(base_url, tarih):
    """
    Arsiv sayfasindan haber linklerini VE basliklarini toplar.
    Baslik bilgisi: a etiketinin text'i veya slug'dan turetilir.
    """
    tarih_str = tarih.strftime("%Y-%m-%d")
    arsiv_url = f"{base_url}/arsiv/{tarih_str}"
    print(f"    Arsiv: {arsiv_url}")

    html = indir(arsiv_url)
    if not html:
        print(f"    ❌ Indirilemedi")
        return []

    soup = BeautifulSoup(html, "lxml")
    haberler = []
    gorulen = set()
    pattern = re.compile(r'/haber/\d+/')

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/haber/"):
            href = base_url + href
        if base_url not in href or not pattern.search(href):
            continue
        if any(x in href for x in ["/foto/", "/video/", "/makale/"]):
            continue
        if href in gorulen:
            continue
        gorulen.add(href)

        # Baslik: a etiketinin texti veya slug'dan cikart
        baslik_raw = a.get_text(strip=True)
        # Slug'dan baslik (URL'deki son kisim, tire -> bosluk)
        slug = href.rstrip("/").split("/")[-1]
        slug_baslik = slug.replace("-", " ")

        # Hangisi daha uzunsa onu kullan
        onizleme = baslik_raw if len(baslik_raw) > len(slug_baslik) else slug_baslik

        haberler.append({"link": href, "onizleme": onizleme})

    print(f"    {len(haberler)} link bulundu")
    return haberler


# ==============================================================
# DETAY SAYFASI
# ==============================================================

def detay_cek(url):
    html = indir(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    baslik = meta(soup, "og:title")
    if not baslik:
        h1 = soup.find("h1")
        if h1: baslik = h1.get_text(strip=True)
    if not baslik:
        return None

    skip = ["haberleri", "gündem", "asayiş", "ekonomi", "manşet", "son dakika"]
    if any(s in baslik.lower() for s in skip) and len(baslik) < 30:
        return None

    icerik = meta(soup, "og:description")
    for cls in ["content-text", "detail-text", "post-text", "entry-content"]:
        div = soup.find("div", class_=re.compile(cls, re.I))
        if div:
            ps = [p.get_text(strip=True) for p in div.find_all("p") if p.get_text(strip=True)]
            txt = " ".join(ps)
            if len(txt) > len(icerik): icerik = txt
            break

    if len(icerik) < 50:
        ps = soup.find_all("p")
        parcalar = [p.get_text(strip=True) for p in ps
                    if len(p.get_text(strip=True)) > 30
                    and "©" not in p.get_text()
                    and "Veri politikası" not in p.get_text()]
        if parcalar: icerik = " ".join(parcalar[:8])

    tarih = ""
    for prop in ["article:published_time", "datePublished", "og:updated_time"]:
        t = meta(soup, prop)
        if t: tarih = t; break
    if not tarih:
        tt = soup.find("time")
        if tt: tarih = tt.get("datetime", "") or tt.get_text(strip=True)

    return {"baslik": baslik, "icerik": icerik, "tarih": tarih}


# ==============================================================
# ISLE VE KAYDET
# ==============================================================

def isle_ve_kaydet(baslik, icerik, link, tarih_str, kaynak, arsiv_tarihi):
    baslik = temizle(baslik)
    icerik = temizle(icerik)
    if not baslik or not link: return False
    if haber_var_mi(link): return False

    tur = siniflandir(baslik, icerik)
    if not tur: return False

    tarih = tarih_parse(tarih_str)
    if not tarih: tarih = arsiv_tarihi

    tam = f"{baslik} {icerik}"
    konum_metin, ilce = konum_cikar(tam)
    if not ilce:
        ilce = ilce_bul(tam)

    # 3 asamali: geocoding -> ilce merkezi -> kocaeli merkez
    enlem, boylam = koordinat_bul(konum_metin, ilce)

    haber_kaydet({
        "haber_turu": tur,
        "baslik": baslik,
        "icerik": icerik[:2000],
        "konum": konum_metin or "",
        "enlem": enlem,
        "boylam": boylam,
        "yayin_tarihi": tarih,
        "kaynak": kaynak,
        "link": link,
        "ilce": ilce,
        "kaynaklar": [kaynak],
    })
    return True


# ==============================================================
# SITE TARA
# ==============================================================

def site_tara(kaynak_adi, base_url, gun_sayisi=3, callback=None):
    print(f"\n  [{kaynak_adi}]")
    toplam = 0
    atlanan = 0
    bugun = datetime.now()

    for gun in range(gun_sayisi):
        tarih = bugun - timedelta(days=gun)
        haberler = arsiv_linklerini_topla(base_url, tarih)

        for i, haber in enumerate(haberler):
            link = haber["link"]
            onizleme = haber["onizleme"]

            if haber_var_mi(link):
                continue

            # *** HIZLI FILTRE: Baslik/slug'da keyword var mi? ***
            if not hizli_keyword_kontrol(onizleme):
                atlanan += 1
                continue  # Detay sayfasina GITME, atla

            # Keyword eslesti -> detay sayfasini indir
            detay = detay_cek(link)
            if detay:
                ok = isle_ve_kaydet(
                    detay["baslik"], detay["icerik"], link,
                    detay["tarih"], kaynak_adi, tarih
                )
                if ok:
                    toplam += 1
                    print(f"      ✓ {toplam}. {detay['baslik'][:55]}")

            if callback:
                callback(kaynak_adi, i + 1, len(haberler), toplam)

            time.sleep(BEKLEME)

    print(f"  [{kaynak_adi}] Kaydedilen: {toplam} | Atlanan: {atlanan}")
    return toplam


# ==============================================================
# ANA
# ==============================================================

def tum_kaynaklari_tara(gun_sayisi=3, callback=None):
    print("\n" + "=" * 55)
    print(f"  KOCAELI HABER SCRAPING (Son {gun_sayisi} gün)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Sadece keyword eslesen haberler cekilecek")
    print("=" * 55)

    # Veritabanini sifirla
    veritabanini_temizle()

    toplam = 0
    for kaynak, url in SITELER:
        try:
            n = site_tara(kaynak, url, gun_sayisi, callback)
            toplam += n
        except Exception as e:
            print(f"  [{kaynak}] HATA: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*55}")
    print(f"  TOPLAM: {toplam} yeni haber")
    print(f"{'='*55}")
    return toplam


if __name__ == "__main__":
    from database import init_db
    init_db()
    tum_kaynaklari_tara(gun_sayisi=3)
