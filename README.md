# Hoverin DroneOps AI

Product specification for an evidence-based flight intelligence workspace for drone operators, engineers, manufacturers, service companies, and maintenance teams.

## 1. Product Summary

Drone flight logs contain valuable telemetry, but interpreting them currently requires specialist knowledge, manual graph inspection, and correlation across many signals. Hoverin DroneOps AI turns raw PX4, ArduPilot, and compatible flight logs into a searchable engineering workspace.

The product must help a user answer three questions quickly:

1. What happened during this flight?
2. Why did it happen, and what evidence supports that conclusion?
3. What should the team do next?

The system is an analysis assistant, not an autonomous flight-safety authority. It must show evidence, confidence, data gaps, and the difference between an observation and a recommendation.

## 2. Goals and Non-goals

### Goals

- Reduce first-pass log review from hours to minutes.
- Detect and prioritize meaningful anomalies across correlated telemetry.
- Let engineers ask natural-language questions against flight evidence.
- Make every answer traceable to signals, timestamps, parameters, or maintenance records.
- Build a searchable history of flights, aircraft, batteries, components, and findings.
- Produce concise reports that can be shared with engineering and operations teams.

### Non-goals for the MVP

- Controlling a drone or changing flight-controller parameters automatically.
- Replacing a certified safety review or a human sign-off.
- Supporting every proprietary log format on day one.
- Making deterministic claims when required data is missing or corrupted.
- Training a new foundation model. The MVP may use a hosted model behind a provider abstraction.

## 3. Target Users

| User | Primary job | Success measure |
| --- | --- | --- |
| Manufacturer engineer | Troubleshoot field failures and regressions | Find probable root cause with evidence |
| Fleet/service manager | Triage many flights and maintenance work | Prioritize the right aircraft and components |
| Drone operator | Understand abnormal flights without deep analysis expertise | Get a clear, actionable explanation |
| Maintenance technician | Decide what to inspect or replace | Receive component-specific recommendations |
| R&D / validation engineer | Compare test flights and firmware versions | Detect trends and regressions across cohorts |
| Research or training user | Explore telemetry and flight dynamics | Learn from transparent, inspectable analysis |

## 4. Core User Journeys

### 4.1 Analyze a flight

1. User uploads a `.ulg`, `.bin`, `.log`, `.csv`, or `.json` file.
2. System validates file type, size, parser support, and integrity.
3. System creates a flight record and shows processing progress.
4. Parser maps raw messages into normalized telemetry channels and metadata.
5. Analysis engine computes health metrics, events, anomalies, and confidence.
6. User lands on a flight summary with severity-ranked findings.
7. User opens any finding to inspect the graph, evidence, timeline, and recommendation.

### 4.2 Investigate an anomaly

1. User selects an anomaly such as motor temperature spike or GPS degradation.
2. System shows the affected time window and related signals on a synchronized chart.
3. Evidence includes exact values, baselines, thresholds, and data quality.
4. User can ask a follow-up question scoped to the flight or anomaly.
5. User can assign status, owner, note, or maintenance action.

### 4.3 Ask the assistant

1. User asks a natural-language question from the workspace or flight view.
2. System identifies the relevant flight, time range, channels, and records.
3. Retrieval supplies only available evidence to the language model.
4. Assistant responds with a conclusion, supporting evidence, uncertainty, and sources.
5. User can copy the answer into a report or open the referenced telemetry window.

### 4.4 Monitor fleet health

1. User opens the overview dashboard for a workspace and time range.
2. System displays analyzed flights, flight hours, anomaly counts, and fleet health.
3. User filters by aircraft, pilot, mission, firmware, battery, severity, or date.
4. User compares trends and identifies repeated component or operational issues.

### 4.5 Generate a report

1. User selects a flight, anomaly set, or date range.
2. System builds a report containing summary, evidence, charts, findings, and recommendations.
3. User reviews and edits the report title, audience, and notes.
4. User exports PDF and JSON, with a stable link to the underlying analysis.

## 5. MVP Scope

### In scope

