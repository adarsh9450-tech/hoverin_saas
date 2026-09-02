import json
import os
from typing import Any

try:
    import psycopg
except ImportError:  # pragma: no cover - optional package until installed.
    psycopg = None

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hoverin")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Run: python3 -m pip install -r requirements.txt")
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True,
    )


def init_db():
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Run: python3 -m pip install -r requirements.txt")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS drones (
                    id SERIAL PRIMARY KEY,
                    serial_number TEXT UNIQUE NOT NULL,
                    model TEXT NOT NULL,
                    manufacturer TEXT,
                    firmware_version TEXT,
                    aircraft_type TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS batteries (
                    id SERIAL PRIMARY KEY,
                    serial_number TEXT UNIQUE NOT NULL,
                    model TEXT,
                    chemistry TEXT,
                    capacity_wh DOUBLE PRECISION,
                    voltage_nominal DOUBLE PRECISION,
                    cycle_count INTEGER,
                    health_percent DOUBLE PRECISION,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS flights (
                    id SERIAL PRIMARY KEY,
                    flight_id TEXT UNIQUE NOT NULL,
                    drone_id INTEGER REFERENCES drones(id),
                    battery_id INTEGER REFERENCES batteries(id),
                    filename TEXT,
                    source_format TEXT,
                    mission_name TEXT,
                    status TEXT,
                    start_time TIMESTAMPTZ,
                    end_time TIMESTAMPTZ,
                    duration_seconds INTEGER,
                    telemetry_points INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS flight_channels (
                    id SERIAL PRIMARY KEY,
                    flight_id INTEGER REFERENCES flights(id) ON DELETE CASCADE,
                    channel_name TEXT NOT NULL,
                    unit TEXT,
                    source_field TEXT,
                    data_type TEXT,
                    UNIQUE (flight_id, channel_name)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_points (
                    id SERIAL PRIMARY KEY,
                    flight_id INTEGER REFERENCES flights(id) ON DELETE CASCADE,
                    channel_id INTEGER REFERENCES flight_channels(id) ON DELETE CASCADE,
                    ts TIMESTAMPTZ NOT NULL,
                    value DOUBLE PRECISION,
                    quality_flag TEXT,
                    UNIQUE (flight_id, channel_id, ts)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS flight_events (
                    id SERIAL PRIMARY KEY,
                    flight_id INTEGER REFERENCES flights(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    event_ts TIMESTAMPTZ NOT NULL,
                    payload JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS anomalies (
                    id SERIAL PRIMARY KEY,
                    flight_id INTEGER REFERENCES flights(id) ON DELETE CASCADE,
                    anomaly_type TEXT NOT NULL,
                    severity TEXT,
                    confidence TEXT,
                    start_ts TIMESTAMPTZ,
                    end_ts TIMESTAMPTZ,
                    description TEXT,
                    evidence JSONB,
                    recommendation TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS assistant_answers (
                    id SERIAL PRIMARY KEY,
                    flight_id INTEGER REFERENCES flights(id),
                    question TEXT,
                    answer JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'Operator',
                    status TEXT NOT NULL DEFAULT 'Pending',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
    finally:
        conn.close()


def save_user(user: dict[str, Any]) -> dict[str, Any]:
    name = (user.get("name") or "").strip()
    email = (user.get("email") or "").strip()
    role = (user.get("role") or "Operator").strip() or "Operator"
    status = (user.get("status") or "Pending").strip() or "Pending"

    if not name or not email:
        raise ValueError("User name and email are required.")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, email, role, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    role = EXCLUDED.role,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id, name, email, role, status
                """,
                (name, email, role, status),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("User record was not saved.")
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "status": row[4],
            }
    finally:
        conn.close()


def list_users() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, role, status FROM users ORDER BY created_at DESC"
            )
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "role": row[3],
                    "status": row[4],
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


def create_drone(serial_number: str, model: str, manufacturer: str | None = None,
                firmware_version: str | None = None, aircraft_type: str | None = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drones (serial_number, model, manufacturer, firmware_version, aircraft_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (serial_number) DO UPDATE SET
                    model = EXCLUDED.model,
                    manufacturer = EXCLUDED.manufacturer,
                    firmware_version = EXCLUDED.firmware_version,
                    aircraft_type = EXCLUDED.aircraft_type
                RETURNING id
                """,
                (serial_number, model, manufacturer, firmware_version, aircraft_type),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def create_battery(serial_number: str, model: str | None = None, chemistry: str | None = None,
                  capacity_wh: float | None = None, voltage_nominal: float | None = None,
                  cycle_count: int | None = None, health_percent: float | None = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO batteries (serial_number, model, chemistry, capacity_wh, voltage_nominal, cycle_count, health_percent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (serial_number) DO UPDATE SET
                    model = EXCLUDED.model,
                    chemistry = EXCLUDED.chemistry,
                    capacity_wh = EXCLUDED.capacity_wh,
                    voltage_nominal = EXCLUDED.voltage_nominal,
                    cycle_count = EXCLUDED.cycle_count,
                    health_percent = EXCLUDED.health_percent
                RETURNING id
                """,
                (serial_number, model, chemistry, capacity_wh, voltage_nominal, cycle_count, health_percent),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def create_flight(flight_id: str, drone_id: int | None = None, battery_id: int | None = None,
                 filename: str | None = None, source_format: str | None = None,
                 mission_name: str | None = None, status: str | None = None,
                 start_time: str | None = None, end_time: str | None = None,
                 duration_seconds: int | None = None, telemetry_points: int | None = None,
                 metadata: dict[str, Any] | None = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flights (
                    flight_id, drone_id, battery_id, filename, source_format, mission_name,
                    status, start_time, end_time, duration_seconds, telemetry_points, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (flight_id) DO UPDATE SET
                    drone_id = EXCLUDED.drone_id,
                    battery_id = EXCLUDED.battery_id,
                    filename = EXCLUDED.filename,
                    source_format = EXCLUDED.source_format,
                    mission_name = EXCLUDED.mission_name,
                    status = EXCLUDED.status,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    duration_seconds = EXCLUDED.duration_seconds,
                    telemetry_points = EXCLUDED.telemetry_points,
                    metadata = EXCLUDED.metadata
                RETURNING id
                """,
                (
                    flight_id,
                    drone_id,
                    battery_id,
                    filename,
                    source_format,
                    mission_name,
                    status,
                    start_time,
                    end_time,
                    duration_seconds,
                    telemetry_points,
                    json.dumps(metadata or {}),
                ),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def insert_channel(flight_id: int, channel_name: str, unit: str | None = None,
                  source_field: str | None = None, data_type: str | None = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flight_channels (flight_id, channel_name, unit, source_field, data_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (flight_id, channel_name) DO UPDATE SET
                    unit = EXCLUDED.unit,
                    source_field = EXCLUDED.source_field,
                    data_type = EXCLUDED.data_type
                RETURNING id
                """,
                (flight_id, channel_name, unit, source_field, data_type),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def insert_telemetry_points(flight_id: int, channel_name: str, records: list[dict[str, Any]]):
    if not records:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            channel_id = cur.execute(
                "SELECT id FROM flight_channels WHERE flight_id = %s AND channel_name = %s",
                (flight_id, channel_name),
            )
            channel_id = cur.fetchone()
            if channel_id is None:
                channel_id = insert_channel(flight_id, channel_name)
            else:
                channel_id = channel_id[0]

            cur.executemany(
                """
                INSERT INTO telemetry_points (flight_id, channel_id, ts, value, quality_flag)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (flight_id, channel_id, ts) DO UPDATE SET
                    value = EXCLUDED.value,
                    quality_flag = EXCLUDED.quality_flag
                """,
                [
                    (
                        flight_id,
                        channel_id,
                        record.get("ts"),
                        record.get("value"),
                        record.get("quality_flag"),
                    )
                    for record in records
                ],
            )
    finally:
        conn.close()


def insert_event(flight_id: int, event_type: str, event_ts: str, payload: dict[str, Any] | None = None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flight_events (flight_id, event_type, event_ts, payload)
                VALUES (%s, %s, %s, %s)
                """,
                (flight_id, event_type, event_ts, json.dumps(payload or {})),
            )
    finally:
        conn.close()


def insert_anomaly(flight_id: int, anomaly_type: str, severity: str | None = None,
                  confidence: str | None = None, start_ts: str | None = None,
                  end_ts: str | None = None, description: str | None = None,
                  evidence: dict[str, Any] | None = None,
                  recommendation: str | None = None, status: str = "open"):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO anomalies (
                    flight_id, anomaly_type, severity, confidence, start_ts, end_ts,
                    description, evidence, recommendation, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    flight_id,
                    anomaly_type,
                    severity,
                    confidence,
                    start_ts,
                    end_ts,
                    description,
                    json.dumps(evidence or {}),
                    recommendation,
                    status,
                ),
            )
    finally:
        conn.close()


def save_flight_analysis(analysis: dict[str, Any]):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            flight_id = analysis.get("flight_id")
            cur.execute(
                """
                INSERT INTO flights (flight_id, filename, status, telemetry_points, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (flight_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    status = EXCLUDED.status,
                    telemetry_points = EXCLUDED.telemetry_points,
                    metadata = EXCLUDED.metadata
                RETURNING id
                """,
                (
                    flight_id,
                    analysis.get("filename"),
                    analysis.get("status"),
                    analysis.get("telemetry_points"),
                    json.dumps(analysis),
                ),
            )
            row = cur.fetchone()
            if row is not None:
                saved_flight_id = row[0]
                anomalies = analysis.get("anomalies", []) or []
                for anomaly in anomalies:
                    if not isinstance(anomaly, dict):
                        continue
                    cur.execute(
                        """
                        INSERT INTO anomalies (
                            flight_id, anomaly_type, severity, confidence, description, evidence, recommendation, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            saved_flight_id,
                            anomaly.get("type") or anomaly.get("name") or "unknown_anomaly",
                            anomaly.get("severity"),
                            anomaly.get("confidence"),
                            anomaly.get("description") or anomaly.get("evidence") or "No description available.",
                            json.dumps({"evidence": anomaly.get("evidence")}),
                            anomaly.get("recommendation"),
                            "open",
                        ),
                    )
    finally:
        conn.close()


def get_latest_flight_context() -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT flight_id, filename, status, telemetry_points, metadata
                FROM flights
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row is None:
                return None

            flight_id, filename, status, telemetry_points, metadata = row
            context = metadata if isinstance(metadata, dict) else {}
            cur.execute(
                """
                SELECT anomaly_type, severity, description, evidence, recommendation
                FROM anomalies
                WHERE flight_id = (SELECT id FROM flights WHERE flight_id = %s)
                ORDER BY created_at DESC
                """,
                (flight_id,),
            )
            anomalies = []
            for anomaly_row in cur.fetchall():
                anomaly_type, severity, description, evidence, recommendation = anomaly_row
                anomaly = {"type": anomaly_type, "severity": severity, "description": description or "No description available."}
                if evidence:
                    try:
                        parsed = json.loads(evidence) if isinstance(evidence, str) else evidence
                        if isinstance(parsed, dict):
                            anomaly["evidence"] = parsed.get("evidence") or description or "No evidence available."
                    except Exception:
                        anomaly["evidence"] = evidence
                else:
                    anomaly["evidence"] = description or "No evidence available."
                if recommendation:
                    anomaly["recommendation"] = recommendation
                anomalies.append(anomaly)

            if not anomalies and isinstance(context.get("anomalies"), list):
                anomalies = context.get("anomalies")

            return {
                "flight_id": flight_id,
                "filename": filename,
                "status": status,
                "telemetry_points": telemetry_points,
                "anomalies": anomalies,
                "sources": ["database:latest_flight", "database:anomaly_history"],
            }
    finally:
        conn.close()


def save_assistant_answer(question: str, result: dict[str, Any], flight_id: int | None = None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO assistant_answers (flight_id, question, answer)
                VALUES (%s, %s, %s)
                """,
                (flight_id, question, json.dumps(result)),
            )
    finally:
        conn.close()
