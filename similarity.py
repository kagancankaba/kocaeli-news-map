"""Metin benzerligi - TF-IDF"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import tum_haberler_benzerlik, birlestir

def benzerlik_analizi():
    h = tum_haberler_benzerlik()
    if len(h) < 2: return 0
    m = [f"{x.get('baslik','')} {x.get('icerik','')}" for x in h]
    sim = cosine_similarity(TfidfVectorizer(max_features=5000, ngram_range=(1,2)).fit_transform(m))
    n, sil = 0, set()
    for i in range(len(h)):
        if i in sil: continue
        for j in range(i+1, len(h)):
            if j in sil: continue
            if sim[i][j] >= 0.90:
                birlestir(h[i]["_id"], h[j]["_id"], h[j].get("kaynak",""))
                sil.add(j); n += 1
    return n
