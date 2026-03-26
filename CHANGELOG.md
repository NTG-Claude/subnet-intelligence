# Changelog

## v1.0.0 — Initial Release (2026-03-26)

### Added
- **5 automated signals** from Taostats + GitHub API:
  - Capital Conviction (25 pts) — net flow, stakers, liquidity
  - Network Activity (25 pts) — miner growth, registrations, weight commits
  - Emission Efficiency (20 pts) — market cap per unit of emission
  - Distribution Health (15 pts) — Gini coefficient + stake concentration
  - Dev Activity (15 pts) — GitHub commits + contributors
- **Composite Score 0–100** for all Bittensor subnets, percentile-ranked cross-subnet
- **REST API** (FastAPI) with 7 endpoints, CORS, rate-limiting, 1h response cache
- **Next.js 14 Dashboard** — dark mode, score gauges, 30-day history charts, leaderboard
- **SQLite/PostgreSQL** persistence with Alembic migrations
- **Daily GitHub Actions** cron at 06:00 UTC with log artifacts
- **Test suite** — 114 tests, 83% coverage
- **Makefile** for common dev tasks
- **scheduler.py** for self-hosted daily runs with retry + webhook alerts

### Architecture
- `scorer/` — pure Python signal functions + async orchestrator
- `api/` — FastAPI app with Pydantic-validated responses
- `frontend/` — Next.js SSR with Recharts
- `.github/workflows/` — CI (test + coverage) + daily scoring cron
