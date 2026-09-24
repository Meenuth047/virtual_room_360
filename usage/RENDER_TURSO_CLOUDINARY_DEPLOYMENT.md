# 24/7 Free Cloud Deployment Guide
## Render + Turso Cloud SQLite + Cloudinary CDN (100% Free Forever, No Credit Card)

This deployment architecture hosts **Virtual Room 360** online 24/7 on Render's free tier without needing paid Render disks, and without keeping your home computer on.

---

### Architecture Overview

```
                      +-----------------------------+
                      |   Render Free Web Service   |
                      |  (FastAPI + Three.js HTML)  |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
+--------------v---------------+             +-------------v--------------+
|     Turso (Cloud SQLite)     |             |        Cloudinary CDN      |
|  - 9 GB free permanent DB    |             |  - 25 GB free photo storage|
|  - Users, OTPs, Rooms data   |             |  - 360° panoramas & thumbs |
|  - No Credit Card required   |             |  - No Credit Card required |
+------------------------------+             +----------------------------+
```

---

### Step 1: Create Free Turso Database (Takes ~1 minute)

1. Go to [https://turso.tech](https://turso.tech) and click **Sign Up** (Choose **Continue with GitHub** — no credit card needed).
2. In the Turso web dashboard (or CLI), click **Create Database**.
3. Name your database: `virtual-room-360` (choose a region close to you).
4. Go to the database details:
   - Copy the **Database URL** (starts with `libsql://...`).
   - Click **Create Token** (or **Generate Token**) and copy the **Auth Token**.
5. Save these two values:
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`

---

### Step 2: Create Free Cloudinary Account (Takes ~1 minute)

1. Go to [https://cloudinary.com](https://cloudinary.com) and click **Sign Up For Free** (no credit card needed).
2. Once logged in, on your **Dashboard** (Product Environment), you will see your **API Keys**:
   - **Cloud Name**
   - **API Key**
   - **API Secret**
3. Save these three values:
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`

---

### Step 3: Deploy on Render (Takes ~2 minutes)

1. Go to [https://render.com](https://render.com) and log in with your GitHub account.
2. Click **New +** and select **Web Service**.
3. Connect your repository: `Meenuth047/virtual_room_360`.
4. In the setup settings:
   - **Name:** `virtual-room-360` (or whatever you prefer)
   - **Branch:** `deploy/render-free-cloud` (or merge this branch into master when ready)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Select **Free** ($0 / month).
5. Scroll down to **Environment Variables** and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Production environment mode |
| `CORS_ORIGINS` | `*` | Allow web traffic |
| `TURSO_DATABASE_URL` | `libsql://your-db.turso.io` | From Step 1 |
| `TURSO_AUTH_TOKEN` | `your-turso-token` | From Step 1 |
| `CLOUDINARY_CLOUD_NAME` | `your-cloud-name` | From Step 2 |
| `CLOUDINARY_API_KEY` | `your-api-key` | From Step 2 |
| `CLOUDINARY_API_SECRET` | `your-api-secret` | From Step 2 |
| `SMTP_HOST` | `smtp.gmail.com` | Your Gmail SMTP host |
| `SMTP_PORT` | `465` | SSL port |
| `SMTP_USERNAME` | `your-email@gmail.com` | Your Gmail address |
| `SMTP_PASSWORD` | `your-16-char-app-password` | Gmail App Password |
| `SMTP_FROM` | `your-email@gmail.com` | Sender address |
| `SMTP_USE_SSL` | `true` | SSL enabled |

6. Click **Deploy Web Service**!

---

### Important Notes

* **Zero Monthly Cost:** Render's web hosting is $0, Turso is $0 (9 GB), and Cloudinary is $0 (25 GB). You will never be billed.
* **Persistent Data:** Users, OTP reset tokens, room metadata, and 360° panoramas remain permanently saved in the cloud even when Render free containers go to sleep or restart.
* **Local Development:** When `TURSO_DATABASE_URL` and `CLOUDINARY_CLOUD_NAME` are empty in your local `.env`, the project automatically falls back to local SQLite (`data/app.db`) and local folder storage (`uploads/`).
