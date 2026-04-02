# Live Model Validation

Stand der Analyse: 2026-04-02 (Europe/Berlin)

## Scope

Diese Datei dokumentiert ausschliesslich die Analyse des aktuellen Modells mit Live-Daten.

Keine Aenderungen wurden vorgenommen an:

- Modelllogik
- Gewichten
- Schwellen
- Scores
- Labels
- APIs
- Dokumentation ausserhalb dieser Datei

## Datengrundlage

- Codepfad geprueft:
  `scorer.run -> scorer.composite -> scoring.engine -> features.model_v2 -> labels.engine / regimes.hard_rules / stress.scenarios -> explain.engine`
- Aktuellster verifizierter Live-Run des deployten Systems:
  `2026-04-01T22:16:26.415842+00:00`
  Das entspricht `2026-04-02 00:16:26` in Europe/Berlin.
- Quelle fuer Live-Ergebnisse:
  deployte API unter `RAILWAY_API_URL`
- Stichprobe mit vollstaendigem Detailpfad:
  `SN51 lium.io`, `SN9 iota`, `SN64 Chutes`, `SN113 TensorUSD`, `SN67 Harnyx`

## Wichtige Einschraenkung

Der lokale direkte Chain-Pfad liess sich auf diesem Windows-Setup nicht nativ ausfuehren, weil `bittensor` bereits beim Import an `fcntl` scheitert. Fuer diese Validierung wurde daher der aktuelle deployte Live-Run des bestehenden Modells verwendet und der vollstaendige Entscheidungsweg anhand des unveraenderten Quellcodes zurueck auf Features, Block-Scores, Hard Rules, Stress-Tests und Label-Logik gemappt.

Das aendert nichts an der Modelllogik, ist aber wichtig fuer die Einordnung:

- die analysierten Ergebnisse sind echte Live-Ergebnisse des aktuellen Modells
- die Ausfuehrung kam aus dem laufenden Deploy statt aus einem lokalen Chain-Run

## Gesamtbild

Aktueller Live-Stand ueber alle 128 investierbaren Subnets:

- `Under Review`: 98
- `Fragile Yield Trap`: 18
- `Early Quality Build`: 7
- `Overrewarded Structure`: 5

Top 10 des Live-Runs:

- Rang 1: `SN51 lium.io` mit `63.34`, Label `Under Review`
- Rang 2: `SN4 Targon` mit `61.52`, Label `Under Review`
- Rang 3: `SN9 iota` mit `61.40`, Label `Early Quality Build`
- Rang 4: `SN64 Chutes` mit `61.06`, Label `Early Quality Build`

Zentrale Beobachtungen:

1. Das Ranking wird aktuell klar von Qualitaet, Struktur und niedriger Fragilitaet getragen, nicht primaer von Mispricing.
2. Das Label-System ist deutlich defensiver als das Ranking-System.
3. Ein grosser Score-Cluster liegt exakt bei `42.0`.
4. Die Verlaufshistorien mehrerer Top-Subnets zeigen trotz Stabilisierung noch sehr grosse Run-to-Run-Spruenge.

## Portfolio-weite Auffaelligkeiten

### 1. Starkes Ranking-/Label-Mismatch

Der hoechste Live-Score (`SN51`) ist `Under Review`.

Das ist kein Einzelfall:

- 98 von 128 Subnets sind `Under Review`
- gleichzeitig liegen mehrere `Under Review`-Subnets sehr weit oben im Ranking

Interpretation:

- Das Ranking bewertet stark `fundamental_health`, `market_legitimacy`, `structural_validity` und niedrige `fragility`
- Das Labeling verlangt zusaetzlich relativ harte qualitative Schwellen
- Dadurch entsteht ein System, das gute Subnets hoch rankt, aber sie semantisch oft nicht klar positiv labelt

Plausibilitaet:

- defensiv betrachtet plausibel
- aus Produktsicht potenziell verwirrend

### 2. Score-Kompression bei 42.0

