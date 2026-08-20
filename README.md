# Hoverin DroneOps AI

Hoverin DroneOps AI is a focused flight intelligence workspace for drone operators, engineers, manufacturers, and maintenance teams.

## Run locally

Open `ui/index.html` directly in a browser, or serve the UI folder with any static web server:

```sh
python3 -m http.server 4173 --directory ui
```

Then visit `http://localhost:4173`.

Start the Python backend in a second terminal:

```sh
python3 backend/server.py
```

The API runs at `http://127.0.0.1:8787`.

Available endpoints:

- `GET /api/health`
- `POST /api/analyze` with `{ "filename": "flight.csv" }`
- `POST /api/ask` with `{ "question": "What caused the temperature spike?" }`
- `POST /api/report`

## Core flow

Upload a `.csv`, `.json`, or `.log` flight log, analyze the demo telemetry, review prioritized anomalies, ask evidence-based questions, and use the source-backed response as the basis for a report.
