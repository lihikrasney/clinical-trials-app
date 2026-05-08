import streamlit as st
import pandas as pd
from google.cloud import bigquery
import plotly.express as px

# --- חיבור ל-BigQuery (מותאם גם לענן וגם למחשב האישי) ---
try:
    if "gcp_service_account" in st.secrets:
        # אם אנחנו בענן של סטרימליט
        info = dict(st.secrets["gcp_service_account"])
        client = bigquery.Client.from_service_account_info(info)
    else:
        # מצב גיבוי
        raise Exception("Secrets not found")
except Exception:
    # אם אנחנו מריצים מקומית על המחשב שלך ב-PyCharm
    KEY_FILE = "clinical-trials-project-495405-ef2da931c162.json"
    client = bigquery.Client.from_service_account_json(KEY_FILE)

# --- תפריט צד ---
st.sidebar.header("סינון לפי נושא")
# שיניתי ל-Alcoholism כדי שיתאים בדיוק למה שמופיע אצלך בטבלה
selected_topics = st.sidebar.multiselect(
    "בחרי נושאי מחקר:",
    options=["Obesity", "Alcoholism"],
    default=["Obesity", "Alcoholism"]
)


# --- משיכת נתונים ---
@st.cache_data(show_spinner=False)

def get_filtered_data(topics):
    if not topics:
        return pd.DataFrame()

    # שאילתה שמשתמשת בטור Category המדויק מהתמונה שלך
    query = f"""
    SELECT * FROM `clinical-trials-project-495405.clinical_trials_data.all_clinical_trials` 
    WHERE Category IN UNNEST({topics})
    LIMIT 2000
    """
    return client.query(query).to_dataframe()


df = get_filtered_data(selected_topics)

# --- תצוגה ---
#--- הגדרת יישור לימין (RTL) כולל כותרות ---
st.markdown("""
    <style>
    /* יישור כללי לטקסטים */
    .rtl-text, div[data-testid="stMarkdownContainer"] > p {
        direction: rtl;
        text-align: right;
    }
    
    /* יישור ספציפי לכותרות (h1, h2, h3) */
    h1, h2, h3 {
        direction: rtl;
        text-align: right;
    }

    /* התאמת כיוון לרשימות ונקודות (Bulleted lists) */
    ul {
        direction: rtl;
        text-align: right;
        padding-right: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- כותרת והסבר ---
st.title(" דשבורד ניסויים קליניים 🏥")

st.markdown(f"""
<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; direction: rtl; text-align: right;">
    הדשבורד מציג את כל הניסויים הקליניים שמתעסקים בתרופות להשמנה או אלכוהוליזם שמופיעים באתר <b>ClinicalTrials.gov</b> .<br>
    ניתן לבחור את תחום המחקר הרלוונטי בתפריט הצד, לעיין בנתונים הסטטיסטיים ולצפות בפרטים אודות המחקרים בתחתית הדף.
</div>
""", unsafe_allow_html=True)

st.write("")
st.divider()

if df.empty:
    st.warning("נא לבחור לפחות קטגוריה אחת בצד.")
else:
    # הצגת מדדים למעלה
    col1, col2 = st.columns(2)
    with col1:
        st.metric("סה\"כ ניסויים", len(df))
    with col2:
        st.metric("נושאים שנבחרו", ", ".join(selected_topics))

    st.divider()

    # יצירת הגרף - משתמש בטור Category
    # אנחנו סופרים כמה מופעים יש לכל ערך בטור Category
    category_counts = df['Category'].value_counts().reset_index()
    category_counts.columns = ['Category', 'Count']

    fig = px.bar(category_counts,
                 x='Category', y='Count',
                 color='Category',
                 color_discrete_map={'Obesity': '#FF4B4B', 'Alcoholism': '#1C83E1'},
                 title="התפלגות ניסויים לפי קטגוריה")

    st.plotly_chart(fig, use_container_width=True)

    # הצגת הטבלה מתחת
    st.subheader("נתונים מפורטים")
    st.dataframe(df, use_container_width=True)