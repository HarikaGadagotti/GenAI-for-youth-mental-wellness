# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------- Load API key ----------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or (st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else None)
if not GOOGLE_API_KEY:
    st.warning("⚠️ Google API key not found. Set GOOGLE_API_KEY in environment or Streamlit secrets.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# ---------------- Config ----------------
MOOD_FILE = "mood_log.csv"

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "i want to die", "give up", "self harm",
    "hurt myself", "i cant go on", "i can't go on", "i'm going to kill myself"
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

SYSTEM_PROMPT = (
    "You are a compassionate, non-judgmental mental wellness assistant for young people. "
    "Respond with empathy, reflective listening, and short supportive suggestions. "
    "Do not provide clinical diagnoses. If the user mentions self-harm or suicide, "
    "respond with a brief statement acknowledging distress and provide crisis resources and encourage seeking immediate help. "
    "Keep responses concise (2-5 sentences) and suggest a simple coping action the user can try right now."
)

LANGUAGES = {"English": "en", "Hindi": "hi", "Telugu": "te"}

# ---------------- Functions ----------------
def generate_response(user_text, lang="English"):
    if not GOOGLE_API_KEY:
        return "Google API key not configured."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Translate input if needed
        if lang != "English":
            user_text = translate(user_text, lang)

        chat = model.start_chat(history=[])
        response = chat.send_message(user_text)
        output = response.text

        # Translate back if needed
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
        return text  # fallback


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
    return pd.DataFrame(columns=["date_time", "date", "mood", "note"])


def calculate_streak():
    df = load_moods()
    if df.empty:
        return 0
    df["date"] = pd.to_datetime(df["date"]).dt.date
    unique_dates = sorted(set(df["date"]), reverse=True)

    streak = 0
    today = date.today()
    for i, d in enumerate(unique_dates):
        expected = today - timedelta(days=i)  # ✅ fixed
        if d == expected:
            streak += 1
        else:
            break
    return streak


def get_coping_tip_for(mood):
    tips = {
        "Happy": "Nice! Share that positivity — text a friend or keep a gratitude note.",
        "Sad": "It can help to name the feeling. Try writing for 5 minutes about what's on your mind.",
        "Anxious": "Try a 2-minute breathing exercise: 4s in, 4s hold, 6s out (repeat).",
        "Angry": "Take a short walk or count to 10, then describe what made you angry in one sentence.",
        "Stressed": "Break tasks into tiny steps and take a short break (stretch/water)."
    }
    return tips.get(mood, "Take a few slow breaths and remind yourself you're doing your best.")


# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Mindsight — Youth Mental Wellness", page_icon="🧠", layout="wide")
st.title("🧠 Mindsight — Youth Mental Wellness")

# --- Language Selector ---
user_lang = st.selectbox("🌍 Choose your language", list(LANGUAGES.keys()))

left, right = st.columns([2, 1])

with left:
    st.header("💬 Chat with the AI Companion")
    user_text = st.text_area("Talk to Mindsight (type how you feel or a situation)", max_chars=1000, key="chat_input")
    if st.button("Send", key="send"):
        if is_crisis(user_text):
            st.error("🚨 We detected language that may indicate risk. Contact local emergency services immediately.")
            st.info("India helpline: " + ", ".join([f"{k}: {v}" for k, v in HELPLINES["India"].items()]))
        else:
            with st.spinner("Thinking..."):
                reply = generate_response(user_text, lang=user_lang)
            st.markdown("**Mindsight:**")
            st.write(reply)

    st.markdown("---")
    st.header("📓 Mood Logger")
    mood = st.selectbox("How would you describe your mood right now?", ["Happy", "Sad", "Anxious", "Angry", "Stressed"])
    note = st.text_area("Optional note (private)", key="note")
    if st.button("Log Mood", key="log"):
        save_mood(mood, note)
        st.success(f"✅ Saved mood: {mood}")
        st.info(get_coping_tip_for(mood))

with right:
    st.header("📈 Summary")
    df = load_moods()
    st.metric("Total Logs", len(df))
    st.metric("Current Streak (days)", calculate_streak())
    st.markdown("**Quick tips**")
    st.write("- Use the chat for immediate support.\n- Log mood daily to build a streak.\n- Crisis helplines in README.")

    # --- Daily Reminder ---
    today_str = date.today().isoformat()
    if df.empty or today_str not in df["date"].astype(str).values:
        st.warning("💡 You haven’t logged your mood today. Take a moment now!")

st.markdown("---")
st.header("📊 Mood Trend")
df = load_moods()
if not df.empty:
    mood_counts = df.groupby("date")["mood"].value_counts().unstack().fillna(0)
    st.line_chart(mood_counts)
else:
    st.info("No mood data yet to show trends.")

st.markdown("---")
st.header("📂 Mood History")
if not df.empty:
    hist = df.sort_values("date_time", ascending=False).reset_index(drop=True)
    st.dataframe(hist)
    csv = hist.to_csv(index=False).encode()
    st.download_button("⬇️ Download mood logs (CSV)", csv, "mood_log.csv", "text/csv")
else:
    st.info("No mood logs yet — try logging one above!")

st.markdown("---")

