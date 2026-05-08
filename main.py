import streamlit as st
import pandas as pd
from google.cloud import bigquery
import plotly.express as px

# ==========================================
# 1. הגדרות דף ועיצוב (RTL & Config)
# ==========================================
st.set_page_config(page_title="Clinical Trials Dashboard", layout="wide")

st.markdown("""
    <style>
    /* יישור כללי לימין */
    .rtl-text, div[data-testid="stMarkdownContainer"] > p, h1, h2, h3 {
        direction: rtl;
        text-align: right;
    }
    /* התאמת רשימות */
    ul {
        direction: rtl;
        text-align: right;
        padding-right: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. ניהול חיבור ו-Secrets (BigQuery)
# ==========================================
try:
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        client = bigquery.Client.from_service_account_info(info)
    else:
        raise Exception("Secrets not found")
except Exception:
    KEY_FILE = "clinical-trials-project-495405-ef2da931c162.json"
    client = bigquery.Client.from_service_account_json(KEY_FILE)

# ==========================================
# 3. פונקציית משיכת נתונים (Cache)
# ==========================================
@st.cache_data(show_spinner=False)
def get_filtered_data(topics):
    if not topics:
        return pd.DataFrame()

    query = f"""
    SELECT * FROM `clinical-trials-project-495405.clinical_trials_data.all_clinical_trials` 
    WHERE Category IN UNNEST({topics})
    LIMIT 2000
    """
    return client.query(query).to_dataframe()

# ==========================================
# 4. תפריט צד (Sidebar) - שלב א': בחירת נושא
# ==========================================
st.sidebar.header("סינון לפי נושא")

selected_topics = st.sidebar.multiselect(
    "בחרי נושאי מחקר:",
    options=["Obesity", "Alcoholism"],
    default=["Obesity", "Alcoholism"]
)

# משיכת הנתונים הראשונית
df = get_filtered_data(selected_topics)

# ==========================================
# 5. תפריט צד (Sidebar) - שלב ב': פילטרים מתקדמים
# ==========================================
if not df.empty:
    st.sidebar.divider()

    # 1. חיפוש חופשי
    search_term = st.sidebar.text_input("חיפוש מילה בכותרת המחקר:", "")

    # 2. בחירת ספונסור
    sponsor_list = sorted(df['Sponsor'].dropna().unique())
    selected_sponsors = st.sidebar.multiselect("בחרי ספונסור:", sponsor_list)

    # 3. בחירת טווח תאריכים
    df['Last Update Posted'] = pd.to_datetime(df['Last Update Posted'])
    first_date = df['Last Update Posted'].min().date()
    last_date = df['Last Update Posted'].max().date()

    user_date_range = st.sidebar.date_input(
        "טווח תאריכי עדכון אחרון:",
        value=(first_date, last_date),
        min_value=first_date,
        max_value=last_date
    )

    # --- לוגיקת סינון הנתונים (filtered_df) ---
    filtered_df = df.copy()

    if search_term:
        filtered_df = filtered_df[filtered_df['Study Title'].str.contains(search_term, case=False, na=False)]

    if selected_sponsors:
        filtered_df = filtered_df[filtered_df['Sponsor'].isin(selected_sponsors)]

    if isinstance(user_date_range, tuple) and len(user_date_range) == 2:
        start, end = user_date_range
        filtered_df = filtered_df[
            (filtered_df['Last Update Posted'].dt.date >= start) &
            (filtered_df['Last Update Posted'].dt.date <= end)
            ]
else:
    filtered_df = df.copy()

# ==========================================
# 6. תצוגת תוכן מרכזית (UI)
# ==========================================
st.title(" דשבורד ניסויים קליניים 🏥")

# תיבת הסבר
st.markdown(f"""
<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; direction: rtl; text-align: right;">
    הדשבורד מציג את כל הניסויים הקליניים שמתעסקים בתרופות להשמנה או אלכוהוליזם שמופיעים באתר <b>ClinicalTrials.gov</b> .<br>
    ניתן לבחור את תחום המחקר הרלוונטי בתפריט הצד, לעיין בנתונים הסטטיסטיים ולצפות בפרטים אודות המחקרים בתחתית הדף.
</div>
""", unsafe_allow_html=True)

st.write("")
st.divider()

# בדיקה אם יש נתונים להצגה
if filtered_df.empty:
    st.warning("נא לבחור לפחות קטגוריה אחת בצד.")
else:
    # א. שורת מדדים (KPIs)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("סה\"כ ניסויים", len(filtered_df))
    with col2:
        st.metric("נושאים שנבחרו", ", ".join(selected_topics))

    st.divider()

    # ב. ויזואליזציה (גרף עמודות)
    category_counts = filtered_df['Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']

    fig = px.bar(category_counts,
                 x='Category', y='Count',
                 color='Category',
                 color_discrete_map={'Obesity': '#FF4B4B', 'Alcoholism': '#1C83E1'},
                 title="התפלגות ניסויים לפי קטגוריה")

    st.plotly_chart(fig, use_container_width=True)

    # ג. טבלת נתונים מפורטת
    st.subheader("נתונים מפורטים")
    st.dataframe(filtered_df, use_container_width=True)