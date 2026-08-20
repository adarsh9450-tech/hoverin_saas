import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8787"))


def flight_analysis(filename="flight-log.json"):
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
        self.send_json(404, {"error": "Route not found."})

    def do_POST(self):
        try:
            payload = self.read_json()
        except (json.JSONDecodeError, ValueError):
            self.send_json(400, {"error": "Request body must be valid JSON."})
            return

        if self.path == "/api/analyze":
            filename = payload.get("filename", "flight-log.json")
            self.send_json(200, flight_analysis(filename))
            return

        if self.path == "/api/ask":
            question = payload.get("question", "")
            if not isinstance(question, str) or not question.strip():
                self.send_json(400, {"error": "A question is required."})
                return
            analysis = flight_analysis()
            self.send_json(
                200,
                {
                    "answer": (
                        f'The latest telemetry shows a stable flight profile overall. For "{question.strip()}", '
                        "FL-249 has 2 relevant signals: motor temperature peaked at 78C for 42 seconds "
                        "while load rose to 86%, then returned to baseline. This is flagged for inspection, "
                        "not an immediate grounding."
                    ),
                    "sources": analysis["sources"],
                },
            )
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
    server = ThreadingHTTPServer((HOST, PORT), DroneOpsHandler)
    print(f"Hoverin DroneOps AI API listening at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHoverin DroneOps AI API stopped")
    finally:
        server.server_close()
