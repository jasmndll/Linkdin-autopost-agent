import streamlit as st
import requests
import urllib.parse
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from agent import (
    generate_caption,
    post_to_linkedin,
    upload_image_to_linkedin,
    post_to_linkedin_with_image
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="LinkedIn AI Agent", page_icon="💼", layout="centered")

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in {
    "access_token": None,
    "person_urn": None,
    "user_name": None,
    "generated_caption": "",
    "post_log": [],
    "scheduled_jobs": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if "scheduler" not in st.session_state:
    st.session_state.scheduler = BackgroundScheduler()
    st.session_state.scheduler.start()

scheduler = st.session_state.scheduler


# ── LinkedIn OAuth helpers ────────────────────────────────────────────────────

def get_redirect_uri() -> str:
    try:
        return st.secrets["REDIRECT_URI"]
    except:
        return "http://localhost:8501/"


def get_linkedin_auth_url() -> str:
    params = {
        "response_type": "code",
        "client_id": st.secrets["LINKEDIN_CLIENT_ID"],
        "redirect_uri": get_redirect_uri(),
        "scope": "openid profile email w_member_social",
        "state": "streamlit_linkedin_agent"
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_redirect_uri(),
        "client_id": st.secrets["LINKEDIN_CLIENT_ID"],
        "client_secret": st.secrets["LINKEDIN_CLIENT_SECRET"]
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def get_user_profile(access_token: str) -> tuple:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    response.raise_for_status()
    data = response.json()
    person_urn = f"urn:li:person:{data['sub']}"
    name = data.get("name", "User")
    return person_urn, name


def clear_session():
    st.session_state.access_token = None
    st.session_state.person_urn = None
    st.session_state.user_name = None
    st.session_state.generated_caption = ""


# ── Handle OAuth callback ─────────────────────────────────────────────────────

query_params = st.query_params
if "code" in query_params and st.session_state.access_token is None:
    try:
        code = query_params["code"]
        token = exchange_code_for_token(code)
        person_urn, name = get_user_profile(token)
        st.session_state.access_token = token
        st.session_state.person_urn = person_urn
        st.session_state.user_name = name
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Login failed: {e}")


# ── Login screen ──────────────────────────────────────────────────────────────

if not st.session_state.access_token:
    st.title("💼 LinkedIn AI Agent")
    st.write("Post to LinkedIn using AI-generated captions.")
    st.divider()
    st.subheader("Login to get started")
    st.write("Click below to log in with your LinkedIn account. You will be redirected back here after approving access.")
    auth_url = get_linkedin_auth_url()
    st.link_button("🔗 Login with LinkedIn", auth_url, use_container_width=True)
    st.caption("Your LinkedIn credentials are never stored. Only a temporary session token is used.")
    st.stop()


# ── Scheduler job ─────────────────────────────────────────────────────────────

def scheduled_post_job(topic: str, tone: str, access_token: str, person_urn: str):
    try:
        caption = generate_caption(topic, tone)
        result = post_to_linkedin(caption, access_token, person_urn)
        status = "✅ Posted" if result["status"] == 201 else f"❌ Failed ({result['status']})"
    except Exception as e:
        caption = "Error"
        status = f"❌ Error: {str(e)}"

    st.session_state.post_log.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "caption": caption,
        "status": status
    })


# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title("💼 LinkedIn AI Agent")
    st.caption(f"Logged in as **{st.session_state.user_name}**")
with col_logout:
    st.write("")
    if st.button("Logout", use_container_width=True):
        clear_session()
        st.rerun()

st.divider()

# ── Compose Post ──────────────────────────────────────────────────────────────

st.subheader("✍️ Compose Post")

topic = st.text_area(
    "What do you want to post about?",
    height=100,
    placeholder="e.g. Just finished building an AI project using sentence-transformers and Streamlit..."
)

tone = st.selectbox("Tone", ["Professional", "Casual", "Inspirational", "Technical"])

uploaded_images = st.file_uploader(
    "Attach images (optional, max 9)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Upload up to 9 JPG or PNG images to include in your post"
)

