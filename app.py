"""
Kocaeli Yerel Haber Harita Sistemi
Tkinter + tkintermapview
"""
import sys, os, threading, webbrowser
from datetime import datetime, timedelta
from tkinter import *
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, haberleri_getir, haber_sayisi, ilceleri_getir
from scraper import tum_kaynaklari_tara
from similarity import benzerlik_analizi
from classifier import RENKLER, EMOJILER, ONCELIK

try:
    import tkintermapview
except ImportError:
    print("pip install tkintermapview"); sys.exit(1)

BG="#1e1e2e"; SIDEBAR="#2b2b3d"; CARD="#363650"; ACCENT="#7c3aed"
TEXT="#e2e8f0"; DIM="#94a3b8"; BORDER="#4a4a6a"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Kocaeli Yerel Haber Haritası")
        self.root.geometry("1400x800")
        self.root.minsize(1000, 600)
        self.root.configure(bg=BG)

        self.haberler = []
        self.markers = []
        self.secili_tur = StringVar(value="Tümü")
        self.secili_ilce = StringVar(value="Tümü")
        self.secili_gun = StringVar(value="Son 3 gün")
        self.scraping = False

        try:
            init_db()
        except Exception as e:
            messagebox.showerror("MongoDB", f"Bağlantı yok!\n{e}")

        self._ui()
        self.root.after(500, self.yukle)

    def _ui(self):
        # UST BAR
        top = Frame(self.root, bg=ACCENT, height=50)
        top.pack(fill=X, side=TOP); top.pack_propagate(False)

        Label(top, text="📍 Kocaeli Yerel Haber Haritası",
              font=("Segoe UI",14,"bold"), bg=ACCENT, fg="white").pack(side=LEFT, padx=15)

        self.lbl_count = Label(top, text="0 haber", font=("Segoe UI",10), bg=ACCENT, fg="#ddd")
        self.lbl_count.pack(side=RIGHT, padx=15)

        # Scrape gun secimi + buton
        scrape_frame = Frame(top, bg=ACCENT)
        scrape_frame.pack(side=RIGHT, padx=5, pady=8)

        self.scrape_gun = StringVar(value="3")
        for val, txt in [("1","1 gün"), ("2","2 gün"), ("3","3 gün")]:
            Radiobutton(scrape_frame, text=txt, variable=self.scrape_gun, value=val,
                       font=("Segoe UI",9), bg=ACCENT, fg="white", selectcolor="#5b21b6",
                       activebackground=ACCENT, activeforeground="white",
                       indicatoron=0, padx=8, pady=3, relief="flat",
                       ).pack(side=LEFT, padx=1)

        self.btn_scrape = Button(scrape_frame, text="🔄 Haberleri Çek",
            font=("Segoe UI",10,"bold"), bg="#5b21b6", fg="white", relief="flat",
            padx=12, command=self.scrape_baslat)
        self.btn_scrape.pack(side=LEFT, padx=(8,0))

        # ANA
        main = Frame(self.root, bg=BG)
        main.pack(fill=BOTH, expand=True)

        # SOL PANEL
        left = Frame(main, bg=SIDEBAR, width=310)
        left.pack(side=LEFT, fill=Y); left.pack_propagate(False)
        inner = Frame(left, bg=SIDEBAR)
        inner.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # FILTRELER
        Label(inner, text="🔍 Filtreler", font=("Segoe UI",11,"bold"),
              bg=SIDEBAR, fg=TEXT).pack(anchor=W, pady=(5,5))

        fbox = Frame(inner, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        fbox.pack(fill=X, pady=(0,10))
        fc = Frame(fbox, bg=CARD); fc.pack(fill=X, padx=12, pady=12)

        # Haber Turu
        Label(fc, text="Haber Türü", font=("Segoe UI",9,"bold"), bg=CARD, fg=DIM).pack(anchor=W)
        om = OptionMenu(fc, self.secili_tur, *["Tümü"]+ONCELIK)
        om.config(font=("Segoe UI",10), bg=BG, fg=TEXT, activebackground=ACCENT,
                  highlightthickness=0, relief="flat")
        om["menu"].config(bg=BG, fg=TEXT)
        om.pack(fill=X, pady=(2,8))

        # Ilce
        Label(fc, text="İlçe", font=("Segoe UI",9,"bold"), bg=CARD, fg=DIM).pack(anchor=W)
        self.ilce_om = OptionMenu(fc, self.secili_ilce, "Tümü")
        self.ilce_om.config(font=("Segoe UI",10), bg=BG, fg=TEXT, activebackground=ACCENT,
                           highlightthickness=0, relief="flat")
        self.ilce_om["menu"].config(bg=BG, fg=TEXT)
        self.ilce_om.pack(fill=X, pady=(2,8))

        # Gun secimi (gosterim icin)
        Label(fc, text="Zaman Aralığı", font=("Segoe UI",9,"bold"), bg=CARD, fg=DIM).pack(anchor=W)
        gun_frame = Frame(fc, bg=CARD)
        gun_frame.pack(fill=X, pady=(2,8))
        for val, txt in [("Son 1 gün","1 Gün"), ("Son 2 gün","2 Gün"), ("Son 3 gün","3 Gün")]:
            Radiobutton(gun_frame, text=txt, variable=self.secili_gun, value=val,
                       font=("Segoe UI",9), bg=CARD, fg=TEXT, selectcolor=ACCENT,
                       activebackground=CARD, activeforeground=TEXT,
                       indicatoron=0, padx=10, pady=4, relief="flat",
                       ).pack(side=LEFT, padx=2)

        Button(fc, text="🔎 Filtrele", font=("Segoe UI",10,"bold"), bg=ACCENT, fg="white",
               relief="flat", command=self.filtrele).pack(fill=X, pady=2)
        Button(fc, text="✖ Temizle", font=("Segoe UI",10), bg=BORDER, fg="white",
               relief="flat", command=self.temizle).pack(fill=X, pady=2)

        # LEJANT
        Label(inner, text="🎨 Lejant", font=("Segoe UI",11,"bold"),
              bg=SIDEBAR, fg=TEXT).pack(anchor=W, pady=(8,5))
        lbox = Frame(inner, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        lbox.pack(fill=X, pady=(0,10))
        lc = Frame(lbox, bg=CARD); lc.pack(fill=X, padx=12, pady=10)
        for tur in ONCELIK:
            row = Frame(lc, bg=CARD); row.pack(fill=X, pady=2)
            c = Frame(row, bg=RENKLER[tur], width=14, height=14,
                      highlightbackground="#fff", highlightthickness=1)
            c.pack(side=LEFT, padx=(0,8)); c.pack_propagate(False)
            Label(row, text=f"{EMOJILER[tur]} {tur}", font=("Segoe UI",9),
                  bg=CARD, fg=TEXT).pack(side=LEFT)

        # ISTATISTIK
        Label(inner, text="📊 İstatistikler", font=("Segoe UI",11,"bold"),
              bg=SIDEBAR, fg=TEXT).pack(anchor=W, pady=(8,5))
        sbox = Frame(inner, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        sbox.pack(fill=X, pady=(0,10))
        self.lbl_stats = Label(sbox, text="Yükleniyor...", font=("Segoe UI",9),
            bg=CARD, fg=DIM, justify=LEFT, anchor=W)
        self.lbl_stats.pack(fill=X, padx=12, pady=10)

        # HABER LISTESI
        Label(inner, text="📰 Haberler", font=("Segoe UI",11,"bold"),
              bg=SIDEBAR, fg=TEXT).pack(anchor=W, pady=(8,5))
        hbox = Frame(inner, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        hbox.pack(fill=BOTH, expand=True)
        self.haber_text = Text(hbox, font=("Segoe UI",9), bg=BG, fg=TEXT, wrap=WORD,
            relief="flat", state=DISABLED, highlightthickness=0, padx=8, pady=8)
        sb = Scrollbar(hbox, command=self.haber_text.yview)
        self.haber_text.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        self.haber_text.pack(fill=BOTH, expand=True)

        # HARITA
        mf = Frame(main, bg=BG); mf.pack(side=RIGHT, fill=BOTH, expand=True)
        self.harita = tkintermapview.TkinterMapView(mf, corner_radius=0)
        self.harita.pack(fill=BOTH, expand=True)
        self.harita.set_position(40.7654, 29.9408)
        self.harita.set_zoom(11)
        self.harita.set_tile_server(
            "https://mt0.google.com/vt/lyrs=m&hl=tr&x={x}&y={y}&z={z}&s=Ga", max_zoom=19)

        # ALT BAR
        bot = Frame(self.root, bg=CARD, height=28)
        bot.pack(fill=X, side=BOTTOM); bot.pack_propagate(False)
        self.lbl_status = Label(bot, text="Hazır", font=("Segoe UI",9), bg=CARD, fg=DIM)
        self.lbl_status.pack(side=LEFT, padx=10)
        self.lbl_progress = Label(bot, text="", font=("Segoe UI",9), bg=CARD, fg=ACCENT)
        self.lbl_progress.pack(side=RIGHT, padx=10)

    # ==============================================================
    def _gun_sayisi_filtre(self):
        """Secili gun degerinden gun sayisi dondur."""
        g = self.secili_gun.get()
        if "1" in g: return 1
        if "2" in g: return 2
        return 3

    def yukle(self, filtreler=None):
        self.status("Yükleniyor...")
        try:
            if filtreler is None:
                filtreler = {}
            # Gun filtresi ekle
            if "baslangic" not in filtreler:
                gun = self._gun_sayisi_filtre()
                filtreler["baslangic"] = datetime.now() - timedelta(days=gun)
                filtreler["bitis"] = datetime.now()

            self.haberler = haberleri_getir(filtreler)
            self.harita_guncelle()
            self.liste_guncelle()
            self.stats_guncelle()
            self.ilce_guncelle()
            self.lbl_count.config(text=f"{len(self.haberler)} haber")
            self.status(f"{len(self.haberler)} haber gösteriliyor.")
        except Exception as e:
            self.status(f"Hata: {e}")

    def harita_guncelle(self):
        for m in self.markers: m.delete()
        self.markers.clear()
        for h in self.haberler:
            lat, lng = h.get("enlem"), h.get("boylam")
            if not lat or not lng: continue
            tur = h.get("haber_turu", "")
            renk = RENKLER.get(tur, "#999")
            emoji = EMOJILER.get(tur, "📌")
            baslik_kisa = h.get("baslik","")[:30]
            m = self.harita.set_marker(lat, lng,
                text=f"{emoji} {baslik_kisa}",
                marker_color_circle=renk, marker_color_outside=renk,
                text_color=renk,
                font=("Segoe UI", 8, "bold"),
                command=None)
            self.markers.append(m)

    def liste_guncelle(self):
        self.haber_text.config(state=NORMAL)
        self.haber_text.delete("1.0", END)
        if not self.haberler:
            self.haber_text.insert(END, "Haber yok.\n\n'Haberleri Çek' ile\nhaber toplayın.")
        else:
            for h in self.haberler[:50]:
                e = EMOJILER.get(h.get("haber_turu",""),"📌")
                self.haber_text.insert(END,
                    f"{e} {h.get('baslik','')[:50]}\n"
                    f"  📅 {h.get('yayin_tarihi','')} | 🏢 {h.get('kaynak','')}\n"
                    f"{'─'*38}\n")
            if len(self.haberler)>50:
                self.haber_text.insert(END, f"\n+{len(self.haberler)-50} haber daha...")
        self.haber_text.config(state=DISABLED)

    def stats_guncelle(self):
        try:
            s = {}
            for h in self.haberler:
                t = h.get("haber_turu","?"); s[t] = s.get(t,0)+1
            txt = f"DB toplam: {haber_sayisi()} | Gösterilen: {len(self.haberler)}\n\n"
            for t in ONCELIK:
                txt += f"{EMOJILER[t]} {t}: {s.get(t,0)}\n"
            self.lbl_stats.config(text=txt)
        except: pass

    def ilce_guncelle(self):
        try:
            il = ["Tümü"] + ilceleri_getir()
            m = self.ilce_om["menu"]; m.delete(0,"end")
            for i in il: m.add_command(label=i, command=lambda x=i: self.secili_ilce.set(x))
        except: pass

    # FILTRELEME
    def filtrele(self):
        f = {}
        tur = self.secili_tur.get()
        if tur != "Tümü": f["haber_turu"] = tur
        ilce = self.secili_ilce.get()
        if ilce != "Tümü": f["ilce"] = ilce
        gun = self._gun_sayisi_filtre()
        f["baslangic"] = datetime.now() - timedelta(days=gun)
        f["bitis"] = datetime.now()
        self.yukle(f)

    def temizle(self):
        self.secili_tur.set("Tümü")
        self.secili_ilce.set("Tümü")
        self.secili_gun.set("Son 3 gün")
        self.yukle()

    # SCRAPING
    def scrape_baslat(self):
        if self.scraping: return
        self.scraping = True
        gun = int(self.scrape_gun.get())
        self.btn_scrape.config(state=DISABLED, text="⏳ Çekiliyor...")
        self.status(f"Son {gun} gün haberleri çekiliyor...")

        def worker():
            try:
                def cb(kaynak, mevcut, toplam_link, bulunan):
                    self.root.after(0, lambda: self.lbl_progress.config(
                        text=f"{kaynak}: {mevcut}/{toplam_link} | {bulunan} haber"))

                n = tum_kaynaklari_tara(gun_sayisi=gun, callback=cb)
                self.root.after(0, lambda: self.status("Benzerlik analizi..."))
                b = benzerlik_analizi()

                def bitti():
                    self.scraping = False
                    self.btn_scrape.config(state=NORMAL, text="🔄 Haberleri Çek")
                    self.lbl_progress.config(text="")
                    self.yukle()
                    messagebox.showinfo("Tamam", f"✅ {n} haber çekildi\n🔗 {b} benzer birleşti")
                self.root.after(0, bitti)
            except Exception as e:
                def err():
                    self.scraping = False
                    self.btn_scrape.config(state=NORMAL, text="🔄 Haberleri Çek")
                    self.status(f"Hata: {e}")
                self.root.after(0, err)

        threading.Thread(target=worker, daemon=True).start()

    def status(self, t):
        self.lbl_status.config(text=t)


def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = Tk()
    app = App(root)

    def kapanista():
        from database import veritabanini_temizle
        veritabanini_temizle()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", kapanista)
    root.mainloop()

if __name__ == "__main__":
    main()
