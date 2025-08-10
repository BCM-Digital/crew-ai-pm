### Crew AI PM Agent on Docker with GPT-OSS

This guide shows how to run the PM Agent system in Docker and connect it to a local OpenAI-compatible GPT-OSS model served via Docker Models.

#### Prerequisites
- Docker (Docker Desktop 4.33+ or recent Docker Engine)
- Access to Docker Models (enables `docker model run`)
- GitHub Personal Access Token and Slack Bot Token (optional but recommended)

#### Quick Start
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
# GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO (if using GitHub features)
# SLACK_BOT_TOKEN (if posting to Slack)
```

3) Build and run the app container
```bash
docker compose up --build
```
- The default command runs the interactive CLI. Examples:
```bash
# Show config
docker compose run --rm app python main.py config
# Start interactive CLI
docker compose run --rm app python main.py interactive
```

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

#### Troubleshooting
- Model not reachable: Confirm the model container is running and `curl http://localhost:8000/v1/models` works on the host.
- Connection refused in container: Verify `OPENAI_BASE_URL` uses `host.docker.internal` (or correct host IP) and port mapping `-p 8000:8000` is set.
- Auth errors: If your local endpoint requires a key, set `OPENAI_API_KEY` accordingly.
- Missing deps in host environment: Prefer running inside Docker.

#### References
- GPT-OSS announcement: `https://openai.com/index/introducing-gpt-oss/`

You’re set—start the model, set `.env`, and `docker compose up`.