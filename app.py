import streamlit as st
import json
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agent import generate_caption, post_to_linkedin

st.set_page_config(page_title="LinkedIn AI Agent", page_icon="💼", layout="centered")

# ── Scheduler ─────────────────────────────────────────────────────────────────
if "scheduler" not in st.session_state:
    st.session_state.scheduler = BackgroundScheduler()
    st.session_state.scheduler.start()

if "scheduled_jobs" not in st.session_state:
    st.session_state.scheduled_jobs = []

if "post_log" not in st.session_state:
    st.session_state.post_log = []

scheduler = st.session_state.scheduler


def scheduled_post_job(topic: str, tone: str):
    try:
        caption = generate_caption(topic, tone)
        result = post_to_linkedin(caption)
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topic": topic,
            "caption": caption,
            "status": "✅ Posted" if result["status"] == 201 else f"❌ Failed ({result['status']})"
        }
    except Exception as e:
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "topic": topic,
            "caption": "Error",
            "status": f"❌ Error: {str(e)}"
        }
    st.session_state.post_log.append(log_entry)


# ── UI ────────────────────────────────────────────────────────────────────────
st.title("💼 LinkedIn AI Agent")
st.caption("Generate captions with Groq + post to LinkedIn instantly or on a schedule.")
st.divider()

# ── Post Composer ─────────────────────────────────────────────────────────────
st.subheader("✍️ Compose Post")

topic = st.text_area("What do you want to post about?", height=100,
                     placeholder="e.g. Just finished building an AI project...")

tone = st.selectbox("Tone", ["Professional", "Casual", "Inspirational", "Technical"])

col1, col2 = st.columns(2)

with col1:
    if st.button("✨ Generate Caption", use_container_width=True):
        if not topic.strip():
            st.warning("Please enter a topic first.")
        else:
            with st.spinner("Generating with Groq..."):
                try:
                    caption = generate_caption(topic, tone.lower())
                    st.session_state.generated_caption = caption
                except Exception as e:
                    st.error(f"Error: {e}")

if "generated_caption" in st.session_state:
    st.session_state.generated_caption = st.text_area(
        "Generated Post (edit if needed)",
        value=st.session_state.generated_caption,
        height=200
    )

    with col2:
        if st.button("🚀 Post Now", use_container_width=True):
            with st.spinner("Posting to LinkedIn..."):
                result = post_to_linkedin(st.session_state.generated_caption)
                if result["status"] == 201:
                    st.success("✅ Posted! Check your LinkedIn feed.")
                    st.session_state.post_log.append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "topic": topic,
                        "caption": st.session_state.generated_caption,
                        "status": "✅ Posted"
                    })
                else:
                    st.error(f"❌ Failed: {result['body']}")

st.divider()

# ── Scheduler ─────────────────────────────────────────────────────────────────
st.subheader("🕐 Schedule a Post")

sched_topic = st.text_area("Topic for scheduled post", height=80,
                           placeholder="e.g. Weekly ML learning update")
sched_tone = st.selectbox("Tone ", ["Professional", "Casual", "Inspirational", "Technical"],
                          key="sched_tone")

col3, col4 = st.columns(2)
with col3:
    sched_date = st.date_input("Date", min_value=datetime.today())
with col4:
    sched_time = st.time_input("Time", value=time(9, 0))

repeat = st.selectbox("Repeat", ["Once", "Daily", "Weekly"])

if st.button("📅 Schedule Post", use_container_width=True):
    if not sched_topic.strip():
        st.warning("Please enter a topic.")
    else:
        sched_dt = datetime.combine(sched_date, sched_time)

        if repeat == "Once":
            trigger = CronTrigger(
                year=sched_dt.year, month=sched_dt.month, day=sched_dt.day,
                hour=sched_dt.hour, minute=sched_dt.minute
            )
        elif repeat == "Daily":
            trigger = CronTrigger(hour=sched_dt.hour, minute=sched_dt.minute)
        else:
            trigger = CronTrigger(
                day_of_week=sched_dt.strftime("%a").lower(),
                hour=sched_dt.hour, minute=sched_dt.minute
            )

        job = scheduler.add_job(
            scheduled_post_job,
            trigger=trigger,
            args=[sched_topic, sched_tone.lower()],
            id=f"job_{len(st.session_state.scheduled_jobs)}"
        )

        st.session_state.scheduled_jobs.append({
            "id": job.id,
            "topic": sched_topic[:50] + "..." if len(sched_topic) > 50 else sched_topic,
            "datetime": sched_dt.strftime("%Y-%m-%d %H:%M"),
            "repeat": repeat
        })
        st.success(f"✅ Scheduled for {sched_dt.strftime('%Y-%m-%d %H:%M')} ({repeat})")

if st.session_state.scheduled_jobs:
    st.divider()
    st.subheader("📋 Scheduled Jobs")
    for job in st.session_state.scheduled_jobs:
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(f"**{job['datetime']}** ({job['repeat']}) — {job['topic']}")
        with col_b:
            if st.button("Cancel", key=f"cancel_{job['id']}"):
                try:
                    scheduler.remove_job(job['id'])
                    st.session_state.scheduled_jobs.remove(job)
                    st.rerun()
                except Exception:
                    pass

st.divider()

# ── Post Log ──────────────────────────────────────────────────────────────────
st.subheader("📜 Post History")
if st.session_state.post_log:
    for entry in reversed(st.session_state.post_log):
        with st.expander(f"{entry['status']} — {entry['time']} — {entry['topic'][:40]}"):
            st.write(entry['caption'])
else:
    st.caption("No posts yet.")