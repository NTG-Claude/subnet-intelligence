# Investment Framework Migration

## Bisherige Architektur

Das bisherige System war um ein heuristisches Multi-Achsen-Scoring gebaut:

- `features/metrics.py` berechnete Rohmetriken und normalisierte sie global.
- `scoring/engine.py` verdichtete diese Metriken in alte Achsen wie `intrinsic_quality`, `economic_sustainability`, `reflexivity`, `stress_robustness` und `opportunity_gap`.
- Ein dominanter Gesamtscore fungierte intern und extern als zentrale Wahrheit.
- Explainability, Labels, Backtests, API und Frontend hingen implizit an diesem Legacy-Composite.

Das führte zu drei Kernproblemen:

- `opportunity_gap` war zu stark algebraisch aus anderen Achsen abgeleitet statt ein eigenes Erwartungslücken-Signal zu sein.
- Fragility und Confidence waren keine First-Class Outputs.
- Die Architektur war eher ein gutes Research-Ranking als ein investmentorientiertes Entscheidungsmodell.

## Neue Architektur

Das System ist jetzt um vier Primärsignale herum aufgebaut:

- `fundamental_quality`
- `mispricing_signal`
- `fragility_risk`
- `signal_confidence`

Die Architekturänderung verläuft bewusst top-down:

- `features/metrics.py` erzeugt jetzt nicht nur statische Level-Signale, sondern auch Veränderungs-, Beschleunigungs-, Persistenz- und Divergenzmerkmale.
- Die Feature-Normalisierung ist cohort-aware und ergänzt Peer-Relative Kanten innerhalb von Liquiditäts-/Reife-Buckets.
- `scoring/engine.py` behandelt die vier Primärsignale als zentrale Wahrheit.
- Legacy-Achsen und Legacy-Composite werden nur noch aus diesen Primärsignalen abgeleitet.
- `regimes/hard_rules.py` arbeitet jetzt direkt auf Quality-, Mispricing-, Fragility- und Confidence-Constraints.
- `explain/engine.py` beantwortet Investment-Fragen statt nur Komponenten aufzuzählen.
- `backtests/engine.py` ist auf investmentnähere Zielgrößen und Interfaces für spätere echte Targets ausgerichtet.

## Wichtigste Entscheidungen

### 1. Legacy-Kompatibilität bleibt erhalten, aber nur als Layer

Bestehende API- und UI-Consumer bekommen weiterhin:

- `score`
- `breakdown`
- Legacy-Komponenten in `analysis.component_scores`

Diese Werte werden aber jetzt aus den neuen Primärsignalen abgeleitet statt umgekehrt.

### 2. Mispricing wurde als Divergenzmodell aufgebaut

`mispricing_signal` basiert jetzt stärker auf nicht eingepreister struktureller Verbesserung:

- `quality_acceleration`
- `liquidity_improvement_rate`
- `concentration_delta`
- `validator_diversity_trend`
- `price_response_lag_to_quality_shift`
- `emission_to_sticky_usage_conversion`
- `post_incentive_retention`
- `reserve_growth_without_price`
- `participation_without_crowding`

Der Fokus liegt damit auf Erwartungslücken, Verzögerung und Veränderung statt nur auf Levels.

### 3. Fragility ist explizit und nicht mehr nur implizite Schwäche

`fragility_risk` bündelt jetzt unter anderem:

- dünne Liquidität
- Konzentration
- Crowding
- emission-getriebene Verzerrungen
- Preisreaktionen ohne Qualitätsverbesserung
- Reversal-Risiken

Stress-Tests verschärfen das Fragility-Signal zusätzlich, statt es zu ersetzen.

### 4. Confidence ist ein eigener Research-Output

`signal_confidence` berücksichtigt jetzt:

- Datenabdeckung
- History-Tiefe
- Frische
- Proxy-Abhängigkeit
- manipulationsärmere Signalanteile

