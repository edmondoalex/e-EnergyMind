import asyncio
import json
import time
import sqlite3
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .ha_client import HAClient
from .storage import load_config, save_config, apply_config, apply_entities


def _load_version() -> str:
    cfg_path = Path("/app/config.yaml")
    if not cfg_path.exists():
        return "0.0.0"
    for line in cfg_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"')
    return "0.0.0"


APP_VERSION = _load_version()

app = FastAPI(title="e-EnergyMind", version=APP_VERSION)

ha = HAClient()
ha_task: asyncio.Task | None = None
log_task: asyncio.Task | None = None
action_log: list[str] = []

DB_PATH = Path("/data/energymind.db")
LOG_INTERVAL_S = 10
RETENTION_DAYS = 90


def _log_action(msg: str) -> None:
    action_log.append(msg)
    if len(action_log) > 300:
        del action_log[0 : len(action_log) - 300]


def _entity_payload(entity_id: str | None) -> Dict[str, Any]:
    if not entity_id:
        return {"entity_id": None, "state": None, "attributes": {}, "icon": None}
    st = ha.states.get(entity_id)
    if not st:
        return {"entity_id": entity_id, "state": None, "attributes": {}, "icon": None}
    return {
        "entity_id": entity_id,
        "state": st.get("state"),
        "attributes": st.get("attributes", {}) or {},
        "icon": st.get("attributes", {}).get("icon"),
    }


def _db_init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
              ts INTEGER NOT NULL,
              site INTEGER NOT NULL,
              key TEXT NOT NULL,
              value REAL,
              raw TEXT,
              unit TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_samples_site_key ON samples(site, key)")
        conn.commit()


def _db_insert_rows(rows: list[tuple]) -> int:
    if not rows:
        return 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO samples (ts, site, key, value, raw, unit) VALUES (?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def _db_prune(cutoff_ts: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM samples WHERE ts < ?", (cutoff_ts,))
        conn.commit()
        return cur.rowcount or 0


def _parse_site_key(cfg_key: str) -> tuple[int, str] | None:
    if not cfg_key.startswith("s"):
        return None
    parts = cfg_key.split("_", 1)
    if len(parts) != 2:
        return None
    site_part = parts[0][1:]
    if not site_part.isdigit():
        return None
    return int(site_part), parts[1]


def _num_or_none(raw: Any) -> float | None:
    try:
        return float(raw)
    except Exception:
        return None


def _collect_rows() -> list[tuple]:
    cfg = load_config()
    ent_cfg = cfg.get("entities", {})
    now_ts = int(time.time())
    rows: list[tuple] = []
    for cfg_key, entity_id in (ent_cfg or {}).items():
        if not entity_id:
            continue
        parsed = _parse_site_key(cfg_key)
        if not parsed:
            continue
        site, key = parsed
        st = ha.states.get(entity_id)
        if not st:
            continue
        raw = st.get("state")
        val = _num_or_none(raw)
        unit = None
        attrs = st.get("attributes") or {}
        if isinstance(attrs, dict):
            unit = attrs.get("unit_of_measurement")
        rows.append((now_ts, site, key, val, None if raw is None else str(raw), None if unit is None else str(unit)))
    return rows


async def _logging_loop():
    _db_init()
    last_prune = 0.0
    while True:
        try:
            rows = await asyncio.to_thread(_collect_rows)
            if rows:
                inserted = await asyncio.to_thread(_db_insert_rows, rows)
                _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} LOG samples={inserted}")
            now = time.time()
            if now - last_prune > 3600:
                cutoff = int(now - (RETENTION_DAYS * 86400))
                deleted = await asyncio.to_thread(_db_prune, cutoff)
                if deleted:
                    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} PRUNE samples={deleted}")
                last_prune = now
        except Exception as exc:
            _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} LOG error: {exc}")
        await asyncio.sleep(LOG_INTERVAL_S)


@app.on_event("startup")
async def startup_event():
    global ha_task, log_task
    try:
        await ha.start()
        ha_task = asyncio.create_task(ha.run())
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HA connected")
    except Exception as exc:
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HA connect error: {exc}")
    log_task = asyncio.create_task(_logging_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if ha_task:
        ha_task.cancel()
    if log_task:
        log_task.cancel()
    await ha.close()


@app.get("/api/status")
async def get_status():
    cfg = load_config()
    return {
        "version": APP_VERSION,
        "runtime_mode": cfg.get("runtime", {}).get("mode", "dry-run"),
        "ha_connected": bool(ha._session) and ha.enabled,
    }


@app.get("/api/config")
async def get_config():
    return JSONResponse(load_config())


@app.post("/api/config")
async def set_config(payload: Dict[str, Any]):
    cfg = load_config()
    cfg = apply_config(cfg, payload)
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE config")
    return JSONResponse({"ok": True})


@app.get("/api/entities")
async def get_entities():
    cfg = load_config()
    ent_cfg = cfg.get("entities", {})
    out: Dict[str, Any] = {}
    for key, eid in (ent_cfg or {}).items():
        out[key] = _entity_payload(eid)
    return JSONResponse(out)


@app.post("/api/entities")
async def set_entities(payload: Dict[str, Any]):
    cfg = load_config()
    cfg = apply_entities(cfg, payload)
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE entities")
    return JSONResponse({"ok": True})


@app.get("/api/actions")
async def get_actions():
    return JSONResponse({"items": action_log})
