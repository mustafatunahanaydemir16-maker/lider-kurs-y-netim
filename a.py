import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import date

# Uygulamanın olduğu klasörü otomatik bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lider_muhasebe_stabil.db")

st.set_page_config(page_title="Lider Kurs Yönetim", layout="wide")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS ogrenciler (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ad_soyad TEXT, telefon TEXT, 
        ehliyet_sinifi TEXT, toplam_ucret REAL, odenen_ucret REAL, kayit_tarihi TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS kasa (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tur TEXT, aciklama TEXT, 
        tutar REAL, tarih TEXT)""")
    conn.commit()
    conn.close()

init_db()

# --- PANEL FONKSİYONLARI ---

def panel_dashboard():
    st.title("📊 Genel Özet")
    conn = get_conn()
    df_kasa = pd.read_sql_query("SELECT * FROM kasa", conn)
    conn.close()
    gelir = df_kasa[df_kasa['tur'] == 'Gelir']['tutar'].sum() if not df_kasa.empty else 0
    gider = df_kasa[df_kasa['tur'] == 'Gider']['tutar'].sum() if not df_kasa.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Gelir", f"{gelir:,.2f} ₺")
    c2.metric("Toplam Gider", f"{gider:,.2f} ₺")
    c3.metric("Net Kâr", f"{gelir - gider:,.2f} ₺")

def panel_ogrenci():
    st.title("👥 Öğrenci İşlemleri")
    tab1, tab2 = st.tabs(["Yeni Kayıt", "Liste / Borç"])
    with tab1:
        with st.form("kayit"):
            ad = st.text_input("Ad Soyad")
            tel = st.text_input("Telefon")
            sinif = st.selectbox("Sınıf", ["A1", "A2", "B Manuel", "B Otomatik", "C"])
            ucret = st.number_input("Toplam Ücret", step=500.0)
            tarih = st.date_input("Kayıt Tarihi")
            if st.form_submit_button("Kaydet"):
                conn = get_conn()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO ogrenciler (ad_soyad, telefon, ehliyet_sinifi, toplam_ucret, odenen_ucret, kayit_tarihi) VALUES (?, ?, ?, ?, 0.0, ?)", (ad, tel, sinif, ucret, str(tarih)))
                conn.commit()
                conn.close()
                st.rerun()
    with tab2:
        conn = get_conn()
        df = pd.read_sql_query("SELECT * FROM ogrenciler", conn)
        conn.close()
        if not df.empty:
            df['Kalan Borç'] = df['toplam_ucret'] - df['odenen_ucret']
            st.dataframe(df, use_container_width=True)

def panel_tahsilat():
    st.title("💵 Taksit Tahsilatı")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM ogrenciler", conn)
    if not df.empty:
        ogrenci_dict = {f"{r['ad_soyad']} (Borç: {r['toplam_ucret']-r['odenen_ucret']:.2f})": r['id'] for _, r in df.iterrows()}
        secim = st.selectbox("Öğrenci Seçin", list(ogrenci_dict.keys()))
        tutar = st.number_input("Tutar", step=100.0)
        tarih = st.date_input("Ödeme Tarihi")
        if st.button("Kasaya İşle"):
            cursor = conn.cursor()
            cursor.execute("UPDATE ogrenciler SET odenen_ucret = odenen_ucret + ? WHERE id = ?", (tutar, ogrenci_dict[secim]))
            cursor.execute("INSERT INTO kasa (tur, aciklama, tutar, tarih) VALUES ('Gelir', ?, ?, ?)", (f"Tahsilat: {secim.split(' (')[0]}", tutar, str(tarih)))
            conn.commit()
            conn.close()
            st.rerun()
    conn.close()

def panel_gider():
    st.title("💸 Gider Girişi")
    with st.form("gider_formu"):
        aciklama = st.text_input("Açıklama")
        tutar = st.number_input("Tutar", step=50.0)
        tarih = st.date_input("Tarih")
        if st.form_submit_button("Gideri Kaydet"):
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO kasa (tur, aciklama, tutar, tarih) VALUES ('Gider', ?, ?, ?)", (aciklama, tutar, str(tarih)))
            conn.commit()
            conn.close()
            st.rerun()

def panel_rapor():
    st.title("📅 Aylık Finansal Özet")
    conn = get_conn()
    df_kasa = pd.read_sql_query("SELECT * FROM kasa", conn)
    conn.close()
    if not df_kasa.empty:
        df_kasa['tarih'] = pd.to_datetime(df_kasa['tarih'])
        ay = st.selectbox("Ay Seçin", range(1, 13))
        filtreli = df_kasa[df_kasa['tarih'].dt.month == ay]
        gelir = filtreli[filtreli['tur']=='Gelir']['tutar'].sum()
        gider = filtreli[filtreli['tur']=='Gider']['tutar'].sum()
        st.metric("Net Kar", f"{gelir - gider:,.2f} ₺")
        st.dataframe(filtreli, use_container_width=True)

# Navigasyon
menu = st.sidebar.radio("Menü", ["Genel Özet", "Öğrenci İşlemleri", "Taksit Tahsilatı", "Gider Ekle", "Aylık Finansal Özet"])
if menu == "Genel Özet": panel_dashboard()
elif menu == "Öğrenci İşlemleri": panel_ogrenci()
elif menu == "Taksit Tahsilatı": panel_tahsilat()
elif menu == "Gider Ekle": panel_gider()
elif menu == "Aylık Finansal Özet": panel_rapor()