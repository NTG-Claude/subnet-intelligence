# Subnet Intelligence — Projektkontext für Claude Code

## Zweck
Automatisiertes Bittensor Subnet Scoring-System für Investoren.
Scores basieren ausschliesslich auf frei verfügbaren, automatisierbaren Daten.

## Architektur
```
scorer/             Python-Package für Signal-Berechnung und Orchestrierung
  taostats_client.py  Async API-Client (8 Endpoints, Rate-Limit, Cache, Retry)
  github_client.py    GitHub API (Commits, Contributors, Repo-Stats)
  subnet_github_mapper.py  netuid → (owner, repo) mit Override-Support
  signals.py          5 reine Signalfunktionen (0.0–1.0 je)
  normalizer.py       percentile_rank() — min→0, max→1, ties→average
  composite.py        compute_all_subnets() — orchestriert alles parallel
  database.py         SQLAlchemy ORM + 6 Query-Funktionen
  run.py              CLI Entry-Point (argparse)
  scheduler.py        Tagesplaner via schedule-library + Webhook-Alerts

api/                FastAPI REST-Endpunkte
  main.py             7 Endpoints, CORS, slowapi Rate-Limit, fastapi-cache2
  models.py           Pydantic Response-Modelle
  dependencies.py     DB-Session Injection

frontend/           Next.js 14 Dashboard
  app/page.tsx        Hauptdashboard (Top-3, Histogramm, Tabelle, Zombie-Warning)
  app/subnets/[netuid]/page.tsx  Detail (Gauge, Breakdown, History-Chart)
  components/SubnetTable.tsx     Sortierbar, paginiert, Suchfeld
  components/ScoreGauge.tsx      SVG-Ring, Farbcodierung, Confidence-Indikator
  components/SignalBreakdown.tsx 5 Balken mit Erklärungen

.github/workflows/
  daily-score.yml   Cron 06:00 UTC + workflow_dispatch
  test.yml          CI auf Push/PR, Coverage ≥80%

data/
  subnet_scores.db          SQLite (lokal)
  github_map.json           Cache netuid → (owner, repo)
  github_map_overrides.json Manuelle Overrides (SN3, SN4, SN64 bekannt)
```

## Score-Formel v1
```
score = capital(25) + activity(25) + efficiency(20) + health(15) + dev(15)
```
Jede Dimension ist percentile-ranked über alle aktiven Subnets (0.0–1.0 → gewichtet).

## Deployment
| Dienst    | Plattform | URL                              |
|-----------|-----------|----------------------------------|
| Datenbank | Supabase  | (DATABASE_URL in GitHub Secrets) |
| API       | Railway   | uvicorn api.main:app --port $PORT |
| Frontend  | Vercel    | NEXT_PUBLIC_API_URL → Railway URL |

## API Keys (in .env, niemals committen)
- `TAOSTATS_API_KEY`  — dash.taostats.io
- `GITHUB_TOKEN`      — github.com/settings/tokens (read:repo)
- `DATABASE_URL`      — PostgreSQL Connection String (Supabase/Railway)
- `ALERT_WEBHOOK_URL` — Optional, Slack/Discord Webhook für Fehlerbenachrichtigungen

## Befehle
```bash
make score           # alle Subnets berechnen
make score-dry       # trocken (kein DB-Write)
make score-netuid NETUID=4   # einzelnes Subnet
make api             # uvicorn api.main:app --reload
make frontend        # cd frontend && npm run dev
make test            # pytest tests/ -v
make migrate         # alembic upgrade head
make migrate-new MSG="add column"
make scheduler       # täglichen Scheduler starten
```

## Wichtige Prinzipien
1. Alle Scores deterministisch und reproduzierbar
2. Jedes Signal hat eine klare Datenquelle (Taostats oder GitHub API)
3. Kein manueller Input — alles automatisiert
4. Score-Methodik ist öffentlich dokumentiert (kein Black Box)
5. Backward-compatible: neue Signale dürfen alte Scores nicht brechen
6. Fehler werden geloggt, stoppen nicht den Gesamt-Run (`None` statt Exception)

## Bekannte Eigenheiten & Fallstricke
- **fastapi vs bittensor**: `bittensor 8.0.0` erwartet `fastapi~=0.110.1`, wir nutzen 0.135+.
  Falls bittensor im selben venv → `fastapi~=0.110.1` in requirements.txt pinnen.
- **Taostats Response-Format**: Endpunkte geben teils `[...]` teils `{"data": [...]}` zurück.
  `taostats_client.py` normalisiert beide Formate.
- **GitHub Repos in Identity**: Viele Subnets hinterlegen kein GitHub-URL in ihrer On-Chain Identity.
  Manuelle Overrides in `data/github_map_overrides.json`.
- **percentile_rank Formel**: `(2*below + equal - 1) / (2*(n-1))` — garantiert min→0, max→1.
  Nicht `below/n` (gibt max nie 1.0).
- **fastapi-cache2 + slowapi Reihenfolge**: `@cache` muss VOR `@limiter.limit` stehen.
- **pytest asyncio**: `asyncio_mode = strict` in pyproject.toml → alle async Tests brauchen `@pytest.mark.asyncio`.

## Bekannte Limitierungen
- Externer Revenue nicht messbar (strukturell off-chain)
- GitHub-Repos nicht immer in Subnet-Identity hinterlegt
- Staking-Manipulation durch koordinierte Wallets nicht erkennbar
- composite.py nutzt `miner_count` aus HistoryPoint — Taostats gibt dieses Feld ggf. anders.
  Bei Live-Daten Feldnamen in `get_subnet_history()` Response prüfen.

## Nächste geplante Verbesserungen
# v1.1 — Token Velocity (volume_24h / market_cap, 10 Punkte)
# v1.2 — Subnet Maturity Score (Alter vs. Score-Trend)
# v1.3 — Cross-Subnet Validator Overlap
# v2.0 — PostgreSQL für Produktion, Redis-Cache für API