- Workspace dashboard and recent flight history.
- Upload and parse CSV, JSON, PX4 ULog, and ArduPilot DataFlash logs.
- Normalized flight metadata and telemetry channel catalog.
- Flight summary with timeline and severity-ranked anomalies.
- Initial detectors for battery, motor/ESC, GPS, IMU/vibration, EKF, altitude, velocity, attitude, RC link, failsafe, temperature, and flight mode events.
- Natural-language Q&A grounded in the selected workspace data.
- Evidence citations to telemetry channel and time range.
- Anomaly status, assignee, notes, and maintenance recommendation.
- Text/PDF report export.
- Workspace members with Operator, Engineer, Maintenance, and Administrator roles.

### Later releases

- Automated fleet baselines per aircraft model and component.
- Firmware regression comparisons and test-flight cohorts.
- Battery cycle-life prediction and remaining useful life.
- Webhooks, Slack/Teams alerts, and ticketing integrations.
- S3-compatible ingestion, scheduled imports, and organization-level tenancy.
- Offline/on-premise inference for sensitive programs.

## 6. Functional Requirements

### Dashboard

- Show date range and workspace selector.
- Show flights analyzed, flight hours, anomalies, and fleet health.
- Show recent flights with ID, mission, date, aircraft, status, and anomaly count.
- Show priority anomalies with severity and direct navigation to evidence.
- Show analysis freshness and parser/model version.

### Flight ingestion

- Accept a configurable maximum file size, default 500 MB for MVP.
- Reject unsupported extensions and malformed payloads with an actionable error.
- Preserve the original file checksum and never mutate the source artifact.
- Detect duplicate uploads by workspace and checksum.
- Show `queued`, `parsing`, `analyzing`, `complete`, and `failed` states.
- Allow retry without creating duplicate flight records.

### Flight detail

- Display aircraft, pilot, mission, firmware, start/end time, duration, distance, and parser status.
- Display overall health and a human-readable executive summary.
- Provide synchronized time-series charts with zoom, pan, range selection, and channel toggles.
- Display an event timeline for takeoff, landing, mode changes, failsafes, GPS changes, and detected anomalies.
- Allow export of the selected chart range and underlying data.

### Anomalies

Every anomaly must include:

- Stable ID, type, severity, status, and confidence.
- Start/end timestamp and affected flight.
- Human-readable observation.
- Supporting channels, values, baseline, and threshold.
- Likely contributing factors, clearly labeled as hypotheses.
- Recommended next action.
- Model and detector version.
- Links to source records and chart windows.

Statuses are `open`, `acknowledged`, `in_review`, `resolved`, and `dismissed`. Dismissal requires a reason.

### Assistant

- Scope questions to the current flight by default and allow fleet-wide scope explicitly.
- Answer only from retrieved evidence and state when evidence is insufficient.
- Distinguish observed facts, inferred causes, and recommendations.
- Include source labels, channel names, and timestamps.
- Never invent telemetry values, maintenance history, or aircraft context.
- Preserve conversation history per flight and allow starting a new thread.
- Log model, prompt context identifiers, retrieval sources, and latency for auditability without storing secrets.

### Reports

- Include report title, author, generation time, flight scope, software versions, summary, findings, evidence, recommendations, and reviewer notes.
- Include severity and confidence for each finding.
- Include a disclaimer that recommendations require qualified human review.
- Export a stable, reproducible snapshot rather than a live dashboard view.

### Access control

- Administrator: workspace, member, retention, and integration management.
- Engineer: full flight analysis, anomaly review, reports, and notes.
- Maintenance: flight evidence, assigned findings, status updates, and notes.
- Operator: upload flights, view own/team flights, ask questions, and create reports.
- Every read and write must be scoped to a workspace.

## 7. Telemetry and Analysis Model

### Normalized channel groups

- Power: battery voltage, current, cell voltage, capacity, state of charge, battery temperature.
- Propulsion: motor output, RPM, ESC voltage/current, ESC temperature, desync/error flags.
- Navigation: GPS fix, satellites, HDOP/VDOP, position, ground speed, home distance.
- State estimation: EKF innovations, estimator status, position/velocity variance, reset events.
- Motion: IMU acceleration, gyroscope, vibration, clipping, attitude, angular rates.
- Flight state: altitude, climb/descent rate, velocity, flight mode, arming state, failsafe events.
- Control and link: RC RSSI, link quality, packet loss, stick inputs, actuator outputs.
- Environment and mission: ambient temperature, mission waypoint, geofence, payload, firmware, aircraft identity.

### Analysis pipeline