Live wurden `26` Subnets exakt mit `42.0` bewertet:

- `15` davon `Fragile Yield Trap`
- `11` davon `Under Review`

Das ist sehr wahrscheinlich kein Zufall, sondern ein Cap-/Boundary-Effekt.

Beobachtung aus den Detailfaellen:

- `SN113` liegt exakt bei `42.0`
- dort ist `market_structure_floor_watchlist` aktiv
- diese Regel setzt `legacy_score_cap = 0.42`

Bewertung:

- als Schutzmechanismus plausibel
- fuer Ranking-Feinaufloesung unrobust
- Gefahr von kuenstlichen Gleichstaenden und schlechter Trennschaerfe im Mittelfeld

### 3. Hohe historische Volatilitaet trotz Stabilisierung

Mehrere Live-Beispiele zeigen starke Spruenge innerhalb weniger Runs:

- `SN51`: von ~`16-22` auf `63.34`
- `SN64`: von ~`43-70` auf `61.06`
- `SN113`: von ~`55.7` auf `23.5`, spaeter auf `42.0`

Bewertung:

- das Modell ist nicht komplett instabil
- aber die derzeitige History-Daempfung reicht bei mehreren Namen nicht aus, um sehr grosse Regimewechsel oder Daten-/Cap-Umschaltungen glattzuziehen

### 4. Stress-Output wirkt bei einigen fragilen Faellen zu mild

Beispiel:

- `SN113` ist Label `Fragile Yield Trap` mit `fragility_risk = 76.0`
- der Stress-Block klassifiziert trotzdem `fragility_class = robust`
- Max Drawdown nur `14.24`

Auch `SN67`:

- `fragility_risk = 88.0`
- Label `Overrewarded Structure`
- Stress nur `watchlist`

Bewertung:

- Das Stress-Modul liefert nuetzliche relative Richtungen
- Fuer sehr kleine/capped Pools scheint es die oekonomische Fragilitaet eher zu unterschaetzen

## Detailanalyse pro Subnet

### SN51 lium.io

Live-Endzustand:

- Score `63.34`
- Rang `1`
- Label `Under Review`
- `fundamental_quality = 74.52`
- `mispricing_signal = 34.47`
- `fragility_risk = 21.19`
- `signal_confidence = 44.47`
- keine aktiven Hard Rules

Input- und Featurebild:

- `active_ratio = 1.00`
- `participation_breadth = 0.7773`
- `reserve_depth = 95,484.95 TAO`
- `market_structure_floor = 0.8679`
- `crowding_proxy = 0.1970`
- `concentration = 0.4377`
- `slippage_50_tao = 0.00052`
- keine GitHub-Externals vorhanden

Pfad durch das Modell:

- sehr starke Qualitaets-Inputs heben `fundamental_health` auf `72.28`
- sehr starke Struktur hebt `market_legitimacy` auf `82.26`
- `opportunity_underreaction` ist nur `53.99`, also kein extremer Mispricing-Fall
- niedrige Fragilitaet und starke Struktur treiben den finalen Score hoch
- keine Hard Rules greifen
- das Label bleibt trotzdem `Under Review`

Warum `Under Review`?

- `signal_confidence = 44.47`
- `thesis_breakers` enthaelt:
  `Evidence quality is too weak or stale to rely on the current signal mix.`

Bewertung:

- Der Score selbst ist aus Sicht des Ranking-Moduls plausibel
- Das Label ist aus Sicht der Label-Logik ebenfalls plausibel
- Zusammen erzeugt es aber einen auffaelligen Widerspruch:
  bestes Ranking, aber kein klar investierbares Label

Moegliche Fehlbewertung:

- Wenn das Produkt Top-Raenge als investierbare Priorisierung lesen soll, wirkt Rang 1 + `Under Review` fragwuerdig
- Wenn das Produkt defensiv sein soll, ist eher das hohe Ranking als das Label zu aggressiv

### SN9 iota

Live-Endzustand:

- Score `61.40`
- Rang `3`
- Label `Early Quality Build`
- `fundamental_quality = 72.18`
- `mispricing_signal = 31.72`
- `fragility_risk = 23.70`
- `signal_confidence = 51.29`
- keine aktiven Hard Rules

Input- und Featurebild:

- `reserve_depth = 51,888.46 TAO`
- `market_structure_floor = 0.8442`
- `crowding_proxy = 0.2184`
- `concentration = 0.4851`
- `slippage_50_tao = 0.00096`
- GitHub-Externals formal vorhanden, aber `repo_commits_30d = 0`, `repo_contributors_30d = 0`

Pfad durch das Modell:

- starke Struktur und Qualitaet treiben `fundamental_health = 70.33`
- `market_legitimacy = 78.20`
- `opportunity_underreaction = 48.41`
- Mispricing bleibt also klar unterdurchschnittlich bis moderat
- trotzdem reicht die Kombination aus Qualitaet, geringer Fragilitaet und ausreichender Confidence fuer einen sehr hohen Endscore

Wichtiger Widerspruch:

- `thesis_breakers` enthaelt:
  `Usage is not retaining once incentives normalize, which weakens the structural thesis.`
- trotzdem Rang 3 und positives Label

Bewertung:

- intern konsistent als `quality-first`-Name
- potenziell fraglich, wenn der Score als Investment-Opportunity und nicht als Qualitaetsliste verstanden wird

Moegliche Fehlbewertung:

- hoher Rang trotz schwacher Mispricing-Komponente
- positives Label trotz explizitem Retention-Breaker

### SN64 Chutes

Live-Endzustand:

- Score `61.06`
- Rang `4`
- Label `Early Quality Build`
- `fundamental_quality = 75.07`
- `mispricing_signal = 25.92`
- `fragility_risk = 21.08`
- `signal_confidence = 56.23`
- keine aktiven Hard Rules

Input- und Featurebild:

- `reserve_depth = 216,778.41 TAO`
- `market_structure_floor = 0.8997`
- `market_relevance_proxy = 0.8747`
- `crowding_proxy = 0.1976`
- `concentration = 0.4391`
- `repo_commits_30d = 24`, `repo_contributors_30d = 3`, `repo_recency = 1.0`

Pfad durch das Modell:

- sehr starke Qualitaet und Marktstruktur
- `fundamental_health = 72.94`
- `market_legitimacy = 82.02`
- `opportunity_underreaction = 38.19`
- also noch schwaecheres Opportunity-Profil als bei `SN9`
- der Endscore bleibt trotzdem Top-5, weil die Ranking-Logik Qualitaet und Resilienz deutlich ueber Opportunity gewichtet

Bewertung:

- als Qualitaets-Subnet sehr plausibel
- als Opportunity-Subnet deutlich weniger plausibel

Moegliche Fehlbewertung:

- Top-Rang trotz `mispricing_signal = 25.92`
- `thesis_breakers` meldet ebenfalls fehlende Retention
- wenn der Score "alpha opportunity" meinen soll, ist `SN64` ein klarer Kandidat fuer Ueberbewertung

### SN113 TensorUSD

Live-Endzustand:

- Score `42.00`
- Rang `81`
- Label `Fragile Yield Trap`
- `fundamental_quality = 42.0`
- `mispricing_signal = 18.0`
- `fragility_risk = 76.0`
- `signal_confidence = 38.09`

Aktive Hard Rules:

- `small_pool_yield_intensity_caps_confidence`
- `extreme_yield_small_pool_caps_mispricing`
- `market_structure_floor_watchlist`
- `concentration_caps_fundamental_quality`
- `crowded_structure_evidence_watchlist`

Input- und Featurebild:

- `reserve_depth = 1,356.91 TAO`
- `staking_apy = 481.99%`
- `concentration = 0.7137`
- `crowding_proxy = 0.3249`
- `slippage_50_tao = 0.03685`

Pfad durch das Modell:

- Rohbild ist nicht voellig schlecht:
  `fundamental_health = 55.81`, `opportunity_underreaction = 49.33`
