# Detailed Project Guide & AI Handoff Specification
## Project: Virtual Room 360 (`virtual_room_360`)

> **Note for AI Assistants (Antigravity, ChatGPT, Claude, Cursor, Copilot, etc.):**
> Read this document completely before modifying or running any code. It contains the exact architecture, branch separation, completed milestones, remaining tasks, and strict coding guardrails to avoid unnecessary or breaking changes.

---

## 1. Project Overview & Architecture

**Virtual Room 360** is a lightweight web application that turns 8–40 smartphone photos of an indoor room into an interactive 360° panorama:
* **Backend:** Python 3.11+, FastAPI, OpenCV (`cv2.Stitcher` for classical cylindrical panorama stitching without heavy GPUs or AI models).
* **Database:** SQLite (`data/app.db`) for local mode; **Turso Cloud SQLite** (`libsql`) for 24/7 cloud mode.
* **Storage:** Local filesystem (`uploads/`) for local mode; **Cloudinary CDN** for 24/7 cloud mode.
* **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+), and Three.js for interactive spherical 360° viewing. No complex node/npm build step required.
* **Authentication:** Argon2id password hashing, 256-bit server-side session tokens in HTTP-only cookies, and a secure 6-digit Email OTP "Forgot Password" flow via Gmail SMTP (port 465 SSL).

---

## 2. Git Branch Strategy

This repository uses **two distinct branches**:

| Branch | Purpose | Storage & DB | How to Run |
| :--- | :--- | :--- | :--- |
| **`master`** | **Local Development & Demos** | Local SQLite (`data/app.db`) + Local `uploads/` folder | Run `./start_server.sh` for instant public HTTPS via Cloudflare Tunnel |
| **`deploy/render-free-cloud`** | **24/7 Cloud Deployment** | Turso Cloud SQLite + Cloudinary CDN (100% Free, No Credit Card) | Hosted on Render Free Web Service |

> ⚠️ **Rule:** Keep local demo workflows on `master`. Work on 24/7 cloud hosting on `deploy/render-free-cloud`. Do not merge `deploy/render-free-cloud` into `master` until cloud deployment is completely verified.

---

## 3. What Has Been Done (Completed Milestones)

1. **Fullstack Core Application:**
   * User registration and login with Argon2id password hashing.
   * Categories and Room creation/management.
   * Batch image upload (8 to 40 photos per room).
   * Panorama generation using OpenCV `cv2.Stitcher`.
   * Interactive Three.js 360° viewer in the browser.
2. **Secure Email OTP Forgot-Password System:**
   * Backend endpoints: `/api/auth/forgot-password`, `/resend-otp`, `/verify-otp`, `/reset-password`.
   * Security controls: SHA-256 OTP hashing, 10-minute expiry, 60s cooldown timer, max 5 failed attempts, session invalidation on password reset, email enumeration prevention.
   * SMTP Service: Custom `backend/email_service.py` with automatic Port 465 SSL fallback (tested and verified with Gmail SMTP).
   * Frontend UI: Multi-step modal with 6-digit input boxes, live countdown timer, and automatic resend cooldown.
