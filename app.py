# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import random
import time

# ---------------- Load API key ----------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or (st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else None)
if not GOOGLE_API_KEY:
    st.warning("Google API key not found. Set GOOGLE_API_KEY in environment or Streamlit secrets.")
genai.configure(api_key=GOOGLE_API_KEY)

# ---------------- Config ----------------
MOOD_FILE = "mood_log.csv"

CRISIS_KEYWORDS = [
    "suicide","kill myself","end my life","i want to die","give up","self harm",
    "hurt myself","i cant go on","i can't go on","i'm going to kill myself"
]

HELPLINES = {
    "India": {
        "AASRA": "91-98204 66726",
        "Vandrevala Foundation Helpline": "1860 266 2345 or 1800 233 3330",
        "Snehi": "91-9582208181"
    },
    "USA": {"National Suicide Prevention Lifeline": "988"},
    "UK": {"Samaritans": "116 123"}
}

LANGUAGES = {"English":"en", "Hindi":"hi", "Telugu":"te"}

AFFIRMATIONS = [
    "🌟 You are stronger than you think.",
    "💪 Every day is a fresh start.",
    "🌈 You are doing your best, and that’s enough.",
    "☀️ Believe in yourself—you’ve got this!",
    "💖 You matter, and your feelings are valid."
]

QUOTES = [
    "💡 You don’t have to control your thoughts. You just have to stop letting them control you. – Dan Millman",
    "💡 Self-care is not a luxury, it’s a necessity.",
    "💡 This too shall pass.",
    "💡 Healing takes time, and asking for help is a courageous step.",
]

# ---------------- Functions ----------------
def generate_response(user_text, lang="English"):
    if not GOOGLE_API_KEY:
        return "Google API key not configured."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        if lang != "English":
            user_text = translate(user_text, lang)
        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)
        output = response.text
        if lang != "English":
            output = translate(output, lang)
        return output
    except Exception as e:
        return f"⚠️ Google API error: {str(e)}"

def translate(text, target_lang):
    try:
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
            f"Translate this text to {target_lang}: {text}"
        )
        return response.text
    except Exception:
        return text

def is_crisis(text):
    if not text:
        return False
    t = text.lower()
    return any(kw in t for kw in CRISIS_KEYWORDS)

def save_mood(mood, note=""):
    entry = {
        "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": date.today().isoformat(),
        "mood": mood,
        "note": note
    }
    if os.path.exists(MOOD_FILE):
        df = pd.read_csv(MOOD_FILE)
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    else:
        df = pd.DataFrame([entry])
    df.to_csv(MOOD_FILE, index=False)

def load_moods():
    if os.path.exists(MOOD_FILE):
        return pd.read_csv(MOOD_FILE)
    return pd.DataFrame(columns=["date_time","date","mood","note"])

def calculate_streak():
    df = load_moods()
    if df.empty:
        return 0
    df["date"] = pd.to_datetime(df["date"]).dt.date
    unique_dates = sorted(set(df["date"]), reverse=True)
    streak = 0
    today = date.today()
    for i, d in enumerate(unique_dates):
        expected = today - timedelta(days=i)
        if d == expected:
            streak += 1
        else:
            break
    return streak

def get_coping_tip_for(mood):
    tips = {
        "😃 Happy": "Nice! Share that positivity — text a friend or write a gratitude note.",
        "😢 Sad": "Try writing down your feelings for 5 minutes to release them.",
        "😰 Anxious": "Do a 2-min breathing exercise: 4s inhale, 4s hold, 6s exhale.",
        "😡 Angry": "Take a short walk, then write what made you angry in one sentence.",
        "😓 Stressed": "Break tasks into small steps, and stretch for 2 minutes."
    }
    return tips.get(mood, "Take a few deep breaths — you’re doing your best. 💙")

def plot_wordcloud(notes):
    if not notes:
        return None
    text = " ".join(notes)
    wc = WordCloud(width=800, height=400, background_color="white").generate(text)
    fig, ax = plt.subplots()
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig

def wellness_score(df):
    if df.empty:
        return 50
    score_map = {"😃 Happy": 2, "😢 Sad": -1, "😰 Anxious": -1, "😡 Angry": -2, "😓 Stressed": -1}
    score = df["mood"].map(score_map).sum() + 50
    return max(0, min(100, score))

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Mindsight — Youth Mental Wellness", page_icon="🧠", layout="wide")

st.title("🧠 Mindsight — Youth Mental Wellness")
st.caption("AI-powered companion for daily mental wellness tracking, support, and reflection.")