- dann greifen mehrere Caps
- Ergebnis: Qualitaet gedrueckt, Confidence gedrueckt, Mispricing gedrueckt, Fragility angehoben
- Endscore landet exakt auf `42.0`

Bewertung:

- die negative Richtung ist plausibel
- die Haerte des Score-Caps ist ebenfalls plausibel
- die exakte Landung auf `42.0` zeigt aber sehr klar Cap-Dominanz statt feiner Bewertung

Wichtige Inkonsistenz:

- Label: `Fragile Yield Trap`
- `fragility_risk = 76.0`
- Stress-Klasse trotzdem `robust`

Das spricht dafuer, dass der Stress-Block small-pool-Fragilitaet zu milde abbildet.

### SN67 Harnyx

Live-Endzustand:

- Score `7.85`
- Rang `127`
- Label `Overrewarded Structure`
- `fundamental_quality = 28.0`
- `mispricing_signal = 10.0`
- `fragility_risk = 88.0`
- `signal_confidence = 31.74`

Aktive Hard Rules:

- `thin_liquidity_caps_fragility`
- `micro_pool_apy_caps_total_score`
- `small_pool_yield_intensity_caps_confidence`
- `extreme_yield_small_pool_caps_mispricing`
- `fragile_repricing_blocks_top_mispricing`
- `elevated_yield_small_pool_caps_confidence`
- `market_structure_floor_watchlist`
- `concentration_caps_fundamental_quality`

Input- und Featurebild:

- `reserve_depth = 17.93 TAO`
- `staking_apy = 106,609.6%`
- `market_structure_floor = 0.5163`
- `concentration = 0.6568`
- `slippage_10_tao = 0.5579`
- `slippage_50_tao = 1.0`

Pfad durch das Modell:

- Roh-Mispricing waere eigentlich hoch:
  `opportunity_underreaction = 84.06`
- die Hard Rules zerlegen dieses Signal praktisch vollstaendig
- Endzustand ist stark negativ und bleibt es auch historisch sehr stabil

Bewertung:

- dieser Fall wirkt robust korrekt
- genau fuer solche extremen Mikro-Pools scheint die Hard-Rule-Schicht gut zu funktionieren

Restzweifel:

- Stress-Klasse nur `watchlist`, nicht `fragile`
- oekonomisch wirkt der Fall haerter als die Stress-Klassifikation

## Sensitivitaets- und Grenzfalltests

### A. Confidence-Grenze bei Top-Subnets

`SN51` liegt mit `signal_confidence = 44.47` nur knapp unter der wichtigen `45%`-Schwelle.

Weitere relevante Werte:

- `fundamental_quality = 74.52`
- `fundamental_health = 72.28`
- `fragility_risk = 21.19`
- `thesis_confidence = 51.31`
- `market_legitimacy = 82.26`
- `concentration = 43.77%`
- `crowding = 19.70%`

Damit liegt `SN51` sehr wahrscheinlich nur rund `0.53` Punkte Confidence von `Early Quality Build` entfernt.

Bewertung:

- sehr sensitiv an einer semantisch wichtigen Grenze
- kleiner Confidence-Shift kann das Label kippen, obwohl sich am Grundbild kaum etwas aendert

### B. Positive Top-Raenge trotz schwacher Mispricing-Werte

`SN9` und `SN64` sind gute Grenzfaelle:

- `SN9`: `mispricing_signal = 31.72`, Rang `3`
- `SN64`: `mispricing_signal = 25.92`, Rang `4`

Beide werden stark von Qualitaet und Struktur nach oben getragen.

Bewertung:

- robust, wenn der Score eher "durable subnet quality" meint
- problematisch, wenn der Score eher "current investment opportunity" meinen soll

### C. Cap-Grenze bei 42.0

Der `42.0`-Cluster ist ein echter Grenzfall im Live-System.

`SN113` zeigt exemplarisch:

- mehrere aktive Caps
- qualitative Bewertung klar negativ
- exakter Endscore `42.0`

