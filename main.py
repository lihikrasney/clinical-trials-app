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
    /* יישור כללי לימין לכל האתר */
    .main {
        direction: rtl;
        text-align: right;
    }

    /* תיקון המטריקות - שיעמדו יפה בימין */
    [data-testid="stMetric"] {
        direction: rtl;
        text-align: right;
        width: fit-content !important;
        margin-right: 0 !important;
        margin-left: auto !important;
    }

    /* הצמדת הכותרת למספר */
    [data-testid="stMetricLabel"] {
        display: flex;
        justify-content: flex-start;
        width: 100%;
    }

    /* הגדלת המספר שיהיה ברור */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        width: 100%;
        text-align: right;
    }

    /* יישור כותרות וגרפים */
    h1, h2, h3, p {
        direction: rtl;
        text-align: right;
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

    # 2. בחירת שלב הניסוי (Phase)
    # ננקה ערכים ריקים ונסדר אותם
    phase_list = sorted(df['Phase'].dropna().unique())
    selected_phases = st.sidebar.multiselect("בחרי שלב ניסוי (Phase):", phase_list)

    # 3. בחירת ספונסור
    sponsor_list = sorted(df['Sponsor'].dropna().unique())
    selected_sponsors = st.sidebar.multiselect("בחרי ספונסור:", sponsor_list)

    # 4. בחירת טווח תאריכים
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

    if selected_phases:
        filtered_df = filtered_df[filtered_df['Phase'].isin(selected_phases)]

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

    # ג. ויזואליזציה (כמות ניסויים פסיכואקטיביים)
    st.divider()
    st.subheader("ניתוח ניסויים פסיכואקטיביים (Neuro-Plastic)")

    # ג1. חישוב הנתונים והגדרת ה"מסננת" (is_neuro)
    neuro_col = 'Is_Neuro_Plastic'
    total_trials = len(filtered_df)

    # יצירת המשתנה שבודק מי "כן" - זה ה-is_neuro שחיפשנו
    is_neuro = filtered_df[neuro_col].isin([True, 1])
    neuro_count = len(filtered_df[is_neuro])
    neuro_percentage = (neuro_count / total_trials * 100) if total_trials > 0 else 0

    # ג2. תצוגה של המדדים והגרף
    col_m1, col_m2, col_m3 = st.columns([1, 1, 2])  # שיניתי קצת יחס כדי שיהיה מקום לגרף

    with col_m1:
        st.metric("סה\"כ פסיכואקטיביים", f"{neuro_count}")

    with col_m2:
        st.metric("אחוז פסיכואקטיביים מתוך כלל הניסויים", f"{neuro_percentage:.1f}%")

    with col_m3:
        neuro_dist = filtered_df[neuro_col].astype(str).value_counts().reset_index()
        neuro_dist.columns = ['Status', 'Count']
        fig_neuro = px.bar(neuro_dist, x='Status', y='Count',
                           title="התפלגות פסיכואקטיבי",
                           color='Status',
                           height=200)
        fig_neuro.update_layout(title_x=1, title_xanchor='right', showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_neuro, use_container_width=True)

    # ג3. הוספת הרשימה המפורטת מתחת (השתמשנו ב-is_neuro שהגדרנו למעלה)
    st.write("---")  # קו מפריד עדין
    with st.expander(f"🔍 רשימת {neuro_count} הניסויים הפסיכואקטיביים"):
        # סינון הטבלה והצגת עמודות ספציפיות
        # ודאי ששמות העמודות כאן (Study Title, Sponsor, Phase) זהים למה שיש ב-BigQuery
        neuro_list = filtered_df[is_neuro][['Study Title', 'Sponsor', 'Phase']]

        # עיצוב הטבלה למשתמש
        st.dataframe(
            neuro_list.rename(columns={
                'Study Title': 'שם הניסוי',
                'Sponsor': 'ספונסר',
                'Phase': 'שלב (Phase)'
            }),
            use_container_width=True,
            hide_index=True
        )

    # ד1. ויזואליזציה (גרף עוגה של חלוקה לפי פייז) בצד שמאל של האתר
    st.divider()

    # יצירת שתי עמודות לגרפים החדשים
    col_left, col_right = st.columns(2)

    with col_left:
        # גרף עוגה/דונאט של השלבים (Phases)
        phase_counts = filtered_df['Phase'].value_counts().reset_index()
        phase_counts.columns = ['Phase', 'Count']

        fig_phase = px.pie(phase_counts,
                           values='Count',
                           names='Phase',
                           title="התפלגות לפי שלב הניסוי (Phase)",
                           hole=0.4)
        fig_phase.update_layout(title_x=1, title_xanchor='right')
        st.plotly_chart(fig_phase, use_container_width=True)

    # ד2. ויזואליזציה (גרף עמודות של חלוקה לפי סטטוס) בצד ימין של האתר
    with col_right:
        # גרף עמודות אופקי של סטטוס הניסויים
        status_counts = filtered_df['Study Status'].value_counts().reset_index()
        status_counts.columns = ['Study Status', 'Count']

        fig_status = px.bar(status_counts,
                            x='Count',
                            y='Study Status',
                            orientation='h',
                            title="מצב הניסויים (Study Status)",
                            color='Study Status')
        fig_status.update_layout(title_x=1, title_xanchor='right')
        st.plotly_chart(fig_status, use_container_width=True)

    # ה. טבלת נתונים מפורטת
    st.subheader("נתונים מפורטים")
    st.dataframe(filtered_df, use_container_width=True)