```text
Source file -> validation -> parser -> normalized channels -> data quality
	-> event extraction -> detector rules/statistics -> correlated findings
	-> evidence store -> assistant retrieval/report snapshot
```

The detector layer should begin with transparent rules and robust statistics. Each detector must define its required channels, default thresholds, baseline strategy, minimum duration, and false-positive caveats. Model-assisted detection can be added behind the same finding contract.

### Initial detector examples

| Detector | Signal pattern | Suggested action |
| --- | --- | --- |
| Motor temperature spike | Temperature exceeds configured limit for a sustained interval, especially under rising load | Inspect motor, cooling, and bearings |
| Battery imbalance | Cell delta exceeds threshold under load or during recovery | Test battery health and connector resistance |
| GPS degradation | Fix quality, HDOP, or satellite count worsens during a flight segment | Check antenna, interference, and sky visibility |
| Vibration event | RMS vibration or clipping exceeds aircraft baseline | Inspect props, motors, mounts, and frame |
| EKF inconsistency | Innovation or estimator variance breaches limit with correlated navigation symptoms | Review sensors, calibration, and environment |
| RC link degradation | RSSI/link quality or packet loss crosses limit | Inspect antenna placement and link environment |
| Failsafe event | Failsafe state or mode transition occurs unexpectedly | Correlate trigger, operator action, and recovery |

## 8. Data Model

Core entities:

- `Workspace`: organization boundary, plan, settings, retention policy.
- `User` and `Membership`: identity, role, invite/status, workspace access.
- `Aircraft`: model, serial number, firmware, configuration, owner workspace.
- `Battery`: serial number, chemistry, rated capacity, cycle count, aircraft history.
- `Flight`: source file, checksum, aircraft, pilot, mission, timestamps, parser/version, status.
- `TelemetryChannel`: normalized name, unit, source field, sampling metadata, quality flags.
- `TelemetryChunk`: compressed time-series data partitioned by flight and time range.
- `Event`: timestamped mode, failsafe, estimator, mission, or system event.
- `Anomaly`: detector output, evidence, severity, confidence, status, assignment.
- `Conversation` and `Message`: scoped assistant history and source references.
- `Report`: immutable generated snapshot, export format, reviewer metadata.
- `AuditEvent`: actor, action, entity, timestamp, request ID, and result.

All timestamps are stored in UTC. Original units and normalized units must both be retained when conversion occurs.

## 9. API Contract

The current demo API is intentionally small. Production endpoints should evolve toward:

```text
GET    /api/health
POST   /api/workspaces/:workspaceId/flights
GET    /api/workspaces/:workspaceId/flights
GET    /api/flights/:flightId
GET    /api/flights/:flightId/telemetry
GET    /api/flights/:flightId/events
GET    /api/flights/:flightId/anomalies
PATCH  /api/anomalies/:anomalyId
POST   /api/ask
POST   /api/reports
GET    /api/reports/:reportId
```

Responses should use consistent JSON errors with `code`, `message`, `details`, and `request_id`. Long-running ingestion and report jobs should return a job ID and expose progress rather than holding an HTTP request open.

Current demo payloads:

- `POST /api/analyze` with `{ "filename": "flight.csv" }`
- `POST /api/ask` with `{ "question": "What caused the temperature spike?" }`
- `POST /api/report`

## 10. Technical Architecture

### MVP

- Static HTML/CSS/JavaScript frontend.
- Python HTTP API for demo analysis and assistant responses.
- Local or object storage for source files.
- SQLite or PostgreSQL for metadata and findings.
- Background worker for parsing and analysis.
- Pluggable parser adapters for PX4 and ArduPilot.
- Pluggable LLM provider with retrieval and structured output validation.

### Production direction

```text
Browser -> API gateway -> auth/workspace service
					-> flight metadata database
					-> object storage for source logs
					-> queue -> parser/analyzer workers
					-> telemetry store and anomaly store
					-> retrieval service -> LLM provider
					-> report/export worker
```

The API, parser, detector, retrieval, and report layers should have explicit interfaces so analysis remains testable without a live model or cloud storage.

## 11. Security, Privacy, and Reliability