user_lang = st.selectbox("🌍 Choose your language", list(LANGUAGES.keys()))

# --- Tabs for better UI ---
tabs = st.tabs(["💬 Chat", "📓 Mood Logger", "📊 Insights", "📖 Journaling", "🧘 Exercises"])

# --- Chat ---
with tabs[0]:
    st.subheader("💬 Chat with Mindsight")
    user_text = st.text_area("Talk to Mindsight", max_chars=1000, key="chat_input")
    if st.button("Send", key="send"):
        if is_crisis(user_text):
            st.error("🚨 Crisis language detected! Contact local emergency services immediately.")
            st.info("India helpline: " + ", ".join([f"{k}: {v}" for k,v in HELPLINES["India"].items()]))
        else:
            with st.spinner("Thinking..."):
                reply = generate_response(user_text, lang=user_lang)
            st.markdown("**Mindsight:**")
            st.write(reply)

# --- Mood Logger ---
with tabs[1]:
    st.subheader("📓 Log Your Mood")
    mood = st.radio("How are you feeling?", ["😃 Happy","😢 Sad","😰 Anxious","😡 Angry","😓 Stressed"])
    note = st.text_area("Optional note (private)", key="note")
    anon_mode = st.checkbox("🔒 Anonymous Mode (don’t save moods)")
    if st.button("Log Mood", key="log"):
        if not anon_mode:
            save_mood(mood, note)
            st.success(f"Saved mood: {mood}")
        else:
            st.info("Mood logged in session only (not saved).")
        st.info(get_coping_tip_for(mood))
        st.success(random.choice(AFFIRMATIONS))

# --- Insights ---
with tabs[2]:
    st.subheader("📊 Your Insights")
    df = load_moods()
    st.metric("📝 Total Logs", len(df))
    st.metric("🔥 Current Streak", calculate_streak())
    st.metric("🧠 Wellness Score", f"{wellness_score(df)}/100")

    if not df.empty:
        mood_counts = df.groupby("date")["mood"].value_counts().unstack().fillna(0)
        st.line_chart(mood_counts)

        last_week = date.today() - timedelta(days=7)
        weekly_df = df[pd.to_datetime(df["date"]) >= pd.to_datetime(last_week)]
        if not weekly_df.empty:
            top_mood = weekly_df["mood"].mode()[0]
            st.success(f"Most frequent mood this week: {top_mood}")
            st.bar_chart(weekly_df["mood"].value_counts())

        if df["note"].notna().any():
            st.subheader("☁️ Word Cloud of Your Notes")
            notes = df["note"].dropna().tolist()
            fig = plot_wordcloud(notes)
            if fig:
                st.pyplot(fig)

        st.subheader("📂 Mood History")
        hist = df.sort_values("date_time", ascending=False).reset_index(drop=True)
        st.dataframe(hist, height=300)
        csv = hist.to_csv(index=False).encode()
        st.download_button("Download mood logs (CSV)", csv, "mood_log.csv", "text/csv")

# --- Journaling ---
with tabs[3]:
    st.subheader("📖 Journaling")
    entry = st.text_area("Write your thoughts here...")
    if st.button("Analyze My Journal"):
        if entry.strip():
            with st.spinner("Analyzing..."):
                response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
                    f"Analyze this journal entry for emotional tone and give supportive feedback:\n{entry}"
                )
                st.write(response.text)
        else:
            st.warning("Write something before analyzing.")

# --- Exercises ---
with tabs[4]:
    st.subheader("🧘 Guided Breathing Exercise")
    if st.button("Start 30-sec Breathing"):
        for i in range(3):
            st.write("🌬️ Inhale...")
            time.sleep(4)
            st.write("😌 Exhale...")
            time.sleep(4)
        st.success("Done! Feeling calmer?")

    st.subheader("🌟 Daily Affirmation")
    if "last_affirmation" not in st.session_state or st.session_state["last_affirmation_date"] != str(date.today()):
        try:
            response = genai.GenerativeModel("gemini-1.5-flash").generate_content(
                "Generate a short positive daily affirmation (1 sentence)."
            )
            st.session_state["last_affirmation"] = response.text
            st.session_state["last_affirmation_date"] = str(date.today())
        except:
            st.session_state["last_affirmation"] = random.choice(AFFIRMATIONS)
    st.success(st.session_state["last_affirmation"])

    st.subheader("💡 Inspirational Quote")
    st.info(random.choice(QUOTES))
