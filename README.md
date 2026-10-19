# 💼 LinkedIn AI Posting Agent

An AI-powered Streamlit app that writes LinkedIn posts for you, lets you edit them, attach images, and publish instantly or on a schedule, all through your own LinkedIn account with secure OAuth 2.0 login.

**🚀 Live demo:** [linkdin-autopost-agent7.streamlit.app](https://linkdin-autopost-agent7.streamlit.app/)

Used by 10+ real LinkedIn accounts.

---

## ✨ Features

- **AI caption generation**: describe a topic, pick a tone (Professional, Casual, Inspirational, Technical) and get a ready-to-post caption from Llama 3.3 70B via the Groq API
- **Edit before you post**: tweak the generated text in the app before publishing
- **Image posts**: attach up to 9 JPG/PNG images, uploaded through LinkedIn's asset upload flow
- **Post now or schedule**: schedule one-time, daily, or weekly posts using APScheduler cron triggers
- **Scheduled job manager**: view and cancel upcoming scheduled posts
- **Post history**: review everything posted during your session
- **Secure login**: LinkedIn OAuth 2.0 (Authorization Code flow); your LinkedIn password is never seen or stored
- **One-click unlink**: revoke the app's access to your account from inside the app

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| Auth | LinkedIn OAuth 2.0 (`openid profile email w_member_social`) |
| Posting | LinkedIn UGC Posts API and Assets API |
| Scheduling | APScheduler (`BackgroundScheduler`, `CronTrigger`) |
| Language | Python |

---

## 🧠 How It Works

1. **Login**: the user signs in with LinkedIn. The app exchanges the authorization code for an access token and fetches the member's profile URN.
2. **Generate**: the topic and tone are sent to Groq, with a prompt that enforces a strong hook, short paragraphs, 3-5 hashtags, and under 300 words.
3. **Review**: the caption appears in an editable text box.
4. **Publish**: text posts go straight to the UGC Posts API. For image posts, each image is registered and uploaded to LinkedIn first, then attached to the post.
5. **Schedule**: scheduled jobs run in a background scheduler and call the same generate-and-post pipeline at the chosen time.

---

## 📁 Project Structure

```
Linkdin-autopost-agent/
├── app.py            # Streamlit UI, OAuth flow, scheduling, post history
├── agent.py          # Groq caption generation + LinkedIn posting/image upload
├── auth.py           # Standalone local OAuth helper (CLI flow, not used by the Streamlit app)
├── requirements.txt  # Python dependencies
└── .gitignore
```

---

## ⚙️ Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/jasmndll/Linkdin-autopost-agent.git
cd Linkdin-autopost-agent
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create a LinkedIn app

1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) and create an app.
2. Add the products **Sign In with LinkedIn using OpenID Connect** and **Share on LinkedIn**.
3. Under **Auth**, add `http://localhost:8501/` as an authorized redirect URL.
4. Copy your **Client ID** and **Client Secret**.

### 4. Get a Groq API key

Create a free key at [console.groq.com](https://console.groq.com).

### 5. Add your secrets

Create `.streamlit/secrets.toml` in the project root:

```toml
LINKEDIN_CLIENT_ID = "your-linkedin-client-id"
LINKEDIN_CLIENT_SECRET = "your-linkedin-client-secret"
GROQ_API_KEY = "your-groq-api-key"
REDIRECT_URI = "http://localhost:8501/"
```

> ⚠️ Never commit `secrets.toml`. Make sure `.streamlit/` is listed in `.gitignore`.

### 6. Start the app

```bash
streamlit run app.py
```

Open `http://localhost:8501`, click **Login with LinkedIn**, and start posting.

---

## ☁️ Deploying on Streamlit Cloud

1. Push the repo to GitHub.
2. Create a new app on [Streamlit Community Cloud](https://streamlit.io/cloud) pointing to `app.py`.
3. Paste the same keys from `secrets.toml` into the app's **Secrets** settings, with `REDIRECT_URI` set to your deployed app URL (for example `https://linkdin-autopost-agent7.streamlit.app/`).
4. Add that same URL as an authorized redirect URL in your LinkedIn app.

---

## 🔒 Privacy & Security

- LinkedIn credentials are never stored. Only a temporary access token is kept in the session.
- API keys and client secrets live in Streamlit secrets, not in the code.
- Users can revoke the app's access at any time with the **Unlink LinkedIn Account** option.

---

## ⚠️ Known Limitations

- Scheduled jobs and post history live in memory, so they are lost if the app restarts or the session ends.
- LinkedIn access tokens expire (typically after about 60 days), so a long-running schedule may need re-login.
- Image posts support JPG and PNG only, up to 9 images per post.

---

## 🗺️ Roadmap

- [ ] Persist scheduled jobs and post history in a database
- [ ] Token refresh handling
- [ ] Post analytics
- [ ] Draft saving and multiple caption variants

---

## 👩‍💻 Author

**Jasmine**: B.Tech CSE, Lovely Professional University

- GitHub: [@jasmndll](https://github.com/jasmndll)
- Portfolio: [jasmine77.netlify.app](https://jasmine77.netlify.app)

---

## 📄 License

This project is open source. Add a license of your choice (for example MIT) to the repo.
