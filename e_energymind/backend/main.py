import asyncio
import json
import time
import sqlite3
import mimetypes
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from .ha_client import HAClient
from .storage import load_config, save_config, apply_config, apply_entities, ENERGY_ENTITY_KEYS


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


def _norm(text: str) -> str:
    s = text.lower()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())


def _patterns() -> Dict[str, list[str]]:
    return {
        "pv_power_total": ["pv power total", "pv_total", "activepower_pv_ext", "pv ext", "pv_ext", "produzione inst fv totale", "produzione inst. fv totale"],
        "pv_power": ["pv power", "pvpower", "pv_power"],
        "pv_power_aux": ["pv1 power", "pv1_power", "pv1"],
        "load_power": ["activepower_load_sys", "load power", "load sys", "load_total", "consumo"],
        "grid_power": ["activepower_pcc_total", "pcc total", "grid power"],
        "grid_import_power": ["grid import", "import power", "energy import"],
        "grid_export_power": ["grid export", "export power", "export surplus"],
        "battery_power": ["battery power"],
        "battery_voltage": ["battery voltage"],
        "battery_current": ["battery current"],
        "battery_soc": ["battery soc", "batteria soc", "soc battery", "soc batteria", "bms soc", "soc"],
        "battery_soh": ["battery soh", "soh"],
        "battery_temp": ["battery temperature", "battery temp"],
        "storage_control_mode": ["storage control mode"],
        "timed_charge_start": ["timed charge start"],
        "timed_charge_end": ["timed charge end"],
        "timed_charge_power": ["timed charge power"],
        "timed_discharge_start": ["timed discharge start"],
        "timed_discharge_end": ["timed discharge end"],
        "timed_discharge_power": ["timed discharge power"],
        "today_production_kwh": ["today production"],
        "today_load_kwh": ["today load consumption", "today load"],
        "today_import_kwh": ["today energy import", "today import", "today energy in", "today_energy_in", "import oggi", "energia import oggi", "energia importata oggi"],
        "today_export_kwh": ["today energy export"],
        "forecast_today_kwh": ["forecast today"],
        "forecast_tomorrow_kwh": ["forecast tomorrow"],
        "inverter_status": ["inverter status"],
        "device_fault": ["device fault"],
        "grid_frequency": ["grid frequency"],
        "ambient_temp_1": ["ambient temperature 1", "ambient temp 1"],
        "ambient_temp_2": ["ambient temperature 2", "ambient temp 2"],
        "module_temp_1": ["module temperature 1", "module temp 1"],
        "module_temp_2": ["module temperature 2", "module temp 2"],
        "module_temp_3": ["module temperature 3", "module temp 3"],
        "radiator_temp_1": ["radiator temperature 1", "radiator temp 1"],
        "radiator_temp_2": ["radiator temperature 2", "radiator temp 2"],
        "radiator_temp_3": ["radiator temperature 3", "radiator temp 3"],
        "radiator_temp_4": ["radiator temperature 4", "radiator temp 4"],
        "radiator_temp_5": ["radiator temperature 5", "radiator temp 5"],
        "radiator_temp_6": ["radiator temperature 6", "radiator temp 6"],
    }


def _match_key(entry: dict, patterns: Dict[str, list[str]]) -> list[str]:
    text = " ".join([
        str(entry.get("entity_id") or ""),
        str(entry.get("original_name") or ""),
        str(entry.get("name") or ""),
    ])
    n = _norm(text)
    out: list[str] = []
    for key, pats in patterns.items():
        for p in pats:
            if _norm(p) in n:
                out.append(key)
                break
    return out


async def _get_device_entities(device_id: str | None, device_name: str | None) -> tuple[dict | None, list[dict]]:
    devices = await ha.ws_call("config/device_registry/list") or []
    entities = await ha.ws_call("config/entity_registry/list") or []
    if not isinstance(devices, list) or not isinstance(entities, list):
        return None, []

    target = None
    if device_id:
        for d in devices:
            if d.get("id") == device_id:
                target = d
                break
    if not target and device_name:
        dn = device_name.strip().lower()
        for d in devices:
            name = (d.get("name_by_user") or d.get("name") or "").strip().lower()
            if name == dn:
                target = d
                break
    if not target:
        return None, []

    dev_id = target.get("id")
    dev_entities = [e for e in entities if e.get("device_id") == dev_id]
    return target, dev_entities


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


@app.get("/")
async def index():
    return FileResponse("/app/static/index.html")


@app.get("/index.html")
async def index_html():
    return FileResponse("/app/static/index.html")


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


@app.post("/api/entities/reset")
async def reset_entities():
    cfg = load_config()
    cfg["entities"] = {f"s{site}_{key}": None for site in (1, 2, 3) for key in ENERGY_ENTITY_KEYS}
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} RESET entities")
    return JSONResponse({"ok": True})


