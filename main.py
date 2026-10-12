import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime


st.set_page_config(
    page_title="Hava Durumu Uygulaması",

)

st.title("Hava Durumu Uygulaması")
st.write("Bir şehir adı girerek 7 günlük hava tahminini öğren.")


def veritabani_olustur():
    with sqlite3.connect("hava_durumu.db") as baglanti:
        baglanti.execute("""
            CREATE TABLE IF NOT EXISTS sorgu_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sehir TEXT,
                sorgu_zamani TEXT,
                sicaklik REAL
            )
        """)

veritabani_olustur()


sehir = st.text_input(
    "Şehir adı girin:",
    placeholder="Örn. Sinop, Paris, Tokyo"
)

if st.button("Hava Durumunu Getir"):

    if not sehir.strip():
        st.warning("Lütfen bir şehir adı girin.")

    else:
        try:

            url = "https://geocoding-api.open-meteo.com/v1/search"

            parametreler = {
                "name": sehir.strip(),
                "count": 10,
                "language": "tr",
                "format": "json"
            }

            cevap = requests.get(
                url,
                params=parametreler,
                timeout=15
            )
            cevap.raise_for_status()
            veri = cevap.json()

            if not veri.get("results"):
                st.error("Şehir bulunamadı. Şehir adını kontrol edin.")

            else:

                sehir_bilgisi = veri["results"][0]

                enlem = sehir_bilgisi["latitude"]
                boylam = sehir_bilgisi["longitude"]
                sehir_adi = sehir_bilgisi["name"]

                st.subheader(f"{sehir_adi}")


                hava_url = "https://api.open-meteo.com/v1/forecast"

                hava_parametreleri = {
                    "latitude": enlem,
                    "longitude": boylam,
                    "daily": [
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "wind_speed_10m_max"
                    ],
                    "timezone": "auto",
                    "forecast_days": 7
                }

                hava_cevap = requests.get(
                    hava_url,
                    params=hava_parametreleri,
                    timeout=15
                )
                hava_cevap.raise_for_status()
                hava_verisi = hava_cevap.json()

                gunluk = hava_verisi["daily"]


                df = pd.DataFrame({
                    "Tarih": gunluk["time"],
                    "En Yüksek Sıcaklık (°C)": gunluk["temperature_2m_max"],
                    "En Düşük Sıcaklık (°C)": gunluk["temperature_2m_min"],
                    "Yağış Olasılığı (%)": gunluk["precipitation_probability_max"],
                    "Rüzgâr Hızı (km/sa)": gunluk["wind_speed_10m_max"]
                })

                st.subheader("📅 7 Günlük Hava Tahmini")
                st.dataframe(df, use_container_width=True)


                fig, ax = plt.subplots(figsize=(10, 5))

                ax.plot(
                    df["Tarih"],
                    df["En Yüksek Sıcaklık (°C)"],
                    marker="o",
                    label="En yüksek sıcaklık"
                )

                ax.plot(
                    df["Tarih"],
                    df["En Düşük Sıcaklık (°C)"],
                    marker="o",
                    label="En düşük sıcaklık"
                )

                ax.set_title(f"{sehir_adi} - 7 Günlük Sıcaklık")
                ax.set_xlabel("Tarih")
                ax.set_ylabel("Sıcaklık (°C)")
                ax.tick_params(axis="x", rotation=45)
                ax.legend()
                ax.grid(True)

                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)


                sicaklik = gunluk["temperature_2m_max"][0]
                sorgu_zamani = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                with sqlite3.connect("hava_durumu.db") as baglanti:
                    baglanti.execute("""
                        INSERT INTO sorgu_gecmisi
                        (sehir, sorgu_zamani, sicaklik)
                        VALUES (?, ?, ?)
                    """, (
                        sehir_adi,
                        sorgu_zamani,
                        sicaklik
                    ))

                st.success("Sorgu geçmişe kaydedildi.")

        except requests.exceptions.RequestException as hata:
            st.error(f"API bağlantı hatası: {hata}")

        except (KeyError, IndexError, TypeError) as hata:
            st.error(f"Veriler işlenirken hata oluştu: {hata}")

st.divider()
st.subheader(" Geçmiş Sorgular")

with sqlite3.connect("hava_durumu.db") as baglanti:
    df_gecmis = pd.read_sql_query(
        """
        SELECT id, sehir, sorgu_zamani, sicaklik
        FROM sorgu_gecmisi
        ORDER BY id DESC
        """,
        baglanti
    )

if df_gecmis.empty:
    st.info("Henüz sorgu geçmişi bulunmuyor.")
else:
    st.dataframe(df_gecmis, use_container_width=True)