- Encrypt data in transit and at rest.
- Enforce workspace authorization on every endpoint and object lookup.
- Validate upload size, MIME type, extension, archive handling, and parser resource usage.
- Treat uploaded logs and model-retrieved text as untrusted input.
- Redact secrets and credentials before sending context to an external model.
- Support configurable retention and permanent deletion of source files and derived data.
- Keep immutable audit events for uploads, exports, assistant access, and anomaly changes.
- Make analysis idempotent by source checksum and analysis version.
- Surface parser failures and incomplete channels instead of silently producing a clean result.
- Target 99.5% monthly availability for the production API and resumable processing for large logs.

## 12. Quality and Acceptance Criteria

The MVP is ready when:

- A supported sample log can be uploaded and reaches a terminal state with visible progress.
- A malformed or unsupported log produces a useful, non-sensitive error.
- A completed flight shows metadata, telemetry channels, events, and at least one chart.
- Every displayed anomaly links to a timestamped evidence window and lists its detector version.
- Assistant answers cite available evidence and explicitly refuse unsupported conclusions.
- Anomaly status changes and notes persist after refresh.
- Reports contain the same findings and values shown in the flight view.
- Workspace users cannot access another workspace's flight, report, or source file.
- Reprocessing the same source with the same analysis version is idempotent.
- The UI remains usable at 375 px mobile width and desktop widths of at least 1280 px.

### Test strategy

- Unit tests for parsers, unit conversion, channel mapping, detectors, severity, and confidence.
- Fixture-based integration tests for representative PX4, ArduPilot, CSV, malformed, and partial logs.
- API tests for validation, authorization, idempotency, and consistent errors.
- Assistant evaluation set covering grounded answers, missing evidence, units, time ranges, and unsafe recommendations.
- Browser tests for upload, analysis progress, anomaly drill-down, Q&A, report export, and responsive layout.
- Performance tests using large logs and high-cardinality telemetry channels.

## 13. Product Metrics

- Median time from upload to completed analysis.
- Percentage of uploads parsed successfully.
- Percentage of findings opened and acknowledged by a human.
- Assistant answer citation rate and unsupported-claim rate.
- Median time from anomaly detection to resolution.
- Repeat anomaly rate by aircraft, battery, motor, firmware, and mission type.
- Weekly active workspaces and analyzed flight hours.
- Report creation and export rate.

## 14. Delivery Roadmap

### Phase 0: Working demo

- Existing dashboard, demo telemetry, upload interaction, anomaly cards, assistant shell, report download, and local Python API.

### Phase 1: Trustworthy single-flight analysis

- Real file upload, parser adapters, normalized channel catalog, charting, detector contracts, persistent flight records, and evidence-linked anomaly detail.

### Phase 2: Team workflow

- Authentication, workspaces, roles, anomaly assignment/status, notes, report snapshots, audit events, and object storage.

### Phase 3: Fleet intelligence

- Cross-flight baselines, trend views, recurring issue detection, cohort comparisons, alerts, and maintenance history.

### Phase 4: Enterprise and predictive maintenance

- On-premise deployment, SSO, integrations, battery life prediction, component risk scoring, and organization-wide governance.

## 15. Local Development

Open `ui/index.html` directly in a browser, or serve the UI folder with a static web server:

```sh
python3 -m http.server 4173 --directory ui
```

Then visit `http://localhost:4173`.

Start the Python backend in a second terminal:

```sh
python3 -m pip install -r requirements.txt
python3 backend/server.py
```

The API runs at `http://127.0.0.1:8787`.

The assistant uses the LangChain agent module in `backend/droneops_agent.py`. Without an `OPENAI_API_KEY`, it uses the deterministic grounded fallback so the demo remains runnable. To enable the model-backed path, set `OPENAI_API_KEY` and optionally `DRONEOPS_MODEL` before starting the backend.

## PostgreSQL database setup

The project includes a PostgreSQL-ready data layer using `psycopg` and environment variables.

Create a local database:

```sh
cp .env.example .env
python3 -m pip install -r requirements.txt
```

Then start PostgreSQL locally with Docker Compose:

```sh
docker compose up -d postgres
```

Example environment variables in `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hoverin
DB_USER=postgres
DB_PASSWORD=postgres
```

When the database is running, the backend will initialize the `flight_analyses` and `assistant_answers` tables automatically on startup. If Postgres is not running yet, the app keeps working in demo mode and logs the database initialization issue instead of crashing the API.

The current prototype supports this core flow: upload a `.csv`, `.json`, or `.log` flight log, analyze demo telemetry, review prioritized anomalies, ask evidence-based questions, and download a source-backed report.
