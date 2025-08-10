### Crew AI PM Agent on Docker with GPT-OSS

This guide shows how to run the PM Agent system in Docker and connect it to a local OpenAI-compatible GPT-OSS model served via Docker Models. It also includes an optional Next.js frontend using Tailwind/ShadCN UI.

#### Prerequisites
- Docker (Docker Desktop 4.33+ or recent Docker Engine)
- Access to Docker Models (enables `docker model run`)
- GitHub Personal Access Token and Slack Bot Token (optional but recommended)

#### Quick Start (Backend only)
1) Start the GPT-OSS model server (OpenAI-compatible API)
```bash
docker model run ai/gpt-oss -p 8000:8000
```
- This exposes an OpenAI-compatible API at `http://localhost:8000/v1`.

2) Configure environment for the app
```bash
cp config.example.env .env
# Edit .env and set at minimum:
# OPENAI_BASE_URL=http://host.docker.internal:8000/v1
# OPENAI_MODEL=ai/gpt-oss
# OPENAI_API_KEY=anything_non_empty_if_not_required
```

3) Build and run the backend container
```bash
docker compose up --build app
# Backend web dashboard will be at http://localhost:8001/
```

#### With Frontend (ShadCN UI, Next.js)
- Build and run both services:
```bash
docker compose up --build
# Frontend: http://localhost:3000
# Backend API: http://localhost:8001
```
- The frontend uses Tailwind with ShadCN-compatible tokens. You can add ShadCN components via:
```bash
cd web-frontend
npm install
npx shadcn@latest init
npx shadcn@latest add button card input textarea badge
```
- Update `app/page.tsx` to use the imported components.

#### Troubleshooting
- If the frontend cannot reach the backend, ensure CORS is enabled (it is) and that `NEXT_PUBLIC_API_BASE` is set to `http://app:8001` in the container (configured in compose) or `http://localhost:8001` locally.
- If the backend fails to connect to the model, verify `OPENAI_BASE_URL` and that the model is running.

#### Environment Variables
- OPENAI_BASE_URL: OpenAI-compatible endpoint base URL (e.g., `http://host.docker.internal:8000/v1`)
- OPENAI_MODEL: Model ID expected by the endpoint (e.g., `ai/gpt-oss`)
- OPENAI_API_KEY: Any non-empty string if the local server does not require auth
- GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO: For GitHub integration
- SLACK_BOT_TOKEN: For Slack notifications
- See `config.example.env` for all supported variables

#### Networking Notes
- The compose file maps `host.docker.internal` to the host gateway so the container can reach the host-exposed model on Linux.
- If `host.docker.internal` is not available in your environment, replace it with your host IP (e.g., `http://172.17.0.1:8000/v1`).

#### References
- GPT-OSS announcement: `https://openai.com/index/introducing-gpt-oss/`

You’re set—start the model, set `.env`, and `docker compose up`.