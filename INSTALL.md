# Installation and Environment Verification

Complete this document before beginning the roadmap. Do not install optional infrastructure until a roadmap stage explicitly requires it.

## 1. Required accounts

- GitHub account with permission to create repositories.
- GitHub Copilot plan that includes the GitHub Copilot App and agent sessions.
- Render account connected to GitHub for the publication stage.
- Optional: credentials for any external data API that requires a key.

Use official, public, no-key data or recorded fixtures for the first dashlet wherever possible.

## 2. Required software

### Git

Verify:

```bash
git --version
```

### GitHub CLI

Install from <https://cli.github.com/> and authenticate:

```bash
gh auth login
gh auth status
```

### Python 3.11 or newer

Verify:

```bash
python3 --version
```

### uv

Install using the official instructions at <https://docs.astral.sh/uv/getting-started/installation/>.

Verify:

```bash
uv --version
```

### Node.js LTS

Node is required for the Canvas extension and local process launcher. Install from <https://nodejs.org/>.

Verify:

```bash
node --version
npm --version
```

### GitHub Copilot App

Install and sign in using the official GitHub documentation:

- <https://docs.github.com/en/copilot/how-tos/github-copilot-app>

Confirm that you can:

- Open a local folder or GitHub repository.
- Start an agent session.
- Access `/create-canvas`.

### GitHub Copilot CLI

Follow:

- <https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/overview>

Verify that an interactive session starts successfully.

### One or both additional coding agents

The project can be completed with the Copilot App and one additional coding agent. Installing both is useful for independent review but not mandatory.

- Codex CLI: <https://developers.openai.com/codex/cli>
- Claude Code: <https://docs.anthropic.com/en/docs/claude-code/overview>

## 3. Recommended development tools

- VS Code for debugging and browser inspection.
- A Chromium-based browser for testing direct and iframe access.
- `curl` for endpoint and health checks.

Verify:

```bash
curl --version
```

## 4. Project initialization

```bash
mkdir canvas-dashlet-studio
cd canvas-dashlet-studio
git init
uv init --python 3.11
```

Add the initial Python dependencies:

```bash
uv add fastapi uvicorn httpx pydantic
uv add --dev pytest pytest-asyncio ruff
```

Initialize the minimal Node package only when starting the Canvas extension:

```bash
npm init -y
```

Avoid adding React, TypeScript or a bundler during the MVP.

## 5. Environment verification application

Create a temporary `verify_environment.py`:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return "<h1>Environment ready</h1>"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

Run:

```bash
uv run uvicorn verify_environment:app --port 8765
```

Verify:

```bash
curl http://127.0.0.1:8765/health
```

Open <http://127.0.0.1:8765/> in a browser.

Delete the temporary verification file after confirming the environment.

## 6. Render publication setup

Do not configure Render until the publication stage. At that point:

1. Push the project to GitHub.
2. Create a Render Web Service connected to the repository.
3. Use Python as the runtime.
4. Use the build command:

   ```bash
   pip install .
   ```

5. Use the start command:

   ```bash
   uvicorn gallery:app --host 0.0.0.0 --port $PORT
   ```

Official guide: <https://render.com/docs/deploy-fastapi>

## 7. Secrets and local configuration

- Store local values in an ignored `.env` only when required.
- Never embed secrets in dashlet Python, HTML or JavaScript.
- Never put tokens in published URLs.
- Use recorded fixtures in CI instead of calling external APIs.
- Generated dashlets may reference only registered data providers.

Add to `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
node_modules/
*.log
runtime/
```

## 8. Installation completion checklist

- [ ] Git works.
- [ ] GitHub CLI is authenticated.
- [ ] Python 3.11+ works.
- [ ] uv works.
- [ ] Node.js and npm work.
- [ ] Copilot App opens the repository.
- [ ] Copilot agent session starts.
- [ ] `/create-canvas` is available.
- [ ] At least one additional coding agent is available.
- [ ] FastAPI verification page opens.
- [ ] Health endpoint responds.

