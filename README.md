# DR Vision

A Django app for patient records, appointments, and retinal image analysis. Patient and appointment workflows work without the AI model.

> **Model status:** This repository does not include the trained model weights. Image analysis is unavailable until a compatible model is installed. The upload page explains this and disables submission.

## Quick start

Use Python 3.12 and run these commands from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/register/> to create an account, then sign in. If port 8000 is busy, use `python manage.py runserver 8001` and open the corresponding URL.

The app uses a local SQLite database (`db.sqlite3`). Uploaded images are stored under `media/`. Both are local runtime files and are excluded from Git.

Appointment times are displayed in the app's configured `Africa/Casablanca` time zone.

## Screenshot data

Run `python manage.py seed_demo` while in development mode. It creates a separate `demo_clinic` account with 10 fictional patients and 7 appointments. The command prints a random temporary password. Use that account for screenshots; running the command again refreshes appointment dates and rotates the password. It creates no retinal images or invented diagnoses.

## Enable image analysis

The inference code in `app/utils.py` expects a PyTorch state dictionary at `app/model_weights/best_model.pth`. The file must match the `DRNet` architecture defined there. It is not provided in this repository.

Install the additional packages in the active virtual environment:

```bash
python -m pip install torch torchvision numpy opencv-python
```

Place a compatible `best_model.pth` in `app/model_weights/`, then restart the server. The model predicts one of five stages: No DR, Mild, Moderate, Severe, or Proliferative DR.

## Project layout

| Path | Purpose |
| --- | --- |
| `config/` | Django settings and root URLs |
| `app/models.py` | Users, patients, appointments, and retinal images |
| `app/views.py` | Registration, dashboard, patients, appointments, uploads, and results |
| `app/utils.py` | Image preprocessing and model inference |
| `app/templates/app/` | Page templates |
| `app/static/app/` | CSS, JavaScript, and images |

## Development notes

Run `python manage.py check` to validate the Django configuration and `python manage.py test app` to run the app tests.

For local development, Django creates an ignored `.local_secret_key` file with owner-only permissions. To deploy, set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` to a new random value, and `DJANGO_ALLOWED_HOSTS` to your domain. `.env.example` lists these variables but is not loaded automatically. Public account registration is disabled when debug mode is off. Use `python manage.py check --deploy` with the deployment environment.

Uploaded images are served through authenticated, owner-checked views. Do not configure a web server to expose `media/` directly. Use HTTPS, protect backups, and review the hosting setup before storing real patient information. This repository is a development project, not a production clinical system.

**GitHub history warning:** The original Git commits contain an old Django secret key. The active key is now different, but deleting a secret from the current file does not erase old commits. For a public repository with no old key in its history, publish from a fresh repository made from the cleaned source files, rather than pushing this repository's existing history. If the old key was ever used outside local development, rotate it there as well. See [GitHub's guidance on exposed secrets](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