@app.post("/api/auto_map")
async def auto_map(payload: Dict[str, Any]):
    site = int(payload.get("site") or 0)
    if site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    device_id = str(payload.get("device_id") or "").strip()
    device_name = str(payload.get("device_name") or "").strip()
    overwrite = bool(payload.get("overwrite", False))

    if not ha.enabled:
        raise HTTPException(status_code=400, detail="HA not connected")

    device, dev_entities = await _get_device_entities(device_id or None, device_name or None)
    if not device:
        # Fallback: try matching by name across states if device registry is unavailable
        if device_name:
            dn = _norm(device_name)
            dev_entities = []
            for eid, st in (ha.states or {}).items():
                if not isinstance(st, dict):
                    continue
                fname = st.get("attributes", {}).get("friendly_name", "")
                text = f"{eid} {fname}"
                if dn and dn in _norm(text):
                    dev_entities.append({
                        "entity_id": eid,
                        "name": fname,
                        "original_name": fname,
                    })
            device = {"name": device_name}
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

    patterns = _patterns()
    used = set()
    mapped = {}

    for ent in dev_entities:
        keys = _match_key(ent, patterns)
        if not keys:
            continue
        for key in keys:
            if key in mapped:
                continue
            eid = ent.get("entity_id")
            if not eid or eid in used:
                continue
            mapped[key] = eid
            used.add(eid)

    cfg = load_config()
    ent_cfg = cfg.get("entities", {})
    count = 0
    skipped_existing = 0
    for key in ENERGY_ENTITY_KEYS:
        eid = mapped.get(key)
        if not eid:
            continue
        cfg_key = f"s{site}_{key}"
        if not overwrite and ent_cfg.get(cfg_key):
            skipped_existing += 1
            continue
        ent_cfg[cfg_key] = eid
        count += 1

    cfg["entities"] = ent_cfg
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} AUTO_MAP site={site} mapped={count}")
    return JSONResponse({
        "ok": True,
        "mapped": count,
        "matched": len(mapped),
        "skipped_existing": skipped_existing,
        "device": device.get("name") or device.get("name_by_user") or device.get("id"),
    })


@app.post("/api/auto_map/")
async def auto_map_slash(payload: Dict[str, Any]):
    return await auto_map(payload)


@app.get("/api/devices")
async def list_devices():
    if not ha.enabled:
        raise HTTPException(status_code=400, detail="HA not connected")
    devices = await ha.ws_call("config/device_registry/list") or []
    out = []
    for d in devices:
        out.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "name_by_user": d.get("name_by_user"),
            "model": d.get("model"),
            "manufacturer": d.get("manufacturer"),
        })
    return JSONResponse({"items": out})


@app.get("/api/device_entities")
async def device_entities(device_id: str = "", device_name: str = ""):
    if not ha.enabled:
        raise HTTPException(status_code=400, detail="HA not connected")
    device_id = (device_id or "").strip()
    device_name = (device_name or "").strip()
    if not device_id and not device_name:
        raise HTTPException(status_code=400, detail="Missing device_id")
    entities = await ha.ws_call("config/entity_registry/list") or []
    devices = await ha.ws_call("config/device_registry/list") or []
    target_id = device_id
    if not target_id and device_name and isinstance(devices, list):
        dn = device_name.strip().lower()
        for d in devices:
            name = (d.get("name_by_user") or d.get("name") or "").strip().lower()
            if name == dn:
                target_id = d.get("id")
                break
    items = []
    if isinstance(entities, list):
        for e in entities:
            if target_id and e.get("device_id") != target_id:
                continue
            items.append({
                "entity_id": e.get("entity_id"),
                "name": e.get("name"),
                "original_name": e.get("original_name"),
                "platform": e.get("platform"),
                "disabled_by": e.get("disabled_by"),
            })
    # sample device_ids present in registry (debug)
    sample_ids = []
    if isinstance(entities, list):
        seen = set()
        for e in entities:
            did = e.get("device_id")
            if not did or did in seen:
                continue
            seen.add(did)
            sample_ids.append(did)
            if len(sample_ids) >= 20:
                break
    device_list = []
    if isinstance(devices, list):
        for d in devices:
            device_list.append({
                "id": d.get("id"),
                "name": d.get("name"),
                "name_by_user": d.get("name_by_user"),
                "model": d.get("model"),
                "manufacturer": d.get("manufacturer"),
            })
    return JSONResponse({
        "device_id": target_id or device_id,
        "device_name": device_name,
        "items": items,
        "devices": device_list,
        "entity_device_ids_sample": sample_ids,
    })


@app.get("/api/routes")
async def get_routes():
    return JSONResponse({"routes": [str(r.path) for r in app.router.routes]})


@app.get("/api/actions")
async def get_actions():
    return JSONResponse({"items": action_log})


def _mount_assets() -> None:
    return


_mount_assets()


@app.get("/assets/{path:path}")
async def get_asset(path: str):
    if not path:
        raise HTTPException(status_code=404, detail="Not Found")
    base = Path("/app/static/assets")
    candidate = base / path
    if candidate.exists() and candidate.is_file():
        media_type, _ = mimetypes.guess_type(str(candidate))
        return FileResponse(str(candidate), media_type=media_type)
    fallback = Path("/app/static") / path
    if fallback.exists() and fallback.is_file():
        media_type, _ = mimetypes.guess_type(str(fallback))
        return FileResponse(str(fallback), media_type=media_type)
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/api/ha_debug")
async def ha_debug():
    out = {
        "enabled": ha.enabled,
        "token_source": getattr(ha, "token_source", None),
        "base_url": getattr(ha, "_base_url", None),
    }
    try:
        options_path = Path("/data/options.json")
        out["options_exists"] = options_path.exists()
        if options_path.exists():
            raw = options_path.read_text(encoding="utf-8")
            out["options_len"] = len(raw)
            try:
                data = json.loads(raw)
                token = data.get("ha_token")
                out["options_has_token"] = bool(isinstance(token, str) and token.strip())
                out["options_url"] = data.get("ha_url")
            except Exception:
                out["options_parse_error"] = True
    except Exception:
        out["options_error"] = True
    if not ha._session:
        out["session"] = "none"
        return JSONResponse(out)
    async def _probe_ws(cmd: str):
        res = await ha.ws_call(cmd)
        if res is None:
            return {"status": "error", "size": None}
        size = len(res) if isinstance(res, list) else None
        sample = res[:1] if isinstance(res, list) else res
        return {"status": "ok", "size": size, "sample": sample}
    out["device_registry"] = await _probe_ws("config/device_registry/list")
    out["entity_registry"] = await _probe_ws("config/entity_registry/list")
    return JSONResponse(out)
