# SUVASTU

Project spec and setup guide: docs/suvastu-setup.md (single source of truth).
Env template: docs/.env.example. Real env: ./.env (already filled by the owner).

## Rules
- Never overwrite, recreate or print the contents of ./.env. Read variable NAMES only.
- If a new env var is needed, add it to docs/.env.example and tell the owner.
- Follow the repo layout, ports and service names in docs/suvastu-setup.md exactly.
- Frontend map library is Mapbox GL JS v3 (not MapLibre). No Google Earth Engine.
- Stack: PostGIS 17, Express 5 (ESM, plain JS), React 19 + Vite + Tailwind v4, TiTiler, Python 3.12 worker.
- Everything runs in Docker Compose; verify with `docker compose ps` and the health endpoint.
- Large data goes in data/raw and data/cogs (gitignored). Never commit data or secrets.
- Commit after each working milestone with a clear message.
