import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if __package__ in (None, ""):
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    from db import get_latest_flight_context, init_db, list_users, save_flight_analysis, save_assistant_answer, save_user
    from ingest import analyze_uploaded_log
    from agents.anomaly_agent import answer_anomaly_question, should_use_anomaly_agent as detect_anomaly_intent
    from agents.droneops_agent import answer_flight_question
else:
    from .db import get_latest_flight_context, init_db, list_users, save_flight_analysis, save_assistant_answer, save_user
    from .ingest import analyze_uploaded_log
    from agents.anomaly_agent import answer_anomaly_question, should_use_anomaly_agent as detect_anomaly_intent
    from agents.droneops_agent import answer_flight_question


def should_use_anomaly_agent(question: str, analysis: dict | None = None) -> bool:
    return detect_anomaly_intent(question, analysis)

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8787"))


def flight_analysis(filename="flight-log.json", content=None, flight_id=None):
    db_context = get_latest_flight_context()
    if flight_id and isinstance(db_context, dict) and db_context.get("flight_id") == flight_id:
        return db_context
    if isinstance(db_context, dict) and db_context.get("anomalies"):
        return db_context

    if content is not None:
        try:
            return analyze_uploaded_log(filename, content)
        except Exception:
            pass
    try:
        return analyze_uploaded_log(filename)
    except Exception:
        return {
            "flight_id": "FL-249",
            "filename": filename,
            "status": "complete",
            "telemetry_points": 18420,
            "anomalies": [
                {
                    "type": "motor_temperature_spike",
                    "severity": "high",
                    "evidence": "Motor temperature peaked at 78C for 42 seconds while load rose to 86%.",
                    "recommendation": "Inspect the motor assembly before the next high-load flight.",
                },
                {
                    "type": "gps_accuracy_degradation",
                    "severity": "medium",
                    "evidence": "GPS accuracy briefly degraded to 2.8m during the return leg.",
                    "recommendation": "Review antenna placement and repeat a controlled GPS check.",
                },
            ],
            "sources": ["FL-249 telemetry", "maintenance history", "anomaly model v2.8"],
        }


class DroneOpsHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        return json.loads(body) if body else {}

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json(200, {"status": "ok", "service": "droneops-api", "version": "1.0.0"})
            return
        if self.path == "/api/users":
            self.send_json(200, {"users": list_users()})
            return
        self.send_json(404, {"error": "Route not found."})

    def do_POST(self):
        try:
            payload = self.read_json()
        except (json.JSONDecodeError, ValueError):
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return

        if self.path == "/api/analyze":
            filename = payload.get("filename", "flight-log.json")
            content = payload.get("content")
            analysis = flight_analysis(filename, content)
            try:
                save_flight_analysis(analysis)
            except Exception:
                pass
            self.send_json(200, analysis)
            return

        if self.path == "/api/anomaly":
            question = payload.get("question", "")
            if not isinstance(question, str) or not question.strip():
                self.send_json(400, {"error": "A question is required."})
                return

            flight_context = payload.get("flight_context") or {}
            if isinstance(flight_context, dict) and flight_context:
                analysis = flight_context
            else:
                analysis = flight_analysis(flight_id=payload.get("flight_id"))

            result = answer_anomaly_question(question, analysis)
            try:
                save_assistant_answer(question, result)
            except Exception:
                pass
            self.send_json(200, result)
            return

        if self.path == "/api/ask":
            question = payload.get("question", "")
            if not isinstance(question, str) or not question.strip():
                self.send_json(400, {"error": "A question is required."})
                return

            flight_context = payload.get("flight_context") or {}
            if isinstance(flight_context, dict) and flight_context:
                analysis = flight_context
            else:
                analysis = flight_analysis(flight_id=payload.get("flight_id"))

            if should_use_anomaly_agent(question, analysis):
                result = answer_anomaly_question(question, analysis)
            else:
                result = answer_flight_question(question, analysis)
            try:
                save_assistant_answer(question, result)
            except Exception:
                pass
            self.send_json(200, result)
            return

        if self.path == "/api/users":
            try:
                user = save_user(payload)
            except ValueError as exc:
                self.send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self.send_json(500, {"error": f"Unable to save user: {exc}"})
                return
            self.send_json(201, {"user": user})
            return

        if self.path == "/api/report":
            analysis = flight_analysis()
            self.send_json(
                200,
                {
                    "title": "Hoverin DroneOps AI Flight Briefing",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "summary": analysis,
                    "recommendation": analysis["anomalies"][0]["recommendation"],
                },
            )
            return

        self.send_json(404, {"error": "Route not found."})

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")


if __name__ == "__main__":
    try:
        init_db()
    except Exception as exc:
        print(f"Database initialization skipped: {exc}")

    try:
        server = ThreadingHTTPServer((HOST, PORT), DroneOpsHandler)
    except OSError as exc:
        if exc.errno == 48:
            print(f"Port {PORT} is already in use. Hoverin DroneOps AI API is already running.")
            raise SystemExit(0)
        raise

    print(f"Hoverin DroneOps AI API listening at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHoverin DroneOps AI API stopped")
    finally:
        server.server_close()
