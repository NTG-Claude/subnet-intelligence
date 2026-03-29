# Subnet Intelligence — Projektkontext für Claude Code

## Zweck
Automatisiertes Bittensor Subnet Scoring-System für Investoren.
Scores basieren ausschliesslich auf frei verfügbaren, automatisierbaren Daten.

## Architektur
```
scorer/             Python-Package für Signal-Berechnung und Orchestrierung
  bittensor_client.py  On-chain Daten via bittensor SDK (Finney mainnet, kein API-Key)
                       - SubnetMetrics: n_total, n_active_7d, total_stake_tao, unique_coldkeys,
                         top3_stake_fraction, emission_per_block_tao, incentive_scores, n_validators
                       - SubnetIdentity: name, github_url, website
                       - threading.local() für Subtensor-Reuse, asyncio.Semaphore(6) für Concurrency
  coingecko_client.py  TAO/USD Preis (CoinGecko Free API, 1h Cache, kein API-Key)
  github_client.py     GitHub API (Commits, Contributors, Repo-Stats)
  subnet_github_mapper.py  netuid → (owner, repo) mit Override-Support
  signals.py           5 reine Signalfunktionen (0.0–1.0 je), Score v2 Signaturen
  normalizer.py        percentile_rank() — min→0, max→1, ties→average
  composite.py         compute_all_subnets() — orchestriert alles parallel, SCORE_VERSION="v2"
  database.py          SQLAlchemy ORM + 6 Query-Funktionen
  run.py               CLI Entry-Point (argparse)
  scheduler.py         Tagesplaner via schedule-library + Webhook-Alerts

api/                FastAPI REST-Endpunkte
  main.py             7 Endpoints, CORS, In-Memory Rate-Limit
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

## Score-Formel v2
```
score = capital(25) + activity(25) + efficiency(20) + health(15) + dev(15)

capital    = 0.6 * percentile(total_stake_usd) + 0.4 * percentile(unique_coldkeys)
activity   = 0.6 * percentile(n_active_7d / n_total) + 0.4 * percentile(n_validators)
efficiency = percentile(total_stake_tao / emission_per_block_tao)
health     = 0.5 * (1 - gini(incentives)) + 0.5 * (1 - top3_stake_fraction)
dev        = 0.6 * percentile(commits_30d) + 0.4 * percentile(unique_contributors_30d)
```
Jede Dimension ist percentile-ranked über alle aktiven Subnets (0.0–1.0 → gewichtet).

## Deployment
| Dienst    | Plattform | URL                              |
|-----------|-----------|----------------------------------|
| Datenbank | Supabase  | Transaction Pooler, Port 6543, postgres.PROJECT_REF als User |
| API       | Railway   | uvicorn api.main:app --port $PORT |
| Frontend  | Vercel    | NEXT_PUBLIC_API_URL → Railway URL |

## API Keys (in .env, niemals committen)
- `GITHUB_TOKEN`      — github.com/settings/tokens (read:repo)
- `DATABASE_URL`      — PostgreSQL Connection String (Supabase Transaction Pooler)
- `ALERT_WEBHOOK_URL` — Optional, Slack/Discord Webhook für Fehlerbenachrichtigungen
- ~~TAOSTATS_API_KEY~~ — entfernt, kein API-Key mehr nötig (bittensor SDK + CoinGecko)

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
2. Jedes Signal hat eine klare Datenquelle (Bittensor on-chain oder GitHub API)
3. Kein manueller Input — alles automatisiert
4. Score-Methodik ist öffentlich dokumentiert (kein Black Box)
5. Backward-compatible: neue Signale dürfen alte Scores nicht brechen
6. Fehler werden geloggt, stoppen nicht den Gesamt-Run (`None` statt Exception)

## Bekannte Eigenheiten & Fallstricke
- **fastapi vs bittensor**: `bittensor 8.x` erwartet `fastapi~=0.110.1`.
  requirements.txt ist auf `fastapi>=0.110.1,<1.0.0` gepinnt.
- **bittensor SDK Semaphore**: `asyncio.Semaphore` in bittensor_client.py wird lazy initialisiert
  (innerhalb des laufenden Event Loops), da module-level Semaphore in Python <3.10 Probleme macht.
- **emission_value in rao**: `SubnetInfo.emission_value` ist in rao (1 TAO = 1e9 rao).
  Konvertierung: `emission_per_block_tao = emission_value / 1e9`.
- **GitHub Repos in Identity**: Viele Subnets hinterlegen kein GitHub-URL in ihrer On-Chain Identity.
  Manuelle Overrides in `data/github_map_overrides.json`.
- **percentile_rank Formel**: `(2*below + equal - 1) / (2*(n-1))` — garantiert min→0, max→1.
  Nicht `below/n` (gibt max nie 1.0).
- **Supabase Transaction Pooler**: DATABASE_URL muss Port 6543 + `postgres.PROJECT_REF` als Username nutzen.
  Session Pooler Port 5432 oder direct connection führen zu IPv4-Problemen auf GitHub Actions.
- **pytest asyncio**: `asyncio_mode = strict` in pyproject.toml → alle async Tests brauchen `@pytest.mark.asyncio`.

## Bekannte Limitierungen
- Externer Revenue nicht messbar (strukturell off-chain)
- GitHub-Repos nicht immer in Subnet-Identity hinterlegt
- Staking-Manipulation durch koordinierte Wallets nicht erkennbar
- bittensor metagraph: n_active_7d basiert auf `last_update` Block — misst Gewichtssets, nicht Miner-Aktivität

## dTAO Pool-Daten (seit Feb 2025 on-chain)
Jedes Subnet hat ein eigenes AMM mit zwei Reservoirs:
- `SubtensorModule.SubnetTAO`      — TAO-Reserven im Pool (rao, /1e9 → TAO)
- `SubtensorModule.SubnetAlphaIn`  — Alpha-Reserven im Pool (rao, /1e9 → Alpha)
- `SubtensorModule.SubnetAlphaOut` — Alpha ausserhalb des Pools (Emissionen + Entnahmen)
Alpha-Preis in TAO = SubnetTAO / SubnetAlphaIn (konstantes Produkt AMM)
Staking-APY = (emission_per_block_tao * BLOCKS_PER_DAY * 365) / tao_in_pool * 100

## Roadmap
### v3.0 — dTAO Market Data (aktiv in Entwicklung)
- SubnetMetrics: alpha_price_tao, tao_in_pool, alpha_in_pool, market_cap_tao, staking_apy
- DB: neue Spalten, Alembic-Migration
- API: SubnetSummary + SubnetDetail um dTAO-Felder erweitert
- Frontend: Alpha-Preis + APY-Spalte in Tabelle, Score-Trend-Indikator

### v3.1 — Score-Trend & Flows
- Score-Trend-Pfeil in Haupttabelle (7-Tage-Delta aus history)
- Net-Stake-Flow: daily snapshot → 7d/30d Delta sichtbar machen

### v3.2 (future)
- Cross-Subnet Validator Overlap
- Redis-Cache für API
- WebSocket Live-Updates