Externe Proxy-Signale wie GitHub fließen weiterhin ein, sind aber explizit nur schwache Confidence-Bausteine.

### 5. Peer-relative Sicht wurde pragmatisch ergänzt

Statt eines Großumbaus auf komplexe Clustering-Architektur wurde eine pragmatische cohort-aware Erweiterung eingebaut:

- Buckets nach Liquiditätstiefe und Reifegrad
- cohort-relative Edges für Quality, Liquidity und Mispricing

Damit erkennt das Modell besser "best in cohort", ohne die bestehende Struktur zu sprengen.

## Migrationshinweise

### Für Backend-Consumer

Bevorzugt künftig:

- `analysis.primary_outputs.fundamental_quality`
- `analysis.primary_outputs.mispricing_signal`
- `analysis.primary_outputs.fragility_risk`
- `analysis.primary_outputs.signal_confidence`

Legacy-Felder bleiben verfügbar, sind aber Kompatibilitätswerte:

- `score`
- `breakdown`
- `analysis.component_scores`

### Für Explainability-Consumer

Neu hinzugekommen sind unter anderem:

- `analysis.why_mispriced`
- `analysis.risk_drivers`
- `analysis.confidence_rationale`
- `analysis.quality_rationale`
- `analysis.thesis_breakers`

### Für Backtests

Backtests liefern jetzt zielnähere Felder:

- `relative_forward_return_vs_tao_30d`
- `relative_forward_return_vs_tao_90d`
- `drawdown_risk`
- `liquidity_deterioration_risk`
- `concentration_deterioration_risk`

Aktuell sind diese Targets noch proxy-basiert, aber die Architektur ist so gebaut, dass echte TAO-relative Targets später ohne erneuten Großumbau nachgerüstet werden können.

## Research Page Contract

Die Haupttabelle bleibt bewusst score-basiert und dient weiter als Front Door.
Die Detailseite liefert dagegen die kompakte Research-Interpretation, ohne mit
Debug-Rohdaten zu eroeffnen.

Das neue Top-Layer fuer `/api/v1/subnets/{netuid}` ist `research_summary`. Es
nutzt bewusst nicht-personalisierte, deskriptive Sprache und verdichtet die
vorhandenen V2-Signale in wenige direkt lesbare Felder:

- `setup_status`: `strong_setup | improving_setup | fragile_setup | not_investable`
- `setup_read`
- `why_now`
- `main_constraint`
- `break_condition`
- `market_capacity`: `very_low | low | medium | high`
- `evidence_strength`: `high | medium | low`
- `relative_peer_context`

UI-Prinzipien fuer die Research-Seite:

- oben nur die kompakte Summary und die vier Primaersignale
- darunter die Interpretationsebene
- tiefe Contributors, Stress-Szenarien, Conditioning und Raw Context bleiben zugaenglich, aber sekundaer
- die Research-Seite selbst ist jetzt als Memo aufgebaut:
  kompakter Header, ein einheitlicher Executive-Summary-Block, ein zentraler
  Signal-Strip, eine kleine Context Row, danach genau zwei kuratierte
  Hauptsektionen fuer `Market Structure` und `Evidence And Reliability`
- die Score-Erklaerung im Hauptfluss wurde bewusst auf `Top 3 Supports` und
  `Top 3 Drags` reduziert; groessere Contributor-Dumps leben nur noch in den
  Diagnostics
# Scoring refinement note

The current scoring framework still keeps the main score as the primary ranking anchor, but the screening logic is now intentionally less permissive in two places:

- weak evidence bites harder, so shallow history, reconstructed inputs, proxy-heavy reads, and weak telemetry compress both confidence and score interpretation
- investability is treated as a lightweight overlay, so thin liquidity, narrow participation, concentration, and weak market structure can cap or discount otherwise attractive-looking setups

This is an incremental refinement rather than a replacement of the score system. The main page remains score-led, while deeper interpretation can still expand on the underlying setup quality later.