Bewertung:

- Schutzwirkung vorhanden
- Trennschaerfe im Bereich cap-gebundener Mid-/Low-Names gering

### D. Mikro-Pool-Robustheit

`SN67` zeigt, dass ein einzelner positiver Opportunity-Block ein extrem fragiles Pool-Profil nicht mehr nach oben ziehen kann.

Bewertung:

- sehr robust
- hier scheint das Modell eher zu streng als zu locker
- das ist fuer diesen Fall wahrscheinlich richtig

### E. Stress-Modul an den Raendern

Grenzfall:

- `SN113`: Label `Fragile Yield Trap`, aber Stress-Klasse `robust`
- `SN67`: oekonomisch extrem fragil, aber Stress nur `watchlist`

Bewertung:

- die Stress-Szenarien unterscheiden Faelle noch
- die finale Fragilitaetsklasse wirkt an den Small-Pool-Raendern zu freundlich

## Plausibilitaet, Stabilitaet, Robustheit

### Plausibilitaet

Ueberwiegend plausibel:

- sehr tiefe Mikro-Pools werden konsequent negativ begrenzt
- starke, tiefe, liquide Subnets bekommen hohe Scores
- externe Datenlosigkeit drueckt Confidence sichtbar

Teilweise fraglich:

- Top-Raenge mit `Under Review`
- sehr hohe Raenge trotz klar schwacher Mispricing-Signale
- positive Labels trotz aktiver Thesis-Breaker wie fehlender Retention

### Stabilitaet

Mittel bis schwach:

- untere Extreme wie `SN67` sind stabil
- obere Raenge zeigen noch grosse historische Spruenge
- Caps machen einzelne Bereiche stabil, aber teilweise kuenstlich flach

### Robustheit

Gemischt:

- robust gegen offensichtliche Mikro-Pool-/Yield-Fallen
- weniger robust bei semantischen Grenzfaellen zwischen "guter Struktur" und "echter Opportunity"
- weniger robust bei der Uebersetzung von Ranking in nutzerverstaendliche Labels

## Faelle, in denen das Modell falsch liegen koennte

1. `SN51` koennte zu hoch ranken.
   Es ist strukturell stark, aber Rang 1 bei gleichzeitig `Under Review` ist ein echter Warnhinweis.

2. `SN9` und `SN64` koennten als Investment-Opportunity zu positiv dargestellt sein.
   Beide sehen eher nach Quality-Leaders als nach klarem Mispricing aus.

3. Der `42.0`-Cluster koennte Mid-Tier-Faelle falsch zusammenfassen.
   Verschiedene Subnets mit unterschiedlichen Risiken landen auf derselben Score-Decke.

4. Das Stress-Modul koennte Small-Pool-Fragilitaet unterschaetzen.
   Besonders sichtbar bei `SN113`.

## Fazit

Das aktuelle Live-Modell ist in den offensichtlichen Negativfaellen brauchbar defensiv und in den Qualitaetsfaellen intern weitgehend konsistent. Die groessten offenen Punkte liegen nicht in einem offensichtlichen Komplettversagen, sondern in drei systemischen Spannungen:

- Ranking ist aktuell deutlich positiver als Labeling
- Opportunity wird im Top-Ranking schwaecher gewichtet als Struktur/Qualitaet
- Caps erzeugen sichtbare Score-Kompression, vor allem bei `42.0`

## Moeglicher spaeterer Handlungsbedarf

Aus dieser Analyse ergibt sich spaeter potenzieller Handlungsbedarf in folgenden Bereichen:

- Abstimmung zwischen Ranking und Labeling
- Trennschaerfe bei cap-gebundenen Mid-Tier-Faellen
- Pruefung, ob Top-Raenge staerker echtes Mispricing verlangen sollten
- Pruefung, ob Stress-Klassen kleine, fragile Pools schaerfer bewerten sollten

In dieser Runde wurden bewusst keine Aenderungen umgesetzt.
