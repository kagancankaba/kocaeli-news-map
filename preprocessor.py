"""Metin temizleme"""
import re, unicodedata
from datetime import datetime

def temizle(metin):
    if not metin: return ""
    metin = re.sub(r'<[^>]+>', ' ', metin)
    metin = unicodedata.normalize('NFC', metin)
    metin = re.sub(r'\s+', ' ', metin).strip()
    return metin

def tarih_parse(tarih_str):
    if not tarih_str: return None
    tarih_str = tarih_str.strip()
    ay = {'Ocak':'01','Şubat':'02','Mart':'03','Nisan':'04','Mayıs':'05','Haziran':'06',
          'Temmuz':'07','Ağustos':'08','Eylül':'09','Ekim':'10','Kasım':'11','Aralık':'12'}
    for tr, num in ay.items():
        if tr in tarih_str:
            tarih_str = tarih_str.replace(tr, num)
            for f in ["%d %m %Y %H:%M", "%d %m %Y"]:
                try: return datetime.strptime(tarih_str.strip(), f)
                except: pass
    for f in ["%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%d",
              "%d.%m.%Y %H:%M","%d.%m.%Y","%d/%m/%Y"]:
        try: return datetime.strptime(tarih_str[:len(f)+5], f)
        except: continue
    m = re.search(r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})', tarih_str)
    if m:
        try: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except: pass
    return None