if uploaded_images:
    if len(uploaded_images) > 9:
        st.error("LinkedIn allows a maximum of 9 images per post. Please remove some.")
        uploaded_images = uploaded_images[:9]
    st.write(f"**{len(uploaded_images)} image(s) selected:**")
    cols = st.columns(min(len(uploaded_images), 3))
    for i, img in enumerate(uploaded_images):
        with cols[i % 3]:
            st.image(img, caption=img.name, use_column_width=True)

col1, col2 = st.columns(2)

with col1:
    if st.button("✨ Generate Caption", use_container_width=True):
        if not topic.strip():
            st.warning("Please enter a topic first.")
        else:
            with st.spinner("Generating with Groq..."):
                try:
                    st.session_state.generated_caption = generate_caption(topic, tone.lower())
                except Exception as e:
                    st.error(f"Generation error: {e}")

if st.session_state.generated_caption:
    st.session_state.generated_caption = st.text_area(
        "Generated Post (edit if needed)",
        value=st.session_state.generated_caption,
        height=220
    )

    with col2:
        if st.button("🚀 Post Now", use_container_width=True):
            with st.spinner("Posting to LinkedIn..."):
                try:
                    access_token = st.session_state.access_token
                    person_urn = st.session_state.person_urn
                    caption_text = st.session_state.generated_caption

                    if uploaded_images:
                        st.info(f"Uploading {len(uploaded_images)} image(s) to LinkedIn...")
                        image_urns = []
                        for img in uploaded_images:
                            img.seek(0)
                            urn = upload_image_to_linkedin(
                                access_token, person_urn,
                                img.read(), img.name
                            )
                            image_urns.append(urn)
                        result = post_to_linkedin_with_image(
                            caption_text, image_urns,
                            access_token, person_urn
                        )
                        post_type = f"✅ Posted with {len(uploaded_images)} image(s)"
                    else:
                        result = post_to_linkedin(caption_text, access_token, person_urn)
                        post_type = "✅ Posted"

                    if result["status"] == 201:
                        st.success(f"{post_type}! Check your LinkedIn feed.")
                        st.session_state.post_log.append({
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "topic": topic,
                            "caption": caption_text,
                            "status": post_type
                        })
                    else:
                        st.error(f"❌ Failed: {result['body']}")

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

st.divider()

# ── Schedule a Post ───────────────────────────────────────────────────────────

st.subheader("🕐 Schedule a Post")

sched_topic = st.text_area(
    "Topic for scheduled post",
    height=80,
    placeholder="e.g. Weekly update on my ML learning journey"
)
sched_tone = st.selectbox(
    "Tone",
    ["Professional", "Casual", "Inspirational", "Technical"],
    key="sched_tone"
)

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
                year=sched_dt.year, month=sched_dt.month,
                day=sched_dt.day, hour=sched_dt.hour, minute=sched_dt.minute
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
            args=[
                sched_topic, sched_tone.lower(),
                st.session_state.access_token,
                st.session_state.person_urn
            ],
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

# ── Post History ──────────────────────────────────────────────────────────────

st.subheader("📜 Post History")
if st.session_state.post_log:
    for entry in reversed(st.session_state.post_log):
        with st.expander(f"{entry['status']} — {entry['time']} — {entry['topic'][:40]}"):
            st.write(entry["caption"])
else:
    st.caption("No posts yet. Generate and post something above!")

st.divider()

# ── Unlink Account ────────────────────────────────────────────────────────────

with st.expander("⚠️ Unlink LinkedIn Account"):
    st.warning("This will permanently revoke this app's access to your LinkedIn account. You can re-authorize anytime.")
    if st.button("🔗 Unlink My LinkedIn Account", use_container_width=True):
        try:
            revoke_url = "https://www.linkedin.com/oauth/v2/revoke"
            data = {
                "token": st.session_state.access_token,
                "client_id": st.secrets["LINKEDIN_CLIENT_ID"],
                "client_secret": st.secrets["LINKEDIN_CLIENT_SECRET"]
            }
            requests.post(revoke_url, data=data)
            clear_session()
            st.success("✅ Account unlinked. You have been logged out.")
            st.rerun()
        except Exception as e:
            st.error(f"Error revoking token: {e}")
            clear_session()
            st.rerun()