import streamlit as st
import sqlite3
import pandas as pd
import os

# Ayarlar ve Veritabanı Yolu
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
    tab1, tab2, tab3, tab4 = st.tabs(["Yeni Kayıt", "Liste / Borç", "Bilgi Düzenle", "Öğrenci Sil"])
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
        if not df.empty:
            df['Kalan Borç'] = df['toplam_ucret'] - df['odenen_ucret']
            st.dataframe(df, use_container_width=True)
        conn.close()
    with tab3:
        conn = get_conn()
        df = pd.read_sql_query("SELECT * FROM ogrenciler", conn)
        if not df.empty:
            secili = st.selectbox("Düzenlenecek Öğrenci", df['ad_soyad'].tolist(), key="duz")
            data = df[df['ad_soyad'] == secili].iloc[0]
            with st.form("duz_form"):
                yeni_ad = st.text_input("Ad Soyad", value=data['ad_soyad'])
                if st.form_submit_button("Güncelle"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE ogrenciler SET ad_soyad=? WHERE id=?", (yeni_ad, data['id']))
                    conn.commit()
                    st.rerun()
        conn.close()
    with tab4:
        conn = get_conn()
        df = pd.read_sql_query("SELECT * FROM ogrenciler", conn)
        if not df.empty:
            secili = st.selectbox("Silinecek Öğrenci", df['ad_soyad'].tolist(), key="sil")
            if st.button("Öğrenciyi Sil"):
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ogrenciler WHERE ad_soyad=?", (secili,))
                conn.commit()
                st.rerun()
        conn.close()

def panel_gider_yonetimi():
    st.title("💸 Gider Yönetimi")
    tab1, tab2 = st.tabs(["Gider Ekle", "Gider Sil"])
    with tab1:
        with st.form("gider_form"):
            aciklama = st.text_input("Açıklama")
            tutar = st.number_input("Tutar", step=50.0)
            if st.form_submit_button("Kaydet"):
                conn = get_conn()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO kasa (tur, aciklama, tutar, tarih) VALUES ('Gider', ?, ?, date('now'))", (aciklama, tutar))
                conn.commit()
                conn.close()
                st.rerun()
    with tab2:
        conn = get_conn()
        df = pd.read_sql_query("SELECT * FROM kasa WHERE tur='Gider'", conn)
        if not df.empty:
            df['secenek'] = df['aciklama'] + " (" + df['tutar'].astype(str) + " ₺)"
            secili_str = st.selectbox("Silinecek Gider", df['secenek'].tolist(), key="gider_sil")
            if st.button("Seçili Gideri Sil"):
                secili_id = df[df['secenek'] == secili_str]['id'].iloc[0]
                cursor = conn.cursor()
                cursor.execute("DELETE FROM kasa WHERE id=?", (int(secili_id),))
                conn.commit()
                st.rerun()
        conn.close()

def panel_tahsilat():
    st.title("💵 Taksit Tahsilatı")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM ogrenciler", conn)
    if not df.empty:
        ogrenci_dict = {f"{r['ad_soyad']} (Borç: {r['toplam_ucret']-r['odenen_ucret']:.2f})": r['id'] for _, r in df.iterrows()}
        secim = st.selectbox("Öğrenci Seçin", list(ogrenci_dict.keys()))
        tutar = st.number_input("Tutar", step=100.0)
        if st.button("Kasaya İşle"):
            cursor = conn.cursor()
            cursor.execute("UPDATE ogrenciler SET odenen_ucret = odenen_ucret + ? WHERE id = ?", (tutar, ogrenci_dict[secim]))
            cursor.execute("INSERT INTO kasa (tur, aciklama, tutar, tarih) VALUES ('Gelir', ?, ?, date('now'))", (f"Tahsilat: {secim.split(' (')[0]}", tutar))
            conn.commit()
            st.rerun()
    conn.close()

def panel_rapor():
    st.title("📅 Aylık Finansal Analiz")
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM kasa", conn)
    conn.close()
    if not df.empty:
        df['tarih'] = pd.to_datetime(df['tarih'])
        ay = st.selectbox("Ay Seçin", range(1, 13))
        filtreli = df[df['tarih'].dt.month == ay]
        st.dataframe(filtreli, use_container_width=True)
        st.metric("Bu Ayın Toplam İşlemi", f"{filtreli['tutar'].sum():,.2f} ₺")

# --- NAVİGASYON ---
menu = st.sidebar.radio("Menü", ["Genel Özet", "Öğrenci İşlemleri", "Taksit Tahsilatı", "Gider Yönetimi", "Aylık Finansal Analiz"])
if menu == "Genel Özet": panel_dashboard()
elif menu == "Öğrenci İşlemleri": panel_ogrenci()
elif menu == "Taksit Tahsilatı": panel_tahsilat()
elif menu == "Gider Yönetimi": panel_gider_yonetimi()
elif menu == "Aylık Finansal Analiz": panel_rapor()