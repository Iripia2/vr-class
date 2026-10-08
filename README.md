# Fieldglass — Virtual Reality Classroom with Responsible Expression Insights

A runnable Django project with server-rendered dashboards, a browser-based
Three.js classroom, and optional in-browser facial-expression estimates. This
is not a React/FastAPI/WebSocket LMS yet; the existing Django features remain
the working application foundation.

## What's real vs. what's simulated

- **Accounts, classrooms, lessons, enrollment, live sessions** — fully real,
  backed by SQLite via Django's ORM.
- **Virtual classroom** — a real browser-based 3D scene (Three.js). Drag to
  orbit, scroll to zoom. No VR headset required.
- **Facial-expression estimates** — optional webcam capture + a browser-side
   face-api.js model. Camera frames stay in the browser; only a category and
   confidence value are sent, after explicit, per-session student consent.
   Reports contain class aggregates, not individual labels.
- **Student check-ins** — an optional self-report about learning support,
   stored without an account identifier or timestamp and shown only in
   privacy-thresholded class aggregates.

## Requirements

- Python 3.10+
- A modern browser (Chrome, Edge, or Firefox) for WebGL + webcam access
- Internet access in the browser at runtime (Three.js, Bootstrap, and the
  face-api.js model weights load from public CDNs — they are not bundled
  in this zip)

## Step-by-step: running in VS Code

1. **Unzip** this project and open the folder in VS Code
   (`File → Open Folder…`).

2. **Open a terminal** in VS Code (`` Ctrl+` `` / `` Cmd+` ``).

3. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   ```

   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

   VS Code may prompt "Select Python Interpreter" — pick the one inside
   `venv`.

4. **Configure the environment** (optional for local SQLite):

   ```bash
   Copy-Item .env.example .env
   ```

   Local development uses SQLite and a temporary development key by default.
   Set `DJANGO_SECRET_KEY` in `.env` for a stable local session key. Never use
   `DEBUG=true` or a development key in production. For deployment, set
   `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS`, and a PostgreSQL `DATABASE_URL`.

5. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

6. **Run migrations** (creates `db.sqlite3` with all tables):

   ```bash
   python manage.py migrate
   ```

7. **(Optional) Create an admin account**, useful for inspecting data at
   `/admin/`:

   ```bash
   python manage.py createsuperuser
   ```

8. **Start the dev server:**

   ```bash
   python manage.py runserver
   ```

9. **Open the app** at http://127.0.0.1:8000/accounts/register/ and
   register two real accounts to try both roles — e.g. yourself as a
   Teacher and a second account (a different browser or an incognito
   window) as a Student.

10. **As the teacher:** create a classroom, note the join code, add a
   lesson, then click **Start a live session**.

11. **As the student:** join the classroom with the join code from the
   dashboard, then click **Join live session**. In the virtual classroom,
   choose **Continue Without Monitoring** or review privacy details before
   optionally consenting. Camera access begins only after the consent action;
   the browser sends only a categorized expression-pattern estimate and
   confidence score every 6 seconds, never a frame or video.

12. **As the teacher**, open **Class report** from the live session to see
   class-level expression-pattern counts and average confidence — never a
   per-student label.

## Tests

Run the implemented end-to-end classroom workflow and monitoring privacy
tests with:

```bash
python manage.py test classrooms.tests monitoring.tests
```

## Project layout

```
fieldglass/
├── manage.py
├── requirements.txt
├── fieldglass/          # project settings, urls
├── accounts/            # custom User model, registration, login
├── classrooms/          # Classroom, Enrollment, Lesson, ClassSession
├── monitoring/          # ConsentRecord, EmotionEvent, report view
├── templates/
└── static/
    ├── css/styles.css
    └── js/
        ├── classroom3d.js   # Three.js browser-based 3D scene
        └── emotion.js       # face-api.js webcam expression detection
```

## Privacy and responsible AI

- The classroom offers **Continue Without Monitoring**, **Review Privacy
   Details**, and **I Consent & Enable Monitoring**. The camera and model are
   not started until the student chooses monitoring.
- Consent is attached to one session and can be revoked. The server checks
   the user's student role, classroom enrollment, active session, and consent
   before accepting a signal.
- Frames are processed in-browser and never posted to the server. Signals are
   expression-pattern estimates, not proof of internal emotional state.
- Scores below 0.4 are categorized as low confidence; no-face and low-
   confidence states remain distinct.
- Teacher reports aggregate counts and average confidence. They do not expose
   individual signal history and state that signals are not used for grading,
   attendance, ranking, or discipline.
- Optional learning check-ins are explicitly student-authored and are not
   biometric inferences. No account ID or timestamp is stored with a response;
   small or imbalanced categories are suppressed in teacher reports.

## Deployment configuration

The settings read `.env` when present. `DATABASE_URL` supports SQLite or
PostgreSQL URLs; local development falls back to `db.sqlite3`. Production
requires `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, and `DJANGO_DEBUG=false`. Secure
cookies, HTTPS redirect, HSTS, and PostgreSQL SSL are enabled when debug is
disabled. Configure `CSRF_TRUSTED_ORIGINS` for the deployed HTTPS origin.

## Deploy on Railway

1. Push this project to a GitHub repository and create a Railway project from
   that repository.
2. Add a PostgreSQL service to the Railway project and make its connection
   URL available to the Django service as `DATABASE_URL`.
3. Generate a Railway public domain for the Django service. Add these service
   variables:

   - `DJANGO_SECRET_KEY`: a long, randomly generated secret
   - `DJANGO_DEBUG`: `false`
   - `DATABASE_URL`: reference the Railway PostgreSQL service's URL
   - `ALLOWED_HOSTS`: the exact Railway public hostname
   - `CSRF_TRUSTED_ORIGINS`: `https://` plus that hostname

   The app also reads Railway's `RAILWAY_PUBLIC_DOMAIN` variable for its host
   and trusted HTTPS origin. Do not commit a real `.env` file or secret.
4. Railway reads `railway.toml`, installs dependencies from `requirements.txt`,
   applies migrations, collects static files, and starts Gunicorn bound to
   Railway's assigned port. Open the generated HTTPS domain after deployment.

The deployment requires Railway PostgreSQL to be provisioned and linked before
the first start. `runserver` and SQLite remain the local-development path.

This repository intentionally does not infer emotions, attention, or
personality from face, voice, or gaze; it does not collect voice or eye data,
ingest social-media/CRM content, or claim GDPR certification. It also does
not yet include React/TypeScript, FastAPI, Redis, WebSockets, job workers,
2FA, email verification, or the wider LMS/admin/demo flows in the proposed
platform scope. Those are future architectural work and must not be
represented as implemented features.

## Where to go from here

- Set `DATABASE_URL` to a PostgreSQL connection URL for a deployed database.
- Add a "leave" WebSocket channel (Django Channels) if you want live hand
  raises/chat instead of page reloads.
- The face-api.js models currently load from a public GitHub Pages URL —
  for production, download the weight files and serve them from your own
  `static/` folder instead.