3. **Local Cloudflare Tunnel:**
   * [start_server.sh](file:///home/githubdev/virtual_room_360/start_server.sh) script automatically boots backend uvicorn and starts the bundled [bin/cloudflared](file:///home/githubdev/virtual_room_360/bin/cloudflared) tunnel to produce an instant public `https://*.trycloudflare.com` URL.
4. **24/7 Free Cloud Setup (on `deploy/render-free-cloud`):**
   * **Database:** Integrated Turso libSQL in [backend/db.py](file:///home/githubdev/virtual_room_360/backend/db.py) with custom `LibsqlCursorWrapper` and `DictRow` mapping. **Turso remote database is already created and schema initialized.**
   * **Storage:** Created [backend/storage.py](file:///home/githubdev/virtual_room_360/backend/storage.py) supporting Cloudinary CDN uploads, deletion, and HTTP 307 redirect asset serving.
   * **Hybrid Fallback:** When cloud credentials are empty, the app runs locally without errors.
   * **Render Blueprint:** Created [render.yaml](file:///home/githubdev/virtual_room_360/render.yaml) and [.python-version](file:///home/githubdev/virtual_room_360/.python-version) (`3.11.9`).
   * **Automated Tests:** 11 pytest unit tests created and passing (`100% pass rate`).

---

## 4. Setting Up on a New Machine (When You Clone at Home)

Follow these exact steps when cloning this repository on a new home system:

### Step 1: Clone the Repo
```bash
git clone https://github.com/Meenuth047/virtual_room_360.git
cd virtual_room_360
```

### Step 2: Choose Your Branch
* To run the **24/7 Cloud version**:
  ```bash
  git checkout deploy/render-free-cloud
  ```
* To run the **Local SQLite + Cloudflare Tunnel version**:
  ```bash
  git checkout master
  ```

### Step 3: Create Python Virtual Environment & Install Dependencies
```bash
# Python 3.11 or 3.12 recommended
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt
```

*(Note for Linux users: If OpenCV complains about missing libraries, run: `sudo apt update && sudo apt install -y libgl1 libglib2.0-0`)*

### Step 4: Create Your `.env` File
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Fill in the values in `.env`:
```ini
# Session and Upload limits
SESSION_TTL_HOURS=72
MIN_IMAGES=8
RECOMMENDED_MIN_IMAGES=15
RECOMMENDED_MAX_IMAGES=30
MAX_IMAGES=40
MAX_FILE_SIZE_MB=15
MAX_SOURCE_DIMENSION=2000
CORS_ORIGINS=*
ENVIRONMENT=development

# Gmail SMTP Email settings (for Password Reset OTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-gmail-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=false
SMTP_USE_SSL=true

# Turso Cloud SQLite (already created!)
TURSO_DATABASE_URL=libsql://virtual-room-360-meenuth047.aws-ap-south-1.turso.io
TURSO_AUTH_TOKEN=your-turso-auth-token

# Cloudinary 360° Photo Storage (Free 25 GB)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### Step 5: Run Automated Tests to Verify Everything
```bash
pytest tests/
```
All 11 tests should pass cleanly.

### Step 6: Start the Server Locally
```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Open `http://127.0.0.1:8000` in your web browser.

---

## 5. What Remains to be Done (Next Steps)

1. **Obtain Cloudinary Keys:**
   * Go to [https://cloudinary.com](https://cloudinary.com) and log in with GitHub/Google.
   * Copy `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` from the dashboard.
2. **Deploy Web Service on Render:**
   * Go to [https://render.com](https://render.com).
   * Create **New Web Service** pointing to repository `Meenuth047/virtual_room_360`.
   * Set Branch to: `deploy/render-free-cloud`.
   * Set Plan to: **Free** ($0 / month).
   * Build Command: `pip install -r requirements.txt`.
   * Start Command: `python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
   * Add the Environment Variables from your `.env` (Turso credentials, Cloudinary credentials, and Gmail SMTP credentials).
   * Click **Deploy**.
3. **End-to-End Cloud Verification:**
   * Open the live Render URL (e.g. `https://virtual-room-360.onrender.com`).
   * Register a new user (verify that default categories are seeded in Turso).
   * Test "Forgot Password" (verify that OTP email arrives in inbox).
   * Create a room, upload 8+ photos, click "Generate Panorama" (verify panorama renders in Three.js and asset URL is saved on Cloudinary).

---

## 6. Strict Instructions for AI Assistants

When any AI assistant continues development on this project, it **MUST adhere to the following rules**:

1. **DO NOT Rewrite SQLite Queries into PostgreSQL or ORMs:**
   * The backend uses standard Python SQLite syntax with `?` parameter placeholders and `cur.lastrowid`.
   * Turso is **100% SQLite compatible**. Do not rewrite raw SQL queries or replace them with SQLAlchemy/Postgres dialect.
2. **DO NOT Introduce Paid Services or Services Requiring Credit Cards:**
   * Render Free compute tier ($0).
   * Turso Free tier (9 GB, $0, no credit card).
   * Cloudinary Free tier (25 GB, $0, no credit card).
   * Do not attach Render Disks ($7/mo).
3. **Preserve the Hybrid Storage & Database Fallback:**
   * If `TURSO_DATABASE_URL` is empty, [backend/db.py](file:///home/githubdev/virtual_room_360/backend/db.py) must connect to local SQLite (`data/app.db`).
   * If `CLOUDINARY_CLOUD_NAME` is empty, [backend/storage.py](file:///home/githubdev/virtual_room_360/backend/storage.py) must save files to local `uploads/`.
   * Never break offline/local development.
4. **Preserve Frontend Code & Endpoint Contracts:**
   * The frontend Three.js viewer expects the panorama at `/api/rooms/{id}/panorama-file` and thumbnail at `/api/rooms/{id}/thumbnail-file`.
   * When assets are on Cloudinary, the backend returns an HTTP 307 `RedirectResponse`, which the browser and Three.js follow automatically. Do not change frontend asset loading logic unless asked.
5. **Never Commit Secrets:**
   * Never commit real `.env`, passwords, or API tokens to git.
