# Secure Flask API — CI/CD Pipeline Demo

A small Flask API that exists to demonstrate a clean, security-focused CI/CD
pipeline built with GitHub Actions. The application is intentionally minimal —
the pipeline is the point.

---

## What the application is

A minimal Python 3.12 / Flask service with three endpoints:

| Method | Path       | Purpose                                             |
|--------|------------|-----------------------------------------------------|
| GET    | `/health`  | Liveness probe (returns `{"status": "ok"}`)         |
| GET    | `/version` | Returns a build/version string for traceability     |
| POST   | `/echo`    | Validates and echoes a JSON `message` field         |

The app uses the Flask application-factory pattern (`create_app()`), caps
request body size, validates input on `/echo`, and runs under **gunicorn** in
the container rather than the Flask development server.

---

## How the pipeline works

The pipeline lives in `.github/workflows/ci-cd.yml` and runs on every push and
pull request to `main`. It is organized into four jobs. The build/deploy job
runs only after the three gating jobs pass, and only on a push to `main`.

```
                 ┌──────────────────────────┐
  push / PR  →   │ test  (pytest, Bandit,    │
                 │        pip-audit)         │
                 ├──────────────────────────┤
                 │ codeql (semantic SAST)    │ ── all three must pass
                 ├──────────────────────────┤
                 │ secrets (gitleaks)        │
                 └────────────┬─────────────┘
                              │ (push to main only)
                 ┌────────────▼─────────────┐
                 │ build-scan-deploy         │
                 │  docker build             │
                 │  Trivy image scan         │
                 │  push to GHCR             │
                 └──────────────────────────┘
```

### Jobs

1. **Test & Static Analysis** — Installs dependencies, runs the `pytest` suite,
   then runs **Bandit** (Python SAST) and **pip-audit** (dependency/SCA scan).
   A failing test or a high-severity Bandit finding fails the build.
2. **CodeQL Analysis** — GitHub-native semantic static analysis. Findings appear
   in the repository's **Security → Code scanning** tab.
3. **Secret Scan** — **gitleaks** scans the full git history for committed
   secrets, surfaced as a real pipeline run.
4. **Build, Scan & Deploy** — Builds the container image, scans it with
   **Trivy** (OS + dependency CVEs, uploaded as SARIF to the Security tab),
   then pushes to the **GitHub Container Registry (GHCR)** as the deploy step.

`.github/dependabot.yml` adds automated weekly update PRs for pip packages,
GitHub Actions, and the Docker base image.

---

## Security choices and reasoning

The pipeline covers all four security-step categories from the brief, chosen to
match a containerized Python service:

- **SAST (two layers): Bandit + CodeQL.** Bandit is fast, Python-specific, and
  catches common issues (injection, weak crypto, unsafe calls) right in the test
  job. CodeQL adds deeper semantic analysis and is the GitHub-native option, so
  results integrate directly into the Security tab.
- **Dependency / SCA: pip-audit + Dependabot.** pip-audit fails the build if a
  dependency has a known CVE at build time; Dependabot keeps things patched over
  time so the audit doesn't start failing later.
- **Secret scanning: gitleaks (workflow) + GitHub push protection (settings).**
  Defense in depth — push protection blocks secrets *before* they land, gitleaks
  catches anything already in history.
- **Container scanning: Trivy.** Scans the built image for OS-package and
  application CVEs before it's published.

### Pipeline hardening choices

- **Least-privilege tokens.** The workflow defaults to `permissions: contents:
  read`; each job elevates only what it needs (`packages: write` to push,
  `security-events: write` to upload SARIF). The token is never broadly scoped.
- **GHCR over an external registry.** Publishing to GHCR uses the built-in
  `GITHUB_TOKEN`, so there are **no long-lived registry credentials** stored as
  secrets.
- **Pinned dependencies and base image** for reproducible, scannable builds.
- **Non-root container user** and a minimal build context (`.dockerignore`).
- **Gated deploy.** Nothing publishes unless tests and all security jobs pass.

---

## How to run / reproduce

### Locally

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run the test suite
pytest -q

# Run the security checks the pipeline runs
bandit -r app -ll
pip-audit -r requirements.txt

# Run the app locally
gunicorn --bind 127.0.0.1:8000 app.main:app
curl localhost:8000/health
curl -X POST localhost:8000/echo -H "Content-Type: application/json" -d '{"message":"hi"}'
```

### With Docker

```bash
docker build -t secure-flask-api .
docker run -p 8000:8000 secure-flask-api
curl localhost:8000/health
```

### Pulling the published image

After a push to `main`, the image is available from GHCR:

```bash
docker pull ghcr.io/<owner>/<repo>:latest
```

---

## Repository settings to enable

A few protections live in repository settings rather than in YAML. Enable these
under **Settings → Code security**:

- **Secret scanning** and **push protection** (free on public repos)
- **Dependabot alerts** and **security updates**
- **CodeQL / code scanning** (the workflow provides the analysis)
- A **branch protection rule** on `main` requiring the pipeline checks to pass
  before merge

---

## Repository structure

```
.
├── app/
│   ├── __init__.py
│   └── main.py              # Flask application factory + endpoints
├── tests/
│   └── test_main.py         # pytest suite (gates the pipeline)
├── .github/
│   ├── workflows/ci-cd.yml  # the CI/CD pipeline
│   └── dependabot.yml       # automated dependency updates
├── Dockerfile               # hardened, non-root, gunicorn
├── .dockerignore
├── requirements.txt         # pinned runtime deps
└── requirements-dev.txt     # test + security tooling
```
