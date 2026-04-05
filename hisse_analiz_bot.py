"""
ABD Hisse Analiz Botu
Kullanim: python hisse_analiz_bot.py
"""

import yfinance as yf
import pandas as pd

# ─── AYARLAR ───────────────────────────────────────────────
HISSELER = ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA"]
PERIYOT   = "3mo"   # 3 aylik veri
ARALIK    = "1d"    # gunluk mum

RSI_PERIYOT     = 14
RSI_ASIRI_SATIS = 30   # altin: RSI < 30 -> AL sinyali
RSI_ASIRI_ALIM  = 70   # RSI > 70 -> SAT sinyali

MA_KISA  = 20
MA_UZUN  = 50
# ────────────────────────────────────────────────────────────


def rsi_hesapla(fiyat: pd.Series, periyot: int = 14) -> pd.Series:
    delta  = fiyat.diff()
    kazan  = delta.clip(lower=0).rolling(periyot).mean()
    kayip  = (-delta.clip(upper=0)).rolling(periyot).mean()
    rs     = kazan / kayip
    return 100 - (100 / (1 + rs))


def hisse_analiz_et(sembol: str) -> dict:
    """Tek bir hisseyi indir, analiz et ve sonucu sozluk olarak dondur."""
    df = yf.download(sembol, period=PERIYOT, interval=ARALIK,
                     progress=False, auto_adjust=True)

    if df.empty or len(df) < MA_UZUN:
        return {"sembol": sembol, "hata": "Yeterli veri yok"}

    kapat = df["Close"].squeeze()

    rsi     = rsi_hesapla(kapat, RSI_PERIYOT)
    ma_kisa = kapat.rolling(MA_KISA).mean()
    ma_uzun = kapat.rolling(MA_UZUN).mean()

    son_fiyat   = float(kapat.iloc[-1])
    son_rsi     = float(rsi.iloc[-1])
    son_ma_kisa = float(ma_kisa.iloc[-1])
    son_ma_uzun = float(ma_uzun.iloc[-1])

    # Hacim ortalamasi (son gun vs 20 gunluk ort)
    hacim       = df["Volume"].squeeze()
    hacim_oran  = float(hacim.iloc[-1] / hacim.rolling(20).mean().iloc[-1])

    # ── Sinyal mantigi ──────────────────────────────────────
    al_puan = sat_puan = 0

    # RSI
    if son_rsi < RSI_ASIRI_SATIS:
        al_puan += 2
    elif son_rsi > RSI_ASIRI_ALIM:
        sat_puan += 2

    # MA crossover
    if son_ma_kisa > son_ma_uzun:
        al_puan += 1
    else:
        sat_puan += 1

    # Fiyat MA iliskisi
    if son_fiyat > son_ma_kisa:
        al_puan += 1
    else:
        sat_puan += 1

    # Hacim guclendiricisi
    if hacim_oran > 1.5:
        if al_puan >= sat_puan:
            al_puan += 1
        else:
            sat_puan += 1

    # Karar
    if al_puan > sat_puan + 1:
        sinyal = "🟢 AL"
    elif sat_puan > al_puan + 1:
        sinyal = "🔴 SAT"
    else:
        sinyal = "🟡 BEKLE"

    return {
        "sembol":      sembol,
        "fiyat":       son_fiyat,
        "rsi":         round(son_rsi, 1),
        "ma20":        round(son_ma_kisa, 2),
        "ma50":        round(son_ma_uzun, 2),
        "hacim_oran":  round(hacim_oran, 2),
        "al_puan":     al_puan,
        "sat_puan":    sat_puan,
        "sinyal":      sinyal,
    }


def rapor_yazdir(sonuclar: list[dict]) -> None:
    print("\n" + "=" * 65)
    print("   📊  ABD HİSSE ANALİZ RAPORU")
    print("=" * 65)
    baslik = f"{'Sembol':<8} {'Fiyat':>8} {'RSI':>6} {'MA20':>8} {'MA50':>8} {'Hacim':>7}  Sinyal"
    print(baslik)
    print("-" * 65)

    for s in sonuclar:
        if "hata" in s:
            print(f"{s['sembol']:<8}  ⚠️  {s['hata']}")
            continue
        print(
            f"{s['sembol']:<8}"
            f" {s['fiyat']:>8.2f}"
            f" {s['rsi']:>6.1f}"
            f" {s['ma20']:>8.2f}"
            f" {s['ma50']:>8.2f}"
            f" {s['hacim_oran']:>6.2f}x"
            f"  {s['sinyal']}"
        )

    print("=" * 65)
    print("RSI < 30 → Aşırı Satış Bölgesi | RSI > 70 → Aşırı Alım Bölgesi")
    print("MA20 > MA50 → Yükseliş Trendi   | Hacim > 1.5x → Güçlü Hareket")
    print("=" * 65)
    print("⚠️  Bu analiz yatırım tavsiyesi değildir. Kendi araştırmanızı yapın.\n")


def main():
    print("\n⏳ Veriler indiriliyor, lütfen bekleyin...")
    sonuclar = [hisse_analiz_et(s) for s in HISSELER]
    rapor_yazdir(sonuclar)

    # Sadece AL sinyali verenleri ayir
    al_listesi = [s for s in sonuclar if "AL" in s.get("sinyal", "")]
    if al_listesi:
        print(f"💡 AL sinyali veren hisseler: {[s['sembol'] for s in al_listesi]}")
    else:
        print("💡 Şu an güçlü AL sinyali veren hisse yok.")


if __name__ == "__main__":
    main()
