import asyncio
import json
import time
import sqlite3
import mimetypes
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict

import aiohttp
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, RedirectResponse, Response
from starlette.background import BackgroundTask

from .ha_client import HAClient
from .mqtt_client import MqttClient
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


@app.middleware("http")
async def ha_api_proxy_middleware(request: Request, call_next):
    path = request.url.path or ""
    if path == "/api" or path.startswith("/api/"):
        ref = (request.headers.get("referer") or "").lower()
        if "/ha/" in ref or "/lovelace" in ref or "/dashboard-" in ref:
            target = path.lstrip("/")
            return await _proxy_request(request, target)
    return await call_next(request)

ha = HAClient()
ha_task: asyncio.Task | None = None
log_task: asyncio.Task | None = None
proxy_session: aiohttp.ClientSession | None = None
mqtt_client: MqttClient | None = None
last_mqtt_publish: float = 0.0
last_mqtt_values: dict[str, float] = {}
last_forecast_cache: dict[int, dict[str, Any]] = {}
last_forecast_ts: float = 0.0
action_log: list[str] = []
last_history_state: dict[str, tuple[str | None, int]] = {}
last_report_date: str | None = None
insight_condition_since: dict[int, float] = {}
last_rules_update: float | None = None

DB_PATH = Path("/data/energymind.db")
ALL_ENTITIES_PATH = Path("/data/energymind_all_entities.json")
REPORT_DIR = Path("/share/reports")
LOG_INTERVAL_S = 10
HISTORY_INTERVAL_S = 30
RETENTION_DAYS = 90
PARTIAL_EXPORT_MIN_W = 300
PARTIAL_MIN_DURATION_S = 10
LEARN_UPDATE_S = 7200
PV_ADJUST_INTERVAL_S = 60
SAFE_SOC_MARGIN_PCT = 5.0
SOLAR_END_W_THRESHOLD = 100.0
SOLAR_START_END_PCT = 0.05
SOLAR_REAL_MIN_W = 100.0
SOLAR_REAL_MIN_ON_MIN = 5
SOLAR_REAL_MIN_OFF_MIN = 10
MQTT_PUBLISH_INTERVAL_S = 5
FORECAST_CACHE_INTERVAL_S = 10


def _parse_hhmm(value: str) -> int | None:
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return None
        h = int(parts[0])
        m = int(parts[1])
        if h < 0 or h > 23 or m < 0 or m > 59:
            return None
        return h * 60 + m
    except Exception:
        return None


def _extra_safe_schedule_info(cfg: Dict[str, Any], now_ts: int) -> dict[str, Any]:
    automation = cfg.get("automation", {}) if isinstance(cfg.get("automation", {}), dict) else {}
    sched = automation.get("extra_safe_schedule", {})
    if not isinstance(sched, dict):
        return {"percent": 0.0, "day": None, "start": None, "end": None}
    if not bool(sched.get("enabled", False)):
        return {"percent": 0.0, "day": None, "start": None, "end": None}
    days = sched.get("days", {})
    if not isinstance(days, dict):
        return {"percent": 0.0, "day": None, "start": None, "end": None}
    tz_name = None
    try:
        tz_name = (cfg.get("runtime", {}) or {}).get("timezone")
    except Exception:
        tz_name = None
    if isinstance(tz_name, str) and tz_name.strip():
        try:
            lt_dt = datetime.fromtimestamp(now_ts, ZoneInfo(tz_name.strip()))
            lt = lt_dt.timetuple()
        except Exception:
            lt = time.localtime(now_ts)
    else:
        lt = time.localtime(now_ts)
    day_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = day_map[lt.tm_wday] if 0 <= lt.tm_wday < len(day_map) else "mon"
    slots = days.get(day_key, [])
    if not isinstance(slots, list):
        return {"percent": 0.0, "day": day_key, "start": None, "end": None}
    now_min = lt.tm_hour * 60 + lt.tm_min
    for item in slots:
        if not isinstance(item, dict):
            continue
        start = _parse_hhmm(str(item.get("start") or ""))
        end = _parse_hhmm(str(item.get("end") or ""))
        if start is None or end is None:
            continue
        if end <= start:
            continue
        if start <= now_min < end:
            try:
                pct = float(item.get("percent") or 0.0)
            except Exception:
                pct = 0.0
            return {"percent": pct, "day": day_key, "start": str(item.get("start") or ""), "end": str(item.get("end") or "")}
    return {"percent": 0.0, "day": day_key, "start": None, "end": None}

HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _ha_base_url() -> str:
    base = getattr(ha, "_base_url", None) or "http://supervisor/core"
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            data = json.loads(options_path.read_text(encoding="utf-8"))
            ha_url = data.get("ha_url")
            if isinstance(ha_url, str) and ha_url.strip():
                base = ha_url.strip()
        except Exception:
            pass
    # Supervisor core proxy doesn't serve static/frontend paths; prefer direct HA if not set.
    if "supervisor/core" in base:
        base = "http://homeassistant:8123"
    return str(base).rstrip("/")


def _ha_access_token() -> str | None:
    options_path = Path("/data/options.json")
    if options_path.exists():
        try:
            data = json.loads(options_path.read_text(encoding="utf-8"))
            ha_token = data.get("ha_token")
            if isinstance(ha_token, str) and ha_token.strip():
                return ha_token.strip()
        except Exception:
            pass
    return None


def _load_mqtt_options() -> dict[str, Any]:
    options_path = Path("/data/options.json")
    cfg: dict[str, Any] = {
        "enabled": False,
        "host": "core-mosquitto",
        "port": 1883,
        "username": "",
        "password": "",
        "base_topic": "energymind",
        "discovery_prefix": "homeassistant",
        "client_id": "energymind-addon",
    }
    if not options_path.exists():
        return cfg
    try:
        data = json.loads(options_path.read_text(encoding="utf-8"))
        mqtt = data.get("mqtt") or {}
        if isinstance(mqtt, dict):
            cfg["enabled"] = bool(mqtt.get("enabled", False))
            cfg["host"] = str(mqtt.get("host") or cfg["host"])
            cfg["port"] = int(mqtt.get("port") or cfg["port"])
            cfg["username"] = str(mqtt.get("username") or "")
            cfg["password"] = str(mqtt.get("password") or "")
            cfg["base_topic"] = str(mqtt.get("base_topic") or cfg["base_topic"]).rstrip("/")
            cfg["discovery_prefix"] = str(mqtt.get("discovery_prefix") or cfg["discovery_prefix"]).rstrip("/")
            cfg["client_id"] = str(mqtt.get("client_id") or cfg["client_id"])
    except Exception:
        pass
    return cfg


def _mqtt_device_info() -> dict[str, Any]:
    return {
        "identifiers": ["e_energymind"],
        "name": "e-EnergyMind",
        "manufacturer": "EA SAS",
        "model": "e-EnergyMind",
        "sw_version": APP_VERSION,
    }


def _mqtt_site_name(cfg: Dict[str, Any], site: int) -> str:
    devices = cfg.get("devices", {}) if isinstance(cfg.get("devices", {}), dict) else {}
    name = ""
    if isinstance(devices.get(f"s{site}"), dict):
        name = str(devices.get(f"s{site}", {}).get("name") or "").strip()
    return name or f"Utenza {site}"


def _mqtt_state_topics(cfg: Dict[str, Any], mqtt_cfg: dict[str, Any]) -> list[str]:
    topics = []
    base_topic = mqtt_cfg["base_topic"]
    sites_count = int(cfg.get("runtime", {}).get("sites_count", 2))
    for site in (1, 2, 3):
        if site > sites_count:
            continue
        topics.extend([
            f"{base_topic}/state/extra_safe_load_now/s{site}",
            f"{base_topic}/state/extra_safe_load_today/s{site}",
            f"{base_topic}/state/extra_safe_possible_now/s{site}",
            f"{base_topic}/state/extra_safe_total_now/s{site}",
            f"{base_topic}/state/extra_safe_possible_today/s{site}",
            f"{base_topic}/state/extra_safe_possible_tomorrow/s{site}",
        ])
    return topics


def _mqtt_extra_safe_discovery(cfg: Dict[str, Any], mqtt_cfg: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out = []
    sites_count = int(cfg.get("runtime", {}).get("sites_count", 2))
    base_topic = mqtt_cfg["base_topic"]
    discovery_prefix = mqtt_cfg["discovery_prefix"]
    for site in (1, 2, 3):
        if site > sites_count:
            continue
        site_name = _mqtt_site_name(cfg, site)
        # Consumo extra-safe ora (reale)
        object_id = f"s{site}_extra_safe_load_now"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_load_now/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Consumo Extra-safe Ora",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:flash",
        }))
        # Consumi extra-safe oggi (kWh)
        object_id = f"s{site}_extra_safe_load_today"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_load_today/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Extra-safe Consumi Oggi",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
            "icon": "mdi:chart-line",
        }))
        # Extra SAFE possibile ora (W)
        object_id = f"s{site}_extra_safe_possible_now"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_possible_now/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Extra SAFE aggiuntivo ora",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:flash",
        }))
        # Extra SAFE totale ora (W)
        object_id = f"s{site}_extra_safe_total_now"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_total_now/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Extra SAFE totale ora",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "W",
            "device_class": "power",
            "state_class": "measurement",
            "icon": "mdi:flash",
        }))
        # Extra SAFE possibile oggi (kWh)
        object_id = f"s{site}_extra_safe_possible_today"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_possible_today/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Extra SAFE possibile oggi",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
            "icon": "mdi:chart-line",
        }))
        # Extra SAFE possibile domani (kWh)
        object_id = f"s{site}_extra_safe_possible_tomorrow"
        unique_id = f"e_energymind_{object_id}"
        topic = f"{discovery_prefix}/sensor/e_energymind/{object_id}/config"
        state_topic = f"{base_topic}/state/extra_safe_possible_tomorrow/s{site}"
        out.append((topic, {
            "name": f"{site_name} - Extra SAFE possibile domani",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{base_topic}/availability",
            "device": _mqtt_device_info(),
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "measurement",
            "icon": "mdi:chart-line",
        }))
    return out


def _extra_safe_entities_for_site(cfg: Dict[str, Any], site: int) -> list[str]:
    automation_cfg = cfg.get("automation", {}) or {}
    raw_safe = automation_cfg.get("extra_safe_entities", [])
    safe_entities = []
    if isinstance(raw_safe, list):
        for item in raw_safe:
            if not isinstance(item, dict):
                continue
            try:
                s = int(item.get("site") or 0)
            except Exception:
                s = 0
            if s != site:
                continue
            if not bool(item.get("enabled", True)):
                continue
            eid = str(item.get("entity_id") or "").strip()
            if eid:
                safe_entities.append(eid)
    return safe_entities


def _calc_extra_safe_now_w(cfg: Dict[str, Any], site: int) -> float:
    total = 0.0
    found = False
    for eid in _extra_safe_entities_for_site(cfg, site):
        v = _state_num(eid)
        if v is not None:
            total += float(v)
            found = True
    if not found:
        return 0.0
    return round(total, 1)


def _mqtt_publish_discovery(cfg: Dict[str, Any]) -> None:
    if mqtt_client is None:
        return
    mqtt_cfg = _load_mqtt_options()
    if not mqtt_cfg.get("enabled"):
        return
    for topic, payload in _mqtt_extra_safe_discovery(cfg, mqtt_cfg):
        mqtt_client.publish(topic, payload, retain=True)


def _mqtt_clear(cfg: Dict[str, Any]) -> dict[str, int]:
    if mqtt_client is None:
        return {"cleared": 0}
    mqtt_cfg = _load_mqtt_options()
    if not mqtt_cfg.get("enabled"):
        return {"cleared": 0}
    cleared = 0
    for topic, _ in _mqtt_extra_safe_discovery(cfg, mqtt_cfg):
        mqtt_client.publish(topic, "", retain=True)
        cleared += 1
    for topic in _mqtt_state_topics(cfg, mqtt_cfg):
        mqtt_client.publish(topic, "", retain=True)
        cleared += 1
    return {"cleared": cleared}


def _mqtt_status_payload() -> dict[str, Any]:
    cfg = _load_mqtt_options()
    if not cfg.get("enabled"):
        return {"enabled": False, "connected": False, "last_error": None}
    if mqtt_client is None:
        return {"enabled": True, "connected": False, "last_error": "client_not_initialized"}
    st = mqtt_client.status()
    return {"enabled": True, "connected": st.connected, "last_error": st.last_error}


def _mqtt_publish_states(cfg: Dict[str, Any]) -> None:
    if mqtt_client is None:
        return
    mqtt_cfg = _load_mqtt_options()
    if not mqtt_cfg.get("enabled"):
        return
    base_topic = mqtt_cfg["base_topic"]
    sites_count = int(cfg.get("runtime", {}).get("sites_count", 2))
    for site in (1, 2, 3):
        if site > sites_count:
            continue
        # Consumo extra-safe ora (reale)
        value = _calc_extra_safe_now_w(cfg, site)
        key = f"s{site}_extra_safe_load_now"
        if last_mqtt_values.get(key) != value:
            last_mqtt_values[key] = value
            mqtt_client.publish(f"{base_topic}/state/extra_safe_load_now/s{site}", value, retain=True)

        row = last_forecast_cache.get(site) or {}
        possible_now = row.get("extra_safe_now_w")
        possible_today = row.get("extra_safe_today_kwh")
        possible_tomorrow = row.get("extra_safe_tomorrow_kwh")
        load_today = row.get("extra_safe_load_today_kwh")

        if load_today is not None:
            key = f"s{site}_extra_safe_load_today"
            if last_mqtt_values.get(key) != load_today:
                last_mqtt_values[key] = load_today
                mqtt_client.publish(f"{base_topic}/state/extra_safe_load_today/s{site}", load_today, retain=True)
        if possible_now is not None:
            total_now = None
            if value is not None:
                total_now = round(float(possible_now) + float(value), 1)
            if total_now is not None:
                key = f"s{site}_extra_safe_total_now"
                if last_mqtt_values.get(key) != total_now:
                    last_mqtt_values[key] = total_now
                    mqtt_client.publish(f"{base_topic}/state/extra_safe_total_now/s{site}", total_now, retain=True)
        if possible_now is not None:
            key = f"s{site}_extra_safe_possible_now"
            if last_mqtt_values.get(key) != possible_now:
                last_mqtt_values[key] = possible_now
                mqtt_client.publish(f"{base_topic}/state/extra_safe_possible_now/s{site}", possible_now, retain=True)
        if possible_today is not None:
            key = f"s{site}_extra_safe_possible_today"
            if last_mqtt_values.get(key) != possible_today:
                last_mqtt_values[key] = possible_today
                mqtt_client.publish(f"{base_topic}/state/extra_safe_possible_today/s{site}", possible_today, retain=True)
        if possible_tomorrow is not None:
            key = f"s{site}_extra_safe_possible_tomorrow"
            if last_mqtt_values.get(key) != possible_tomorrow:
                last_mqtt_values[key] = possible_tomorrow
                mqtt_client.publish(f"{base_topic}/state/extra_safe_possible_tomorrow/s{site}", possible_tomorrow, retain=True)


async def _refresh_forecast_cache() -> None:
    global last_forecast_cache, last_forecast_ts
    try:
        resp = await forecast()
        payload = json.loads(resp.body.decode("utf-8"))
        sites = payload.get("sites", []) if isinstance(payload, dict) else []
        cache: dict[int, dict[str, Any]] = {}
        if isinstance(sites, list):
            for row in sites:
                if not isinstance(row, dict):
                    continue
                try:
                    site = int(row.get("site") or 0)
                except Exception:
                    site = 0
                if site in (1, 2, 3):
                    cache[site] = row
        if cache:
            last_forecast_cache = cache
            last_forecast_ts = time.time()
    except Exception as exc:
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MQTT forecast cache error: {exc}")


def _rewrite_location(location: str, base_url: str) -> str:
    if not location:
        return location
    loc = location
    if loc.startswith(base_url):
        return "/ha" + loc[len(base_url):]
    if loc.startswith("/") and not loc.startswith("/ha/"):
        return "/ha" + loc
    return loc


def _rewrite_html_base(body: str) -> str:
    if "<base " in body:
        return body
    if "<head>" in body:
        return body.replace("<head>", "<head><base href=\"/ha/\">", 1)
    return "<base href=\"/ha/\">" + body


def _rewrite_html_paths(body: str) -> str:
    body = body.replace('href="/manifest.json"', 'href="/ha/manifest.json"')
    body = body.replace('"/service_worker.js"', '"/ha/service_worker.js"')
    body = body.replace('"/sw.js"', '"/ha/sw.js"')
    body = body.replace('"/auth/', '"/ha/auth/')
    body = body.replace('"/api/', '"/ha/api/')
    body = body.replace('href="/ha/', 'href="/ha/')
    body = body.replace('src="/ha/', 'src="/ha/')
    body = body.replace('href="/', 'href="/ha/')
    body = body.replace('src="/', 'src="/ha/')
    return body


async def _proxy_request(request: Request, target_path: str) -> Response:
    session = await _ensure_proxy_session()
    base = _ha_base_url()
    target = f"{base}/{target_path.lstrip('/')}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    headers.pop("host", None)
    headers.pop("accept-encoding", None)
    headers["accept-encoding"] = "identity"
    token = _ha_access_token()
    if token and "authorization" not in {k.lower() for k in headers.keys()}:
        headers["Authorization"] = f"Bearer {token}"
    body = await request.body()

    resp = await session.request(
        request.method,
        target,
        headers=headers,
        data=body,
        allow_redirects=False,
    )
    resp_headers = {
        k: v
        for k, v in resp.headers.items()
        if k.lower() not in HOP_HEADERS and k.lower() not in ("content-length", "content-encoding")
    }
    if "location" in resp_headers:
        resp_headers["location"] = _rewrite_location(resp_headers["location"], base)

    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type.lower():
        raw = await resp.read()
        text = raw.decode("utf-8", errors="ignore")
        text = _rewrite_html_base(text)
        text = _rewrite_html_paths(text)
        return Response(
            content=text,
            status_code=resp.status,
            headers=resp_headers,
            media_type="text/html",
        )

    async def _stream():
        async for chunk in resp.content.iter_chunked(65536):
            yield chunk

    return StreamingResponse(
        _stream(),
        status_code=resp.status,
        headers=resp_headers,
        background=BackgroundTask(resp.release),
    )


async def _ensure_proxy_session() -> aiohttp.ClientSession:
    global proxy_session
    if proxy_session is None or proxy_session.closed:
        proxy_session = aiohttp.ClientSession()
    return proxy_session


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


def _state_num(entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    st = ha.states.get(entity_id)
    if not st:
        return None
    return _num_or_none(st.get("state"))


def _state_str(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    st = ha.states.get(entity_id)
    if not st:
        return None
    raw = st.get("state")
    return None if raw is None else str(raw)


def _state_unit(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    st = ha.states.get(entity_id)
    if not st:
        return None
    attrs = st.get("attributes") or {}
    unit = attrs.get("unit_of_measurement")
    return None if unit is None else str(unit)


def _is_energy_unit(unit: str | None) -> bool:
    u = (unit or "").strip().lower()
    return u in ("kwh", "wh")


def _load_all_entities_store() -> Dict[str, list]:
    if not ALL_ENTITIES_PATH.exists():
        return {"s1": [], "s2": [], "s3": []}
    try:
        raw = json.loads(ALL_ENTITIES_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {"s1": [], "s2": [], "s3": []}
        out = {"s1": [], "s2": [], "s3": []}
        for key in ("s1", "s2", "s3"):
            items = raw.get(key, [])
            if isinstance(items, list):
                out[key] = items
        return out
    except Exception:
        return {"s1": [], "s2": [], "s3": []}


def _save_all_entities_store(data: Dict[str, list]) -> None:
    ALL_ENTITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    safe = {"s1": [], "s2": [], "s3": []}
    if isinstance(data, dict):
        for key in ("s1", "s2", "s3"):
            items = data.get(key, [])
            if isinstance(items, list):
                safe[key] = items
    ALL_ENTITIES_PATH.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")


def _db_init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Migrate: rename old samples -> history (keep data)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "history" not in tables and "samples" in tables:
            conn.execute("ALTER TABLE samples RENAME TO history")
        # Ensure history table exists with expected columns
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
              ts INTEGER NOT NULL,
              site INTEGER NOT NULL,
              entity_id TEXT NOT NULL,
              value REAL,
              raw TEXT,
              unit TEXT
            )
            """
        )
        cur = conn.execute("PRAGMA table_info(history)")
        cols = [row[1] for row in cur.fetchall()]
        if "entity_id" not in cols:
            conn.execute("ALTER TABLE history ADD COLUMN entity_id TEXT")
        # Backfill entity_id for legacy rows when key column exists
        if "key" in cols:
            cfg = load_config()
            ent_cfg = cfg.get("entities", {}) or {}
            for cfg_key, entity_id in ent_cfg.items():
                if not entity_id:
                    continue
                parsed = _parse_site_key(cfg_key)
                if not parsed:
                    continue
                site, key = parsed
                conn.execute(
                    "UPDATE history SET entity_id = ? WHERE entity_id IS NULL AND site = ? AND key = ?",
                    (entity_id, site, key),
                )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_ts ON history(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_site_entity ON history(site, entity_id)")
        conn.commit()


def _db_insert_rows(rows: list[tuple]) -> int:
    if not rows:
        return 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            "INSERT INTO history (ts, site, entity_id, value, raw, unit) VALUES (?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def _db_prune(cutoff_ts: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM history WHERE ts < ?", (cutoff_ts,))
        conn.commit()
    return cur.rowcount or 0


def _chunked(items: list, size: int = 200) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


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


def _load_history_series(conn: sqlite3.Connection, entity_id: str, since_ts: int) -> list[tuple[int, float]]:
    cur = conn.execute(
        "SELECT ts, value FROM history WHERE entity_id = ? AND ts >= ? AND value IS NOT NULL ORDER BY ts ASC",
        (entity_id, since_ts),
    )
    rows = cur.fetchall()
    out = []
    for ts, val in rows:
        try:
            out.append((int(ts), float(val)))
        except Exception:
            continue
    return out


def _load_history_series_window(conn: sqlite3.Connection, entity_id: str, start_ts: int, end_ts: int) -> list[tuple[int, float]]:
    series = _load_history_series(conn, entity_id, start_ts)
    return [(ts, val) for ts, val in series if ts < end_ts]


def _downsample(series: list[tuple[int, float]], max_points: int = 720) -> list[tuple[int, float]]:
    if len(series) <= max_points:
        return series
    step = max(1, len(series) // max_points)
    return series[::step]


def _svg_polyline(series: list[tuple[int, float]], width: int, height: int, pad: int, color: str) -> str:
    if not series:
        return ""
    xs = [p[0] for p in series]
    ys = [p[1] for p in series]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    dx = max_x - min_x or 1
    dy = max_y - min_y or 1
    w = width - pad * 2
    h = height - pad * 2
    pts = []
    for x, y in series:
        px = pad + (x - min_x) / dx * w
        py = pad + h - (y - min_y) / dy * h
        pts.append(f"{px:.1f},{py:.1f}")
    return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(pts)}" />'


def _svg_axes(width: int, height: int, pad: int) -> str:
    x1, y1 = pad, pad
    x2, y2 = width - pad, height - pad
    return (
        f'<line x1="{x1}" y1="{y2}" x2="{x2}" y2="{y2}" stroke="#3a4757" stroke-width="1" />'
        f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="#3a4757" stroke-width="1" />'
    )


def _svg_chart(series_map: dict[str, list[tuple[int, float]]], title: str) -> str:
    width, height, pad = 1200, 400, 40
    colors = ["#63e6be", "#4cc9f0", "#ff6b6b", "#f59f00", "#74c0fc"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0b121a"/>',
        _svg_axes(width, height, pad),
        f'<text x="{pad}" y="24" fill="#9fb0c3" font-size="16">{title}</text>',
    ]
    i = 0
    for name, series in series_map.items():
        if not series:
            continue
        color = colors[i % len(colors)]
        parts.append(_svg_polyline(series, width, height, pad, color))
        parts.append(f'<text x="{pad}" y="{50 + i*18}" fill="{color}" font-size="12">{name}</text>')
        i += 1
    parts.append("</svg>")
    return "".join(parts)


def _grid_exporting(grid: float | None, export_positive: bool) -> bool:
    if grid is None:
        return False
    return grid > 50 if export_positive else grid < -50


def _grid_importing(grid: float | None, export_positive: bool) -> bool:
    if grid is None:
        return False
    return grid < -50 if export_positive else grid > 50


def _percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    v = sorted(vals)
    k = (len(v) - 1) * p
    f = int(k)
    c = min(f + 1, len(v) - 1)
    if f == c:
        return v[f]
    return v[f] + (v[c] - v[f]) * (k - f)


def _integrate_energy_kwh(series: list[tuple[int, float]]) -> float:
    if len(series) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(series)):
        t0, v0 = series[i - 1]
        t1, v1 = series[i]
        dt = max(0, t1 - t0)
        avg_w = (v0 + v1) / 2.0
        total += (avg_w * dt) / 3600000.0
    return total


def _get_runtime_tz_name() -> str | None:
    try:
        cfg = load_config()
        tz_name = (cfg.get("runtime", {}) or {}).get("timezone")
    except Exception:
        tz_name = None
    if isinstance(tz_name, str) and tz_name.strip():
        return tz_name.strip()
    return None


def _local_dt(ts: int, tz_name: str | None = None) -> datetime:
    if tz_name:
        try:
            return datetime.fromtimestamp(ts, ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.fromtimestamp(ts)


def _day_start(ts: int | None = None) -> int:
    base = ts or int(time.time())
    tz_name = _get_runtime_tz_name()
    dt = _local_dt(base, tz_name)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp())


def _load_history_power_series(conn: sqlite3.Connection, entity_id: str, start_ts: int, end_ts: int) -> list[tuple[int, float]]:
    cur = conn.execute(
        "SELECT ts, raw, value, unit FROM history WHERE entity_id = ? AND ts >= ? AND ts < ? ORDER BY ts ASC",
        (entity_id, start_ts, end_ts),
    )
    rows = cur.fetchall()
    out = []
    for ts, raw, val, unit in rows:
        v = val if val is not None else _num_or_none(raw)
        if v is None:
            continue
        u = (unit or "").strip().lower()
        if u in ("kwh", "wh"):
            continue
        if u == "kw":
            v = v * 1000.0
        out.append((int(ts), float(v)))
    return out


def _daily_energy_kwh(conn: sqlite3.Connection, entity_id: str, day_start: int, day_end: int) -> float:
    series = _load_history_power_series(conn, entity_id, day_start, day_end)
    return round(_integrate_energy_kwh(series), 3)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    v = sorted(values)
    mid = len(v) // 2
    if len(v) % 2 == 1:
        return v[mid]
    return (v[mid - 1] + v[mid]) / 2.0


def _hourly_profile(conn: sqlite3.Connection, entity_id: str, days: int = 7) -> list[float]:
    now = int(time.time())
    start_ts = now - days * 86400
    tz_name = _get_runtime_tz_name()
    cur = conn.execute(
        "SELECT ts, raw, value, unit FROM history WHERE entity_id = ? AND ts >= ? ORDER BY ts ASC",
        (entity_id, start_ts),
    )
    series = []
    for ts, raw, val, unit in cur.fetchall():
        v = val if val is not None else _num_or_none(raw)
        if v is None:
            continue
        u = (unit or "").strip().lower()
        if u in ("kwh", "wh"):
            continue
        if u == "kw":
            v = v * 1000.0
        series.append((int(ts), float(v)))
    if len(series) < 2:
        return [0.0] * 24

    sums_ws = [0.0] * 24
    sums_s = [0.0] * 24
    for i in range(1, len(series)):
        t0, v0 = series[i - 1]
        t1, v1 = series[i]
        if t1 <= t0:
            continue
        seg_start = t0
        seg_end = t1
        while seg_start < seg_end:
            dt_local = _local_dt(seg_start, tz_name)
            hour_start_dt = dt_local.replace(minute=0, second=0, microsecond=0)
            hour_start = int(hour_start_dt.timestamp())
            hour_end = hour_start + 3600
            chunk_end = min(seg_end, hour_end)
            dt_seconds = chunk_end - seg_start
            if dt_seconds <= 0:
                break
            # linear interpolation for v at seg_start and chunk_end
            total_dt = t1 - t0
            r0 = (seg_start - t0) / total_dt
            r1 = (chunk_end - t0) / total_dt
            v_start = v0 + (v1 - v0) * r0
            v_end = v0 + (v1 - v0) * r1
            avg_v = (v_start + v_end) / 2.0
            h = dt_local.hour
            sums_ws[h] += avg_v * dt_seconds
            sums_s[h] += dt_seconds
            seg_start = chunk_end

    out = []
    for h in range(24):
        if sums_s[h] == 0:
            out.append(0.0)
        else:
            out.append(sums_ws[h] / sums_s[h])
    return out


def _hourly_profile_today(conn: sqlite3.Connection, entity_id: str, day_start: int, now_ts: int) -> list[float | None]:
    series = _load_history_power_series(conn, entity_id, day_start, now_ts)
    if len(series) < 2:
        return [None] * 24
    tz_name = _get_runtime_tz_name()

    sums_ws = [0.0] * 24
    sums_s = [0.0] * 24
    for i in range(1, len(series)):
        t0, v0 = series[i - 1]
        t1, v1 = series[i]
        if t1 <= t0:
            continue
        seg_start = t0
        seg_end = t1
        while seg_start < seg_end:
            dt_local = _local_dt(seg_start, tz_name)
            hour_start_dt = dt_local.replace(minute=0, second=0, microsecond=0)
            hour_start = int(hour_start_dt.timestamp())
            hour_end = hour_start + 3600
            chunk_end = min(seg_end, hour_end)
            dt_seconds = chunk_end - seg_start
            if dt_seconds <= 0:
                break
            total_dt = t1 - t0
            r0 = (seg_start - t0) / total_dt
            r1 = (chunk_end - t0) / total_dt
            v_start = v0 + (v1 - v0) * r0
            v_end = v0 + (v1 - v0) * r1
            avg_v = (v_start + v_end) / 2.0
            h = dt_local.hour
            sums_ws[h] += avg_v * dt_seconds
            sums_s[h] += dt_seconds
            seg_start = chunk_end

    out: list[float | None] = []
    for h in range(24):
        if sums_s[h] == 0:
            out.append(None)
        else:
            out.append(sums_ws[h] / sums_s[h])
    return out


def _hourly_profile_multi(conn: sqlite3.Connection, entity_ids: list[str], days: int = 7) -> list[float]:
    if not entity_ids:
        return [0.0] * 24
    acc = [0.0] * 24
    for eid in entity_ids:
        prof = _hourly_profile(conn, eid, days)
        acc = [a + b for a, b in zip(acc, prof)]
    return acc


def _hourly_profile_today_multi(conn: sqlite3.Connection, entity_ids: list[str], day_start: int, now_ts: int) -> list[float | None]:
    if not entity_ids:
        return [None] * 24
    acc: list[float | None] = [None] * 24
    for eid in entity_ids:
        prof = _hourly_profile_today(conn, eid, day_start, now_ts)
        for i in range(24):
            if prof[i] is None:
                continue
            acc[i] = (acc[i] or 0.0) + float(prof[i])
    return acc


def _hourly_profile_median(conn: sqlite3.Connection, entity_id: str, days: int = 7) -> list[float]:
    now = int(time.time())
    start_ts = now - days * 86400
    tz_name = _get_runtime_tz_name()
    cur = conn.execute(
        "SELECT ts, raw, value, unit FROM history WHERE entity_id = ? AND ts >= ? ORDER BY ts ASC",
        (entity_id, start_ts),
    )
    # Bucket by local date + hour
    buckets: dict[tuple[str, int], list[float]] = {}
    for ts, raw, val, unit in cur.fetchall():
        v = val if val is not None else _num_or_none(raw)
        if v is None:
            continue
        u = (unit or "").strip().lower()
        if u in ("kwh", "wh"):
            continue
        if u == "kw":
            v = v * 1000.0
        dt_local = _local_dt(int(ts), tz_name)
        key = (dt_local.strftime("%Y-%m-%d"), dt_local.hour)
        buckets.setdefault(key, []).append(float(v))
    if not buckets:
        return [0.0] * 24
    # Compute per-day-hour mean, then median across days for each hour
    per_hour_vals: list[list[float]] = [[] for _ in range(24)]
    for (day, hour), vals in buckets.items():
        if not vals:
            continue
        per_hour_vals[hour].append(sum(vals) / len(vals))
    out: list[float] = []
    for h in range(24):
        if not per_hour_vals[h]:
            out.append(0.0)
        else:
            out.append(_median(per_hour_vals[h]) or 0.0)
    return out


def _hourly_profile_median_multi(conn: sqlite3.Connection, entity_ids: list[str], days: int = 7) -> list[float]:
    if not entity_ids:
        return [0.0] * 24
    acc = [0.0] * 24
    for eid in entity_ids:
        prof = _hourly_profile_median(conn, eid, days)
        acc = [a + b for a, b in zip(acc, prof)]
    return acc


def _remaining_kwh_from_profile(profile_w: list[float], now_ts: int) -> float:
    tz_name = _get_runtime_tz_name()
    dt_local = _local_dt(now_ts, tz_name)
    h_now = dt_local.hour
    frac = (dt_local.minute + (dt_local.second / 60.0)) / 60.0
    remaining_wh = 0.0
    # remaining part of current hour
    if 0 <= h_now < 24:
        remaining_wh += profile_w[h_now] * max(0.0, 1.0 - frac)
    # remaining full hours
    for h in range(h_now + 1, 24):
        remaining_wh += profile_w[h]
    return max(0.0, remaining_wh / 1000.0)


def _daily_energy_kwh_multi(conn: sqlite3.Connection, entity_ids: list[str], day_start: int, day_end: int) -> float:
    if not entity_ids:
        return 0.0
    total = 0.0
    for eid in entity_ids:
        total += _daily_energy_kwh(conn, eid, day_start, day_end)
    return round(total, 3)


def _hourly_from_forecast_entity(entity_id: str | None, day_start: int, tz_offset_s: int = 3600) -> list[float] | None:
    if not entity_id:
        return None
    st = ha.states.get(entity_id)
    if not st:
        return None
    attrs = st.get("attributes") or {}
    data = None
    if isinstance(attrs, dict):
        data = attrs.get("watts") or attrs.get("w") or attrs.get("values")
    if not isinstance(data, dict):
        return None
    sums = [0.0] * 24
    counts = [0] * 24
    for k, v in data.items():
        try:
            ts = int(datetime.fromisoformat(str(k)).timestamp()) + tz_offset_s
        except Exception:
            continue
        if ts < day_start or ts >= day_start + 86400:
            continue
        try:
            val = float(v)
        except Exception:
            continue
        h = time.localtime(ts).tm_hour
        sums[h] += val
        counts[h] += 1
    if sum(counts) == 0:
        return None
    out = []
    for h in range(24):
        if counts[h] == 0:
            out.append(0.0)
        else:
            out.append(sums[h] / counts[h])
    return out


def _learn_rules_for_site(conn: sqlite3.Connection, site: int, ent_cfg: dict, export_positive: bool, safe_entities: list[str] | None = None) -> dict:
    def _eid(k: str) -> str | None:
        return ent_cfg.get(f"s{site}_{k}")

    pv_id = _eid("pv_power_total") or _eid("pv_power")
    load_id = _eid("load_power")
    grid_id = _eid("grid_power")
    batt_id = _eid("battery_power")
    if not all([pv_id, load_id, grid_id, batt_id]):
        return {}

    now = int(time.time())
    since_ts = now - 48 * 3600
    pv_series = _load_history_series(conn, pv_id, since_ts)
    load_series = _load_history_series(conn, load_id, since_ts)
    safe_series_list = []
    if safe_entities:
        for eid in safe_entities:
            safe_series_list.append(_load_history_series(conn, eid, since_ts))
    grid_series = _load_history_series(conn, grid_id, since_ts)
    batt_series = _load_history_series(conn, batt_id, since_ts)

    export_vals = []
    surplus_vals = []
    charge_frac = []
    charge_powers = []
    discharge_powers = []
    for ts, pv in pv_series[:: max(1, len(pv_series) // 300 or 1)]:
        load = _nearest_value(load_series, ts)
        if safe_series_list:
            safe_load = 0.0
            for s in safe_series_list:
                v = _nearest_value(s, ts)
                if v is not None:
                    safe_load += float(v)
            load = None if load is None else max(0.0, load - safe_load)
        grid = _nearest_value(grid_series, ts)
        batt = _nearest_value(batt_series, ts)
        if load is None or grid is None or batt is None:
            continue
        surplus = pv - load
        if surplus <= 0:
            continue
        surplus_vals.append(surplus)
        if _grid_exporting(grid, export_positive):
            export_vals.append(abs(grid))
        if batt < 0:
            charge_frac.append(abs(batt) / surplus if surplus > 0 else 0)
            charge_powers.append(abs(batt))
        elif batt > 0:
            discharge_powers.append(abs(batt))

    export_thr = _percentile(export_vals, 0.6) or PARTIAL_EXPORT_MIN_W
    export_thr = max(PARTIAL_EXPORT_MIN_W, float(export_thr))
    surplus_thr = _percentile(surplus_vals, 0.3) or 0.0
    charge_pct = _percentile(charge_frac, 0.5)

    # Estimate battery capacity from SOC delta and charged energy (last 24h)
    soc_id = _eid("battery_soc")
    cap_kwh = None
    if soc_id:
        soc_series = _load_history_raw_series(conn, soc_id, since_ts)
        soc_vals = [v for _, _, v, _ in soc_series if v is not None]
        if soc_vals:
            soc_min = min(soc_vals)
            soc_max = max(soc_vals)
            if soc_max - soc_min >= 5:
                batt_id = _eid("battery_power")
                if batt_id:
                    batt_series = _load_history_series(conn, batt_id, since_ts)
                    charge_kwh = _integrate_energy_kwh([(t, -p) for t, p in batt_series if p < 0])
                    try:
                        cap_kwh = round(charge_kwh / ((soc_max - soc_min) / 100.0), 2)
                    except Exception:
                        cap_kwh = None

    return {
        "export_threshold_w": int(round(export_thr)),
        "min_surplus_w": int(round(surplus_thr)),
        "min_duration_s": PARTIAL_MIN_DURATION_S,
        "typical_charge_pct": round(charge_pct * 100, 1) if charge_pct is not None else None,
        "max_charge_w": int(round(_percentile(charge_powers, 0.95))) if charge_powers else None,
        "max_discharge_w": int(round(_percentile(discharge_powers, 0.95))) if discharge_powers else None,
        "battery_capacity_kwh": cap_kwh,
        "samples": {
            "pv": len(pv_series),
            "load": len(load_series),
            "grid": len(grid_series),
            "battery": len(batt_series),
        },
    }


def _learn_rules() -> None:
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    export_positive = bool(cfg.get("runtime", {}).get("grid_export_positive", True))
    automation_cfg = cfg.get("automation", {}) or {}
    rules = {"updated_at": int(time.time()), "export_positive": export_positive}
    with sqlite3.connect(DB_PATH) as conn:
        for site in (1, 2, 3):
            raw_safe = automation_cfg.get("extra_safe_entities", [])
            safe_entities = []
            if isinstance(raw_safe, list):
                for item in raw_safe:
                    if not isinstance(item, dict):
                        continue
                    try:
                        s = int(item.get("site") or 0)
                    except Exception:
                        s = 0
                    if s != site:
                        continue
                    if not bool(item.get("enabled", True)):
                        continue
                    eid = str(item.get("entity_id") or "").strip()
                    if eid:
                        safe_entities.append(eid)
            rules[f"site{site}"] = _learn_rules_for_site(conn, site, ent_cfg, export_positive, safe_entities)
    cfg.setdefault("runtime", {})["learned_rules"] = rules
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} LEARN rules updated")


def _load_history_raw_series(conn: sqlite3.Connection, entity_id: str, since_ts: int) -> list[tuple[int, str | None, float | None, str | None]]:
    cur = conn.execute(
        "SELECT ts, raw, value, unit FROM history WHERE entity_id = ? AND ts >= ? ORDER BY ts ASC",
        (entity_id, since_ts),
    )
    rows = cur.fetchall()
    out = []
    for ts, raw, val, unit in rows:
        out.append((int(ts), raw, val, unit))
    return out


def _nearest_raw(series: list[tuple[int, str | None, float | None, str | None]], ts: int, max_delta_s: int = 90):
    if not series:
        return None
    lo = 0
    hi = len(series) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if series[mid][0] < ts:
            lo = mid + 1
        else:
            hi = mid
    idx = lo
    cand = []
    for j in (idx - 1, idx, idx + 1):
        if 0 <= j < len(series):
            cand.append(series[j])
    if not cand:
        return None
    best = min(cand, key=lambda x: abs(x[0] - ts))
    if abs(best[0] - ts) > max_delta_s:
        return None
    return {"ts": best[0], "raw": best[1], "value": best[2], "unit": best[3]}


def _raw_or_value_num(item: dict | None) -> float | None:
    if not item:
        return None
    if item.get("value") is not None:
        try:
            return float(item["value"])
        except Exception:
            return None
    raw = item.get("raw")
    return _num_or_none(raw)


def _nearest_value(series: list[tuple[int, float]], ts: int, max_delta_s: int = 90) -> float | None:
    if not series:
        return None
    # two-pointer scan by keeping index from previous use
    lo = 0
    hi = len(series) - 1
    # binary search for closest ts
    while lo < hi:
        mid = (lo + hi) // 2
        if series[mid][0] < ts:
            lo = mid + 1
        else:
            hi = mid
    idx = lo
    cand = []
    for j in (idx - 1, idx, idx + 1):
        if 0 <= j < len(series):
            cand.append(series[j])
    if not cand:
        return None
    best = min(cand, key=lambda x: abs(x[0] - ts))
    if abs(best[0] - ts) > max_delta_s:
        return None
    return best[1]


def _solar_window_today_real(conn: sqlite3.Connection, pv_entity_id: str | None, now_ts: int) -> tuple[float | None, float | None]:
    if not pv_entity_id:
        return None, None
    day_start = _day_start(now_ts)
    day_end = day_start + 86400
    series = _load_history_power_series(conn, pv_entity_id, day_start, day_end)
    if not series:
        series = []

    # If live PV is above threshold, extend series to "now" (history might lag).
    live_v = None
    try:
        live_v = _state_num(pv_entity_id)
    except Exception:
        live_v = None
    if live_v is not None:
        series = series + [(now_ts, float(live_v))]

    if len(series) < 2:
        return None, None

    series.sort(key=lambda x: x[0])
    min_w = SOLAR_REAL_MIN_W
    min_on_s = SOLAR_REAL_MIN_ON_MIN * 60
    min_off_s = SOLAR_REAL_MIN_OFF_MIN * 60

    runs: list[tuple[int, int]] = []
    run_start = None
    run_on_s = 0.0
    last_run_end = None
    below_s = 0.0
    confirmed_end = None

    for i in range(1, len(series)):
        t0, v0 = series[i - 1]
        t1, _v1 = series[i]
        if t1 <= t0:
            continue
        dt = t1 - t0
        if v0 >= min_w:
            if run_start is None:
                run_start = t0
                run_on_s = 0.0
            run_on_s += dt
            below_s = 0.0
        else:
            if run_start is not None:
                if run_on_s >= min_on_s:
                    run_end = t0
                    runs.append((run_start, run_end))
                    last_run_end = run_end
                run_start = None
                run_on_s = 0.0
            below_s += dt
            if last_run_end is not None and below_s >= min_off_s:
                confirmed_end = last_run_end

    # Close run if still above at end
    if run_start is not None and run_on_s >= min_on_s:
        run_end = series[-1][0]
        runs.append((run_start, run_end))
        last_run_end = run_end

    if not runs:
        return None, None

    start_ts = runs[0][0]
    end_ts = None
    if confirmed_end is not None:
        end_ts = confirmed_end
    else:
        if live_v is not None and live_v >= min_w:
            end_ts = now_ts

    tz_name = _get_runtime_tz_name()
    dt_min = _local_dt(start_ts, tz_name)
    start = dt_min.hour + (dt_min.minute / 60.0)
    if end_ts is None:
        return start, None
    dt_max = _local_dt(end_ts, tz_name)
    end = dt_max.hour + (dt_max.minute / 60.0)
    return start, end


def _collect_rows() -> list[tuple]:
    return []


def _collect_history_rows() -> list[tuple]:
    cfg = load_config()
    now_ts = int(time.time())
    rows: list[tuple] = []
    store = _load_all_entities_store()
    extra = (cfg.get("automation") or {}).get("extra_datalog_entities", []) or []
    safe = (cfg.get("automation") or {}).get("extra_safe_entities", []) or []
    seen: set[str] = set()

    def add_entity(site: int, entity_id: str):
        key = f"{site}:{entity_id}"
        if key in seen:
            return
        seen.add(key)
        st = ha.states.get(entity_id)
        if not st:
            return
        raw = st.get("state")
        val = _num_or_none(raw)
        unit = None
        attrs = st.get("attributes") or {}
        if isinstance(attrs, dict):
            unit = attrs.get("unit_of_measurement")
        raw_str = None if raw is None else str(raw)
        prev = last_history_state.get(key)
        if prev and prev[0] == raw_str:
            return
        last_history_state[key] = (raw_str, now_ts)
        rows.append((now_ts, site, entity_id, val, raw_str, None if unit is None else str(unit)))

    for site in (1, 2, 3):
        items = (store.get(f"s{site}") or [])
        for e in items:
            entity_id = e.get("entity_id")
            if entity_id:
                add_entity(site, entity_id)
    # Extra user-defined entities for datalogging
    if isinstance(extra, list):
        for item in extra:
            if not isinstance(item, dict):
                continue
            try:
                site = int(item.get("site") or 0)
            except Exception:
                site = 0
            entity_id = str(item.get("entity_id") or "").strip()
            if site in (1, 2, 3) and entity_id:
                add_entity(site, entity_id)
    # Extra-safe entities (optional loads) for learning/forecast
    if isinstance(safe, list):
        for item in safe:
            if not isinstance(item, dict):
                continue
            try:
                site = int(item.get("site") or 0)
            except Exception:
                site = 0
            entity_id = str(item.get("entity_id") or "").strip()
            if site in (1, 2, 3) and entity_id:
                add_entity(site, entity_id)

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
    last_history = 0.0
    global last_mqtt_publish
    while True:
        try:
            now = time.time()
            if now - last_history >= HISTORY_INTERVAL_S:
                hrows = await asyncio.to_thread(_collect_history_rows)
                if hrows:
                    inserted_h = await asyncio.to_thread(_db_insert_rows, hrows)
                    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} LOG history={inserted_h}")
                last_history = now
            await asyncio.to_thread(_maybe_generate_daily_report)
            global last_rules_update
            if last_rules_update is None or (now - last_rules_update) > LEARN_UPDATE_S:
                await asyncio.to_thread(_learn_rules)
                last_rules_update = now
            if now - last_prune > 3600:
                cutoff = int(now - (RETENTION_DAYS * 86400))
                deleted = await asyncio.to_thread(_db_prune, cutoff)
                if deleted:
                    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} PRUNE samples={deleted}")
                last_prune = now
            if mqtt_client is not None and (now - last_forecast_ts) >= FORECAST_CACHE_INTERVAL_S:
                await _refresh_forecast_cache()
            if mqtt_client is not None and (now - last_mqtt_publish) >= MQTT_PUBLISH_INTERVAL_S:
                cfg = load_config()
                _mqtt_publish_states(cfg)
                last_mqtt_publish = now
        except Exception as exc:
            _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} LOG error: {exc}")
        await asyncio.sleep(LOG_INTERVAL_S)


@app.get("/")
async def index():
    return FileResponse("/app/static/index.html")


@app.get("/index.html")
async def index_html():
    return FileResponse("/app/static/index.html")


@app.get("/ha")
async def ha_root():
    return RedirectResponse(url="/ha/")


@app.api_route(
    "/ha/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_proxy(path: str, request: Request):
    return await _proxy_request(request, path)


@app.api_route(
    "/static/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_static_proxy(path: str, request: Request):
    return await _proxy_request(request, f"static/{path}")


@app.api_route(
    "/frontend_latest/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_frontend_proxy(path: str, request: Request):
    return await _proxy_request(request, f"frontend_latest/{path}")


@app.api_route(
    "/hacsfiles/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_hacs_proxy(path: str, request: Request):
    return await _proxy_request(request, f"hacsfiles/{path}")


@app.api_route(
    "/dwains_dashboard/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_dwains_proxy(path: str, request: Request):
    return await _proxy_request(request, f"dwains_dashboard/{path}")


@app.api_route(
    "/local/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_local_proxy(path: str, request: Request):
    return await _proxy_request(request, f"local/{path}")


@app.api_route(
    "/media/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_media_proxy(path: str, request: Request):
    return await _proxy_request(request, f"media/{path}")


@app.api_route(
    "/manifest.json",
    methods=["GET", "HEAD"],
)
async def ha_manifest_proxy(request: Request):
    return await _proxy_request(request, "manifest.json")


@app.api_route(
    "/service_worker.js",
    methods=["GET", "HEAD"],
)
async def ha_sw_proxy(request: Request):
    return Response(status_code=404)


@app.api_route(
    "/sw.js",
    methods=["GET", "HEAD"],
)
async def ha_sw_short_proxy(request: Request):
    return Response(status_code=404)


@app.api_route(
    "/favicon.ico",
    methods=["GET", "HEAD"],
)
async def ha_favicon_proxy(request: Request):
    return await _proxy_request(request, "favicon.ico")


@app.api_route(
    "/lovelace/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_lovelace_proxy(path: str, request: Request):
    # HA frontend may redirect to /lovelace/0 without /ha prefix.
    return await _proxy_request(request, f"lovelace/{path}")


@app.api_route(
    "/lovelace",
    methods=["GET", "HEAD"],
)
async def ha_lovelace_root_proxy(request: Request):
    return await _proxy_request(request, "lovelace")


@app.api_route(
    "/dashboard-{name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_dashboard_root_proxy(name: str, request: Request):
    return await _proxy_request(request, f"dashboard-{name}")


@app.api_route(
    "/dashboard-{name}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_dashboard_proxy(name: str, path: str, request: Request):
    return await _proxy_request(request, f"dashboard-{name}/{path}")


@app.api_route(
    "/ha/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_auth_proxy(path: str, request: Request):
    return await _proxy_request(request, f"auth/{path}")


@app.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_auth_proxy_root(path: str, request: Request):
    # HA frontend sometimes posts /auth/token from root origin.
    return await _proxy_request(request, f"auth/{path}")


@app.api_route(
    "/ha/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def ha_api_proxy(path: str, request: Request):
    return await _proxy_request(request, f"api/{path}")


@app.websocket("/ha/{path:path}")
async def ha_ws_proxy(path: str, websocket: WebSocket):
    await websocket.accept()
    session = await _ensure_proxy_session()
    base = _ha_base_url()
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://") :]
    else:
        ws_base = "ws://homeassistant:8123"
    target = f"{ws_base}/{path}"
    if websocket.url.query:
        target = f"{target}?{websocket.url.query}"

    headers = {}
    origin = websocket.headers.get("origin")
    if origin:
        headers["Origin"] = origin

    async with session.ws_connect(target, headers=headers) as ws:
        async def client_to_ha():
            try:
                while True:
                    msg = await websocket.receive()
                    if msg["type"] == "websocket.receive":
                        if msg.get("text") is not None:
                            await ws.send_str(msg["text"])
                        elif msg.get("bytes") is not None:
                            await ws.send_bytes(msg["bytes"])
                    elif msg["type"] == "websocket.disconnect":
                        break
            finally:
                await ws.close()

        async def ha_to_client():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await websocket.send_text(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await websocket.send_bytes(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break

        await asyncio.gather(client_to_ha(), ha_to_client())


@app.websocket("/ha/api/websocket")
async def ha_api_ws_proxy(websocket: WebSocket):
    await _ha_ws_tunnel(websocket, "/api/websocket")


@app.websocket("/api/websocket")
async def ha_api_ws_proxy_root(websocket: WebSocket):
    # Keep add-on REST /api intact; only WS is proxied for HA frontend compatibility.
    await _ha_ws_tunnel(websocket, "/api/websocket")


async def _ha_ws_tunnel(websocket: WebSocket, path: str):
    await websocket.accept()
    session = await _ensure_proxy_session()
    base = _ha_base_url()
    if base.startswith("https://"):
        ws_base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        ws_base = "ws://" + base[len("http://") :]
    else:
        ws_base = "ws://homeassistant:8123"
    target = f"{ws_base}{path}"

    headers = {}
    token = _ha_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    origin = websocket.headers.get("origin")
    if origin:
        headers["Origin"] = origin

    async with session.ws_connect(target, headers=headers) as ws:
        async def client_to_ha():
            try:
                while True:
                    msg = await websocket.receive()
                    if msg["type"] == "websocket.receive":
                        if msg.get("text") is not None:
                            await ws.send_str(msg["text"])
                        elif msg.get("bytes") is not None:
                            await ws.send_bytes(msg["bytes"])
                    elif msg["type"] == "websocket.disconnect":
                        break
            finally:
                await ws.close()

        async def ha_to_client():
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await websocket.send_text(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await websocket.send_bytes(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break

        await asyncio.gather(client_to_ha(), ha_to_client())


@app.on_event("startup")
async def startup_event():
    global ha_task, log_task, proxy_session, mqtt_client
    proxy_session = await _ensure_proxy_session()
    try:
        await ha.start()
        ha_task = asyncio.create_task(ha.run())
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HA connected")
    except Exception as exc:
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HA connect error: {exc}")
    mqtt_cfg = _load_mqtt_options()
    if mqtt_cfg.get("enabled"):
        _log_action(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} MQTT enabled {mqtt_cfg['host']}:{mqtt_cfg['port']} base={mqtt_cfg['base_topic']}"
        )
        print(f"[e-EnergyMind] MQTT enabled {mqtt_cfg['host']}:{mqtt_cfg['port']} base={mqtt_cfg['base_topic']}")
        mqtt_client = MqttClient(
            host=mqtt_cfg["host"],
            port=int(mqtt_cfg["port"]),
            username=mqtt_cfg["username"],
            password=mqtt_cfg["password"],
            client_id=mqtt_cfg["client_id"],
        )
        mqtt_client.connect()
        mqtt_client.publish(f"{mqtt_cfg['base_topic']}/availability", "online", retain=True)
        _mqtt_publish_discovery(load_config())
        st = mqtt_client.status()
        print(f"[e-EnergyMind] MQTT status connected={st.connected} error={st.last_error}")
    else:
        print("[e-EnergyMind] MQTT disabled")
    log_task = asyncio.create_task(_logging_loop())


@app.on_event("shutdown")
async def shutdown_event():
    global proxy_session, mqtt_client
    if ha_task:
        ha_task.cancel()
    if log_task:
        log_task.cancel()
    if mqtt_client is not None:
        mqtt_cfg = _load_mqtt_options()
        if mqtt_cfg.get("enabled"):
            mqtt_client.publish(f"{mqtt_cfg['base_topic']}/availability", "offline", retain=True)
        mqtt_client.disconnect()
        mqtt_client = None
    if proxy_session and not proxy_session.closed:
        await proxy_session.close()
    await ha.close()


@app.get("/api/mqtt/status")
async def mqtt_status():
    return JSONResponse(_mqtt_status_payload())


@app.post("/api/mqtt/republish")
async def mqtt_republish():
    cfg = load_config()
    _mqtt_publish_discovery(cfg)
    return JSONResponse({"ok": True})


@app.post("/api/mqtt/clear")
async def mqtt_clear():
    cfg = load_config()
    info = _mqtt_clear(cfg)
    return JSONResponse({"ok": True, **info})


@app.get("/api/status")
async def get_status():
    cfg = load_config()
    now_ts = int(time.time())
    cfg_tz = None
    try:
        cfg_tz = (cfg.get("runtime", {}) or {}).get("timezone")
    except Exception:
        cfg_tz = None
    if isinstance(cfg_tz, str) and cfg_tz.strip():
        tz_name = cfg_tz.strip()
        try:
            dt = datetime.fromtimestamp(now_ts, ZoneInfo(tz_name))
            server_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            utc_offset_min = int(dt.utcoffset().total_seconds() / 60) if dt.utcoffset() else 0
        except Exception:
            tz_name = time.tzname[0] if time.tzname else "local"
            server_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
            utc_offset_min = int((time.mktime(time.localtime(now_ts)) - time.mktime(time.gmtime(now_ts))) / 60)
    else:
        tz_name = time.tzname[0] if time.tzname else "local"
        server_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_ts))
        utc_offset_min = int((time.mktime(time.localtime(now_ts)) - time.mktime(time.gmtime(now_ts))) / 60)
    return {
        "version": APP_VERSION,
        "runtime_mode": cfg.get("runtime", {}).get("mode", "dry-run"),
        "ha_connected": bool(ha._session) and ha.enabled,
        "server_time": server_time,
        "server_tz": tz_name,
        "server_utc_offset_min": utc_offset_min,
    }


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB"):
        n = n / 1024.0
        if n < 1024:
            return f"{n:.2f} {unit}"
    return f"{n:.2f} TB"


def _local_date_str(ts: int | None = None) -> str:
    if ts is None:
        ts = int(time.time())
    lt = time.localtime(ts)
    return f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"


def _local_time_str(ts: int) -> str:
    lt = time.localtime(ts)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}"


def _report_paths(date_str: str) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = REPORT_DIR / f"report_e-energymind_{date_str}.md"
    js = REPORT_DIR / f"report_e-energymind_{date_str}.json"
    return md, js


def _generate_report_for_day(date_str: str) -> None:
    start_ts = int(time.mktime(time.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S")))
    end_ts = start_ts + 86400
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    export_positive = bool(cfg.get("runtime", {}).get("grid_export_positive", True))
    devices = cfg.get("devices", {}) or {}
    def _site_name(site: int) -> str:
        name = devices.get(f"s{site}", {}).get("name") if isinstance(devices, dict) else None
        return str(name).strip() if name else f"Utenza {site}"

    def _eid(site: int, key: str) -> str | None:
        return ent_cfg.get(f"s{site}_{key}")

    report = {
        "date": date_str,
        "period": {"from": "00:00", "to": "23:59", "timezone": "Europe/Rome"},
        "sites": [
            {"id": 1, "name": _site_name(1), "inverters_parallel": 3},
            {"id": 2, "name": _site_name(2), "inverters_parallel": 2},
        ],
        "summary": {},
        "comparison": {},
        "partial_charge_events": {"criteria": {"surplus_gt_w": 0, "grid_export_gt_w": PARTIAL_EXPORT_MIN_W, "min_duration_s": PARTIAL_MIN_DURATION_S}},
        "hypotheses": [],
        "actions": [],
        "technical_summary": {},
    }

    md_lines = [
        f"# Report BMS Giornaliero — {date_str}",
        "Periodo: 00:00–23:59 (Europe/Rome)",
        f"Utenze: 1 (3 inverter in parallelo) — {_site_name(1)}, 2 (2 inverter in parallelo) — {_site_name(2)}",
        "",
    ]

    with sqlite3.connect(DB_PATH) as conn:
        for site in (1, 2):
            pv_id = _eid(site, "pv_power_total") or _eid(site, "pv_power")
            load_id = _eid(site, "load_power")
            grid_id = _eid(site, "grid_power")
            batt_id = _eid(site, "battery_power")
            soc_id = _eid(site, "battery_soc")
            temp_id = _eid(site, "battery_temp")
            mode_id = _eid(site, "storage_control_mode")
            exp_id = _eid(site, "grid_export_power")

            if not all([pv_id, load_id, grid_id, batt_id]):
                report["summary"][f"site{site}_missing"] = [k for k, v in {
                    "pv": pv_id, "load": load_id, "grid": grid_id, "battery": batt_id
                }.items() if not v]
                continue

            pv_series = _load_history_series_window(conn, pv_id, start_ts, end_ts)
            load_series = _load_history_series_window(conn, load_id, start_ts, end_ts)
            grid_series = _load_history_series_window(conn, grid_id, start_ts, end_ts)
            batt_series = _load_history_series_window(conn, batt_id, start_ts, end_ts)
            soc_series = _load_history_raw_series(conn, soc_id, start_ts) if soc_id else []
            temp_series = _load_history_raw_series(conn, temp_id, start_ts) if temp_id else []
            mode_series = _load_history_raw_series(conn, mode_id, start_ts) if mode_id else []
            exp_series = _load_history_raw_series(conn, exp_id, start_ts) if exp_id else []

            report["summary"][f"site{site}_series_counts"] = {
                "pv": len(pv_series),
                "load": len(load_series),
                "grid": len(grid_series),
                "battery": len(batt_series),
            }
            report["summary"][f"site{site}_grid_export_positive"] = export_positive

            events = []
            cond_since = None
            in_event = False
            for ts, pv in pv_series:
                if ts >= end_ts:
                    break
                load = _nearest_value(load_series, ts)
                grid = _nearest_value(grid_series, ts)
                batt = _nearest_value(batt_series, ts)
                if load is None or grid is None or batt is None:
                    continue
                surplus = pv - load
                cond_true = surplus > 0 and _grid_exporting(grid, export_positive) and abs(grid) > PARTIAL_EXPORT_MIN_W
                if cond_true:
                    if cond_since is None:
                        cond_since = ts
                    if not in_event and ts - cond_since >= PARTIAL_MIN_DURATION_S:
                        in_event = True
                    if not in_event:
                        continue
                else:
                    cond_since = None
                    in_event = False
                    continue
                charge = abs(batt) if batt < 0 else 0.0
                soc = _nearest_raw(soc_series, ts, 300)
                temp = _nearest_raw(temp_series, ts, 300)
                mode = _nearest_raw(mode_series, ts, 300)
                exp = _nearest_raw(exp_series, ts, 300)
                tags = []
                soc_val = _raw_or_value_num(soc)
                temp_val = _raw_or_value_num(temp)
                if soc_val is not None and soc_val >= 90:
                    tags.append("LIMIT_SOC")
                if temp_val is not None and temp_val <= 15:
                    tags.append("LIMIT_TEMP")
                if mode and (mode.get("raw") or "").strip() not in ("Self Use", "SelfUse", "Auto"):
                    tags.append("LIMIT_MODE")
                if exp and (exp.get("raw") or "").strip() not in ("0", "", None):
                    tags.append("LIMIT_EXPORT")
                if not tags:
                    tags.append("LIMIT_UNKNOWN")
                events.append({
                    "time": _local_time_str(ts),
                    "ts": ts,
                    "pv_w": pv,
                    "load_w": load,
                    "battery_w": batt,
                    "grid_w": grid,
                    "surplus_w": surplus,
                    "charge_w": charge,
                    "charge_pct": round(charge / surplus * 100, 1) if surplus > 0 else None,
                    "soc": soc_val,
                    "temp": temp_val,
                    "mode": mode.get("raw") if mode else None,
                    "export_limit": exp.get("raw") if exp else None,
                    "tags": tags,
                })

            report["partial_charge_events"][f"site{site}"] = events
            report["summary"][f"site{site}_partial_charge_events"] = len(events)

            # Charts disabled (SVG removed)

    md_lines.append("## Sintesi")
    md_lines.append(f"- Utenza 1: {report['summary'].get('site1_partial_charge_events', 0)} episodi di carica parziale.")
    md_lines.append(f"- Utenza 2: {report['summary'].get('site2_partial_charge_events', 0)} episodi di carica parziale.")
    for site in (1, 2):
        counts = report["summary"].get(f"site{site}_series_counts", {})
        inv = report["summary"].get(f"site{site}_grid_export_positive", True)
        if counts:
            md_lines.append(
                f"- Utenza {site}: campioni PV {counts.get('pv',0)}, Load {counts.get('load',0)}, Grid {counts.get('grid',0)}, Batt {counts.get('battery',0)}; Export positivo: {inv}"
            )
    md_lines.append("")

    for site in (1, 2):
        md_lines.append(f"## Eventi carica parziale — Utenza {site} — {_site_name(site)}")
        events = report["partial_charge_events"].get(f"site{site}", [])
        if not events:
            md_lines.append("Nessun evento.")
        else:
            for e in events:
                md_lines.append(
                    f"- {e['time']} PV {e['pv_w']}W, Load {e['load_w']}W, Batt {e['battery_w']}W, Grid {e['grid_w']}W, "
                    f"Surplus {e.get('surplus_w')}W, Carica {e.get('charge_w')}W ({e.get('charge_pct')}%), "
                    f"SOC {e.get('soc')}, Temp {e.get('temp')}, Mode {e.get('mode')}, Tags {','.join(e.get('tags', []))}"
                )
        md_lines.append("")

    # Technical narrative summary
    def _site_stats(site: int, events: list[dict]) -> dict:
        if not events:
            return {"events": 0}
        tag_counts: dict[str, int] = {}
        export_vals = []
        surplus_vals = []
        charge_pct_vals = []
        temp_vals = []
        soc_vals = []
        for e in events:
            for t in e.get("tags", []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
            if e.get("grid_w") is not None:
                export_vals.append(abs(float(e["grid_w"])))
            if e.get("surplus_w") is not None:
                surplus_vals.append(float(e["surplus_w"]))
            if e.get("charge_pct") is not None:
                charge_pct_vals.append(float(e["charge_pct"]))
            if e.get("temp") is not None:
                try:
                    temp_vals.append(float(e["temp"]))
                except Exception:
                    pass
            if e.get("soc") is not None:
                try:
                    soc_vals.append(float(e["soc"]))
                except Exception:
                    pass
        return {
            "events": len(events),
            "tag_counts": tag_counts,
            "export_avg": round(sum(export_vals) / len(export_vals), 1) if export_vals else None,
            "surplus_avg": round(sum(surplus_vals) / len(surplus_vals), 1) if surplus_vals else None,
            "charge_pct_avg": round(sum(charge_pct_vals) / len(charge_pct_vals), 1) if charge_pct_vals else None,
            "temp_avg": round(sum(temp_vals) / len(temp_vals), 1) if temp_vals else None,
            "soc_avg": round(sum(soc_vals) / len(soc_vals), 1) if soc_vals else None,
        }

    md_lines.append("## Relazione tecnica giornaliera")
    for site in (1, 2):
        events = report["partial_charge_events"].get(f"site{site}", [])
        st = _site_stats(site, events)
        report["technical_summary"][f"site{site}"] = st
        if st.get("events", 0) == 0:
            md_lines.append(f"- Utenza {site} — {_site_name(site)}: nessun evento di carica parziale rilevato.")
            continue
        tags = st.get("tag_counts", {})
        main_tag = max(tags, key=tags.get) if tags else "n/d"
        md_lines.append(
            f"- Utenza {site} — {_site_name(site)}: "
            f"{st['events']} eventi. Export medio {st.get('export_avg')} W, "
            f"surplus medio {st.get('surplus_avg')} W, carica media {st.get('charge_pct_avg')}%. "
            f"Temperatura media {st.get('temp_avg')} °C, SOC medio {st.get('soc_avg')}%. "
            f"Tag dominante: {main_tag}."
        )

    md_path, js_path = _report_paths(date_str)
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    js_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} REPORT generated {md_path} {js_path}")


def _maybe_generate_daily_report() -> None:
    global last_report_date
    now = time.time()
    lt = time.localtime(now)
    date_str = _local_date_str(int(now))
    if lt.tm_hour == 23 and lt.tm_min == 59:
        if last_report_date != date_str:
            _generate_report_for_day(date_str)
            last_report_date = date_str


@app.post("/api/reports/generate")
async def generate_report(date: str | None = None):
    if date:
        try:
            time.strptime(date, "%Y-%m-%d")
            date_str = date
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date")
    else:
        date_str = _local_date_str(int(time.time()))
    _generate_report_for_day(date_str)
    return JSONResponse({"ok": True, "date": date_str, "dir": str(REPORT_DIR)})


@app.get("/api/db_info")
async def db_info():
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {"size_bytes": size, "size_human": _fmt_bytes(size)}


@app.get("/api/logging_check")
async def logging_check(site: int | None = None, hours: int = 24):
    if site is not None and site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    hours = max(1, min(168, int(hours)))
    since_ts = int(time.time()) - hours * 3600
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}

    mapped = []
    for cfg_key, entity_id in ent_cfg.items():
        if not entity_id:
            continue
        parsed = _parse_site_key(cfg_key)
        if not parsed:
            continue
        s, key = parsed
        if site is not None and s != site:
            continue
        mapped.append({"site": s, "key": key, "entity_id": entity_id})

    by_entity = {m["entity_id"]: m for m in mapped}
    results = {}
    with sqlite3.connect(DB_PATH) as conn:
        for batch in _chunked(list(by_entity.keys()), 200):
            qmarks = ",".join(["?"] * len(batch))
            cur = conn.execute(
                f"SELECT entity_id, COUNT(*) AS cnt, MAX(ts) AS last_ts FROM history WHERE ts >= ? AND entity_id IN ({qmarks}) GROUP BY entity_id",
                (since_ts, *batch),
            )
            for entity_id, cnt, last_ts in cur.fetchall():
                results[entity_id] = {"count": int(cnt or 0), "last_ts": int(last_ts or 0)}

    present = []
    missing = []
    for entity_id, meta in by_entity.items():
        row = results.get(entity_id)
        if not row or row.get("count", 0) <= 0:
            missing.append({**meta})
        else:
            present.append({**meta, **row})

    return JSONResponse({
        "ok": True,
        "site": site,
        "since_hours": hours,
        "total_mapped": len(mapped),
        "total_present": len(present),
        "total_missing": len(missing),
        "missing": missing,
        "present": present,
    })


@app.get("/api/analysis")
async def analysis(site: int = 1, hours: int = 24):
    if site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    hours = max(1, min(168, int(hours)))
    since_ts = int(time.time()) - hours * 3600
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}

    # Required signals (mapped)
    def _eid(k: str) -> str | None:
        return ent_cfg.get(f"s{site}_{k}")

    pv_id = _eid("pv_power_total") or _eid("pv_power")
    load_id = _eid("load_power")
    grid_id = _eid("grid_power")
    batt_id = _eid("battery_power")

    if not all([pv_id, load_id, grid_id, batt_id]):
        return JSONResponse({"ok": False, "missing": [k for k, v in {
            "pv_power_total": pv_id, "load_power": load_id, "grid_power": grid_id, "battery_power": batt_id
        }.items() if not v]})

    events = []
    with sqlite3.connect(DB_PATH) as conn:
        pv_series = _load_history_series(conn, pv_id, since_ts)
        load_series = _load_history_series(conn, load_id, since_ts)
        grid_series = _load_history_series(conn, grid_id, since_ts)
        batt_series = _load_history_series(conn, batt_id, since_ts)

    for ts, pv in pv_series:
        load = _nearest_value(load_series, ts)
        grid = _nearest_value(grid_series, ts)
        batt = _nearest_value(batt_series, ts)
        if load is None or grid is None or batt is None:
            continue
        # Heuristic: charge power is abs of negative battery power
        charge = abs(batt) if batt < 0 else 0.0
        surplus = pv - load
        if surplus <= 200:
            continue
        # exporting while not charging enough
        if grid > 200 and charge < surplus * 0.6:
            events.append({
                "ts": ts,
                "pv": pv,
                "load": load,
                "grid": grid,
                "battery_power": batt,
                "charge_est": charge,
                "surplus": surplus,
            })

    return JSONResponse({"ok": True, "site": site, "hours": hours, "events": events})


@app.get("/api/history")
async def get_history(entity_id: str = "", site: int = 1, hours: int = 24):
    entity_id = (entity_id or "").strip()
    if not entity_id:
        raise HTTPException(status_code=400, detail="Missing entity_id")
    if site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    hours = max(1, min(168, int(hours)))
    since_ts = int(time.time()) - hours * 3600
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    key_match = None
    for cfg_key, eid in ent_cfg.items():
        if eid == entity_id:
            parsed = _parse_site_key(cfg_key)
            if parsed:
                s, k = parsed
                if s == site:
                    key_match = k
                    break
    with sqlite3.connect(DB_PATH) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()]
        if "key" in cols and key_match:
            cur = conn.execute(
                "SELECT ts, value, raw, unit FROM history WHERE site = ? AND (entity_id = ? OR (entity_id IS NULL AND key = ?)) AND ts >= ? ORDER BY ts ASC",
                (site, entity_id, key_match, since_ts),
            )
        else:
            cur = conn.execute(
                "SELECT ts, value, raw, unit FROM history WHERE site = ? AND entity_id = ? AND ts >= ? ORDER BY ts ASC",
                (site, entity_id, since_ts),
            )
        rows = cur.fetchall()
    items = [{"ts": r[0], "value": r[1], "raw": r[2], "unit": r[3]} for r in rows]
    return JSONResponse({"site": site, "entity_id": entity_id, "hours": hours, "items": items})


@app.get("/api/insights")
async def insights():
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    export_positive = bool(cfg.get("runtime", {}).get("grid_export_positive", True))
    learned = cfg.get("runtime", {}).get("learned_rules", {}) if isinstance(cfg.get("runtime", {}), dict) else {}

    def _eid(site: int, key: str) -> str | None:
        return ent_cfg.get(f"s{site}_{key}")

    def _site_insight(site: int):
        pv = _state_num(_eid(site, "pv_power_total")) or _state_num(_eid(site, "pv_power"))
        load = _state_num(_eid(site, "load_power"))
        grid = _state_num(_eid(site, "grid_power"))
        batt = _state_num(_eid(site, "battery_power"))
        soc = _state_num(_eid(site, "battery_soc"))
        temp = _state_num(_eid(site, "battery_temp"))
        mode = _state_str(_eid(site, "storage_control_mode"))
        export_lim = _state_str(_eid(site, "grid_export_power"))
        fault = _state_str(_eid(site, "device_fault"))
        inv = _state_str(_eid(site, "inverter_status"))

        reasons = []
        suggestions = []
        status = "OK"
        confidence = "low"

        site_rules = learned.get(f"site{site}", {}) if isinstance(learned, dict) else {}
        export_thr = float(site_rules.get("export_threshold_w", PARTIAL_EXPORT_MIN_W))
        min_surplus = float(site_rules.get("min_surplus_w", 0))
        if pv is not None and load is not None and grid is not None and batt is not None:
            surplus = pv - load
            grid_exporting = _grid_exporting(grid, export_positive)
            grid_importing = _grid_importing(grid, export_positive)
            cond = surplus > min_surplus and grid_exporting and abs(grid) > export_thr
            if cond:
                since = insight_condition_since.get(site)
                if since is None:
                    insight_condition_since[site] = time.time()
                elif (time.time() - since) < PARTIAL_MIN_DURATION_S:
                    cond = False
            else:
                insight_condition_since.pop(site, None)

            if cond:
                status = "CARICA_PARZIALE"
                confidence = "medium"
                charge = abs(batt) if batt < 0 else 0.0
                reasons.append(f"Surplus {int(surplus)}W · Export {int(grid)}W")
                reasons.append(f"Rete: {'export' if grid_exporting else 'import'} {int(grid)}W")
                _log_action(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} INSIGHT s{site} CARICA_PARZIALE "
                    f"PV {int(pv)}W Load {int(load)}W Batt {int(batt)}W Grid {int(grid)}W "
                    f"Surplus {int(surplus)}W"
                )
                if soc is not None and soc >= 90:
                    reasons.append("SOC alto")
                if temp is not None and temp <= 15:
                    reasons.append("Temperatura batteria bassa")
                if mode and mode not in ("Self Use", "SelfUse", "Auto"):
                    reasons.append(f"Storage mode: {mode}")
                if export_lim and export_lim not in ("0", "Disabled", "None", ""):
                    reasons.append(f"Export limit: {export_lim}")
                if fault and fault not in ("OK", "Ok", "None"):
                    reasons.append(f"Fault: {fault}")
                if inv and inv not in ("On-grid", "On grid", "OnGrid"):
                    reasons.append(f"Inverter: {inv}")
                if surplus > 0 and grid_importing:
                    reasons.append("Import da rete durante surplus")
                if not reasons:
                    reasons.append("Limite interno BMS/inverter")
                suggestions.append("Verifica limiti carica (BMS) e temperatura batteria")
                suggestions.append("Controlla modalità Storage e Export limit")
                suggestions.append(f"PV {int(pv)}W · Load {int(load)}W · Batt {int(batt)}W · Grid {int(grid)}W")
        else:
            status = "DATI_INCOMPLETI"
            reasons.append("Mancano alcune entità chiave")

        forecast = {
            "t_plus_60s": {
                "battery_power": batt,
                "grid_power": grid,
                "confidence": "low"
            }
        }
        return {
            "site": site,
            "status": status,
            "confidence": confidence,
            "reasons": reasons,
            "suggestions": suggestions,
            "forecast": forecast
        }

    site1 = _site_insight(1)
    site2 = _site_insight(2)
    global_status = "OK"
    if site1["status"] == "CARICA_PARZIALE" or site2["status"] == "CARICA_PARZIALE":
        global_status = "CARICA_PARZIALE"
    return JSONResponse({
        "global": {
            "status": global_status,
            "notes": "Analisi in tempo reale basata su sensori correnti."
        },
        "sites": [site1, site2],
        "learned_rules": learned
    })


@app.get("/api/bms_history")
async def bms_history(days: int = 14):
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    export_positive = bool(cfg.get("runtime", {}).get("grid_export_positive", True))
    now_ts = int(time.time())
    days = max(1, min(60, int(days or 14)))

    def _eid(site: int, key: str) -> str | None:
        return ent_cfg.get(f"s{site}_{key}")

    sites_out = []
    with sqlite3.connect(DB_PATH) as conn:
        for site in (1, 2, 3):
            if site > int(cfg.get("runtime", {}).get("sites_count", 2)):
                continue
            pv_id = _eid(site, "pv_power_total") or _eid(site, "pv_power")
            load_id = _eid(site, "load_power")
            grid_id = _eid(site, "grid_power")
            batt_id = _eid(site, "battery_power")
            missing = []
            if not pv_id:
                missing.append("pv")
            if not load_id:
                missing.append("load")
            if not grid_id:
                missing.append("grid")
            if not batt_id:
                missing.append("battery")

            items = []
            if not missing:
                for d in range(days):
                    day_start = _day_start(now_ts - (d * 86400))
                    day_end = day_start + 86400
                    pv_series = _load_history_series_window(conn, pv_id, day_start, day_end)
                    load_series = _load_history_series_window(conn, load_id, day_start, day_end)
                    grid_series = _load_history_series_window(conn, grid_id, day_start, day_end)
                    batt_series = _load_history_series_window(conn, batt_id, day_start, day_end)
                    if not pv_series or not load_series or not grid_series or not batt_series:
                        continue

                    max_charge = max((abs(v) for _, v in batt_series if v < 0), default=0.0)
                    max_discharge = max((abs(v) for _, v in batt_series if v > 0), default=0.0)

                    charge_fracs = []
                    surplus_vals = []
                    export_vals = []
                    for ts, pv in pv_series:
                        load = _nearest_value(load_series, ts)
                        grid = _nearest_value(grid_series, ts)
                        batt = _nearest_value(batt_series, ts)
                        if load is None or grid is None or batt is None:
                            continue
                        surplus = pv - load
                        if surplus <= 0:
                            continue
                        surplus_vals.append(surplus)
                        if _grid_exporting(grid, export_positive):
                            export_vals.append(abs(grid))
                        if batt < 0:
                            charge_fracs.append(min(1.0, abs(batt) / surplus))

                    charge_pct = round((sum(charge_fracs) / len(charge_fracs)) * 100.0, 1) if charge_fracs else None
                    surplus_avg = round(sum(surplus_vals) / len(surplus_vals), 1) if surplus_vals else None
                    export_avg = round(sum(export_vals) / len(export_vals), 1) if export_vals else None

                    items.append({
                        "date": time.strftime("%Y-%m-%d", time.localtime(day_start)),
                        "ts": day_start,
                        "max_charge_w": int(round(max_charge)) if max_charge else 0,
                        "max_discharge_w": int(round(max_discharge)) if max_discharge else 0,
                        "charge_pct": charge_pct,
                        "surplus_avg_w": surplus_avg,
                        "export_avg_w": export_avg,
                        "samples": len(pv_series),
                    })

            items.sort(key=lambda x: x["ts"])
            sites_out.append({"site": site, "items": items, "missing": missing})

    return JSONResponse({"days": days, "sites": sites_out})


@app.get("/api/forecast")
async def forecast():
    cfg = load_config()
    ent_cfg = cfg.get("entities", {}) or {}
    forecast_cfg = cfg.get("forecast", {}) or {}
    automation_cfg = cfg.get("automation", {}) or {}
    learned = cfg.get("runtime", {}).get("learned_rules", {}) if isinstance(cfg.get("runtime", {}), dict) else {}
    runtime = cfg.setdefault("runtime", {})
    pv_adjust_meta = runtime.get("pv_adjust_meta")
    if not isinstance(pv_adjust_meta, dict):
        pv_adjust_meta = {}
        runtime["pv_adjust_meta"] = pv_adjust_meta
    pv_meta_dirty = False

    def _eid(site: int, key: str) -> str | None:
        return ent_cfg.get(f"s{site}_{key}")

    now_ts = int(time.time())
    today_start = _day_start(now_ts)
    results = []

    with sqlite3.connect(DB_PATH) as conn:
        for site in (1, 2, 3):
            if site > int(cfg.get("runtime", {}).get("sites_count", 2)):
                continue

            site_key = f"site{site}"
            site_rules = learned.get(site_key, {}) if isinstance(learned, dict) else {}
            fc = forecast_cfg.get(f"s{site}", {}) if isinstance(forecast_cfg, dict) else {}

            pv_id = _eid(site, "pv_power_total") or _eid(site, "pv_power")
            load_id = _eid(site, "load_power")
            pv_today_id = _eid(site, "today_production_kwh")
            load_today_id = _eid(site, "today_load_kwh")
            soc_id = _eid(site, "battery_soc")
            batt_id = _eid(site, "battery_power")
            export_limit_id = _eid(site, "grid_export_power")

            pv_fc_today_id = (fc.get("pv_forecast_today") or "").strip() or _eid(site, "forecast_today_kwh")
            pv_fc_tom_id = (fc.get("pv_forecast_tomorrow") or "").strip() or _eid(site, "forecast_tomorrow_kwh")
            pv_fc_today_hourly_id = (fc.get("pv_forecast_today_hourly") or "").strip()
            pv_fc_tom_hourly_id = (fc.get("pv_forecast_tomorrow_hourly") or "").strip()
            load_daily_id = (fc.get("load_daily") or "").strip()
            load_daily_is_today = bool(load_daily_id and load_today_id and load_daily_id == load_today_id)

            pv_fc_today = _state_num(pv_fc_today_id)
            pv_fc_tom = _state_num(pv_fc_tom_id)
            if pv_fc_today is None and pv_fc_today_hourly_id:
                pv_fc_today = _state_num(pv_fc_today_hourly_id)
            if pv_fc_tom is None and pv_fc_tom_hourly_id:
                pv_fc_tom = _state_num(pv_fc_tom_hourly_id)
            load_fc_today = _state_num(load_daily_id) if (load_daily_id and not load_daily_is_today) else None

            soc_now = _state_num(soc_id)
            export_limit = fc.get("export_limit_w") if fc.get("export_limit_w") is not None else _state_num(export_limit_id)

            raw_safe = automation_cfg.get("extra_safe_entities", [])
            safe_entities = []
            if isinstance(raw_safe, list):
                for item in raw_safe:
                    if not isinstance(item, dict):
                        continue
                    try:
                        s = int(item.get("site") or 0)
                    except Exception:
                        s = 0
                    if s != site:
                        continue
                    if not bool(item.get("enabled", True)):
                        continue
                    eid = str(item.get("entity_id") or "").strip()
                    if eid:
                        safe_entities.append(eid)

            # Auto baselines from history (7 giorni)
            pv_days = []
            load_days = []
            safe_days = []
            for d in range(1, 8):
                day_start = today_start - d * 86400
                day_end = day_start + 86400
                if pv_id:
                    pv_days.append(_daily_energy_kwh(conn, pv_id, day_start, day_end))
                if load_id:
                    load_days.append(_daily_energy_kwh(conn, load_id, day_start, day_end))
                if safe_entities:
                    safe_days.append(_daily_energy_kwh_multi(conn, safe_entities, day_start, day_end))
            pv_base = _median([v for v in pv_days if v > 0])
            load_base = _median([v for v in load_days if v > 0])
            safe_base = _median([v for v in safe_days if v > 0]) if safe_days else 0.0

            pv_today_unit = _state_unit(pv_today_id)
            # Battery-day starts at solar production start (not midnight)
            solar_day_start_ts = today_start
            if pv_id:
                solar_start_est = None
                real_start, _real_end = _solar_window_today_real(conn, pv_id, now_ts)
                if real_start is not None:
                    solar_start_est = real_start
                else:
                    pv_profile_fc_tmp = _hourly_from_forecast_entity(pv_fc_today_hourly_id, today_start) or _hourly_profile(conn, pv_id, 7)
                    if pv_profile_fc_tmp:
                        for h in range(0, 24):
                            if pv_profile_fc_tmp[h] >= SOLAR_END_W_THRESHOLD:
                                solar_start_est = float(h)
                                break
                if solar_start_est is not None:
                    solar_day_start_ts = today_start + int(max(0.0, min(23.99, solar_start_est)) * 3600)

            safe_today_kwh = _daily_energy_kwh_multi(conn, safe_entities, solar_day_start_ts, now_ts) if safe_entities else 0.0
            safe_now_w = None
            if safe_entities:
                total = 0.0
                for eid in safe_entities:
                    v = _state_num(eid)
                    if v is not None:
                        total += float(v)
                safe_now_w = round(total, 1)

            # Correction factor if forecast entity present and history exists
            pv_factor = 1.0
            pv_factor_hist = None
            if pv_fc_today_id:
                hist_fc = _load_history_raw_series(conn, pv_fc_today_id, today_start - 8 * 86400)
                if hist_fc:
                    # build daily max map from forecast
                    fc_map = {}
                    for ts, raw, val, _ in hist_fc:
                        v = val if val is not None else _num_or_none(raw)
                        if v is None:
                            continue
                        day = time.strftime("%Y-%m-%d", time.localtime(ts))
                        fc_map[day] = max(fc_map.get(day, 0), float(v))

                    act_map = {}
                    if pv_today_id and _is_energy_unit(pv_today_unit):
                        hist_act = _load_history_raw_series(conn, pv_today_id, today_start - 8 * 86400)
                        for ts, raw, val, _ in hist_act:
                            v = val if val is not None else _num_or_none(raw)
                            if v is None:
                                continue
                            day = time.strftime("%Y-%m-%d", time.localtime(ts))
                            act_map[day] = max(act_map.get(day, 0), float(v))
                    elif pv_id:
                        for day in fc_map.keys():
                            try:
                                dts = int(time.mktime(time.strptime(day, "%Y-%m-%d")))
                            except Exception:
                                continue
                            act_map[day] = _daily_energy_kwh(conn, pv_id, dts, dts + 86400)

                    ratios = []
                    for day, fc_val in fc_map.items():
                        act_val = act_map.get(day)
                        if act_val and fc_val:
                            ratios.append(act_val / fc_val)
                    if ratios:
                        pv_factor_hist = max(0.6, min(1.4, _median(ratios) or 1.0))
                        pv_factor = pv_factor_hist
                        # Log pv_adjust changes (once per day/site) for transparency
                        common_days = sorted(set(fc_map.keys()) & set(act_map.keys()))
                        if common_days:
                            last_day = common_days[-1]
                            fc_val = fc_map.get(last_day)
                            act_val = act_map.get(last_day)
                            ratio = (act_val / fc_val) if (act_val and fc_val) else None
                            meta = pv_adjust_meta.get(f"s{site}", {}) if isinstance(pv_adjust_meta.get(f"s{site}"), dict) else {}
                            last_logged_day = meta.get("last_day")
                            last_logged_factor = meta.get("pv_adjust")
                            last_ts = meta.get("last_ts") or 0
                            need_log = False
                            if last_logged_day != last_day:
                                need_log = True
                            elif last_logged_factor is not None and abs(float(pv_factor) - float(last_logged_factor)) >= 0.02 and (now_ts - int(last_ts)) > 6 * 3600:
                                need_log = True
                            if need_log:
                                _log_action(
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} PV_ADJUST site={site} day={last_day} "
                                    f"forecast={round(fc_val,2) if fc_val is not None else 'n/d'} "
                                    f"actual={round(act_val,2) if act_val is not None else 'n/d'} "
                                    f"ratio={round(ratio,3) if ratio is not None else 'n/d'} "
                                    f"pv_adjust={round(pv_factor,3)}"
                                )
                                err_pct = None
                                if fc_val:
                                    try:
                                        err_pct = (act_val - fc_val) / fc_val * 100.0
                                    except Exception:
                                        err_pct = None
                                pv_adjust_meta[f"s{site}"] = {
                                    "last_day": last_day,
                                    "pv_adjust": round(pv_factor, 3),
                                    "forecast": round(fc_val, 2) if fc_val is not None else None,
                                    "actual": round(act_val, 2) if act_val is not None else None,
                                    "error_pct": round(err_pct, 1) if err_pct is not None else None,
                                    "last_ts": now_ts,
                                }
                                pv_meta_dirty = True

            # Fallback alignment values (today, partial) if no meta available yet
            fallback_fc_kwh = None
            fallback_act_kwh = None
            fallback_err_pct = None
            if pv_fc_today_id and pv_today_id:
                fc_now = _state_num(pv_fc_today_id)
                act_now = None
                if _is_energy_unit(pv_today_unit):
                    act_now = _state_num(pv_today_id)
                elif pv_id:
                    act_now = _daily_energy_kwh(conn, pv_id, today_start, now_ts)
                if fc_now is not None and act_now is not None:
                    fallback_fc_kwh = round(fc_now, 2)
                    fallback_act_kwh = round(act_now, 2)
                    if fc_now:
                        try:
                            fallback_err_pct = round((act_now - fc_now) / fc_now * 100.0, 1)
                        except Exception:
                            fallback_err_pct = None

            # Auto parameters from learned rules / history
            cap_kwh = fc.get("battery_capacity_kwh") if fc.get("battery_capacity_kwh") is not None else site_rules.get("battery_capacity_kwh")
            max_charge_w_cfg = fc.get("max_charge_w") if fc.get("max_charge_w") is not None else None
            max_discharge_w_cfg = fc.get("max_discharge_w") if fc.get("max_discharge_w") is not None else None
            max_charge_w = max_charge_w_cfg if max_charge_w_cfg is not None else site_rules.get("max_charge_w")
            max_discharge_w = max_discharge_w_cfg if max_discharge_w_cfg is not None else site_rules.get("max_discharge_w")

            min_soc = fc.get("min_soc") if fc.get("min_soc") is not None else None
            max_soc = fc.get("max_soc") if fc.get("max_soc") is not None else None
            if soc_id and (min_soc is None or max_soc is None):
                soc_hist = _load_history_raw_series(conn, soc_id, today_start - 8 * 86400)
                soc_vals = []
                for _, raw, val, _ in soc_hist:
                    v = val if val is not None else _num_or_none(raw)
                    if v is None:
                        continue
                    soc_vals.append(float(v))
                if soc_vals:
                    if min_soc is None:
                        min_soc = round(min(soc_vals), 1)
                    if max_soc is None:
                        max_soc = round(max(soc_vals), 1)

            # Real max charge/discharge from history (always compute if batt_id present)
            learned_max_charge = None
            learned_max_discharge = None
            if batt_id:
                batt_hist = _load_history_series(conn, batt_id, today_start - 2 * 86400)
                charge_vals = [abs(v) for _, v in batt_hist if v < 0]
                dis_vals = [abs(v) for _, v in batt_hist if v > 0]
                if charge_vals:
                    learned_max_charge = int(round(_percentile(charge_vals, 0.95)))
                if dis_vals:
                    learned_max_discharge = int(round(_percentile(dis_vals, 0.95)))
            if max_charge_w is None:
                max_charge_w = learned_max_charge
            if max_discharge_w is None:
                max_discharge_w = learned_max_discharge

            # Today: prefer real measured energy; Tomorrow: forecast corrected by pv_adjust
            pv_today_real_kwh = _daily_energy_kwh(conn, pv_id, solar_day_start_ts, now_ts) if pv_id else None
            load_today_real_kwh = _daily_energy_kwh(conn, load_id, solar_day_start_ts, now_ts) if load_id else None
            pv_today_kwh = pv_today_real_kwh if pv_today_real_kwh is not None else ((pv_fc_today * pv_factor) if pv_fc_today is not None else pv_base)
            pv_tom_kwh = (pv_fc_tom * pv_factor) if pv_fc_tom is not None else pv_base
            load_today_kwh = load_today_real_kwh if load_today_real_kwh is not None else ((load_fc_today if load_fc_today is not None else load_base) or 0.0)
            load_tom_kwh = load_today_kwh
            if safe_base:
                load_today_kwh = max(0.0, load_today_kwh - safe_base)
                load_tom_kwh = max(0.0, load_tom_kwh - safe_base)
            if safe_today_kwh:
                load_today_kwh = max(0.0, load_today_kwh - safe_today_kwh)

            # Estimate surplus and end SOC (initial)
            surplus_today = None
            export_today = None
            end_soc = None
            if pv_today_kwh is not None and load_today_kwh is not None:
                surplus = pv_today_kwh - load_today_kwh
                surplus_today = round(surplus, 2)
                if cap_kwh and soc_now is not None:
                    max_soc_eff = max_soc if max_soc is not None else 100.0
                    min_soc_eff = min_soc if min_soc is not None else 0.0
                    headroom_kwh = max(0.0, cap_kwh * max(0.0, (max_soc_eff - soc_now) / 100.0))
                    charge_kwh = min(max(0.0, surplus), headroom_kwh)
                    export_today = round(max(0.0, surplus - charge_kwh), 2)
                    end_soc = soc_now + (charge_kwh / cap_kwh * 100.0) if cap_kwh else None
                    if end_soc is not None:
                        end_soc = round(max(min_soc_eff, min(max_soc_eff, end_soc)), 1)
                else:
                    export_today = round(max(0.0, surplus), 2)

            hourly = []
            hourly_tomorrow = []
            hourly_safe = []
            charge_complete_h = None
            charge_complete_h_tom = None
            end_soc_sim = None
            target_reachable = None
            export_sim_kwh = 0.0
            import_sim_kwh = 0.0
            charge_sim_kwh = 0.0
            discharge_sim_kwh = 0.0
            export_sim_kwh_tom = 0.0
            import_sim_kwh_tom = 0.0
            charge_sim_kwh_tom = 0.0
            discharge_sim_kwh_tom = 0.0
            extra_now_w = None
            extra_safe_now_w = None
            extra_safe_today_kwh = None
            extra_safe_tomorrow_kwh = None
            target_soc = None
            target_reason = None
            intraday_forecast_kwh = None
            intraday_actual_kwh = None
            intraday_error_pct = None
            pv_expected_today_kwh = None
            pv_remaining_fc_kwh = None
            pv_remaining_hist_kwh = None
            required_charge_w = None
            schedule_info = _extra_safe_schedule_info(cfg, now_ts)
            schedule_pct = float(schedule_info.get("percent") or 0.0)
            if pv_id and load_id:
                pv_profile_fc = _hourly_from_forecast_entity(pv_fc_today_hourly_id, today_start) or _hourly_profile(conn, pv_id, 7)
                load_profile_fc = _hourly_profile(conn, load_id, 7)
                pv_profile_today = _hourly_profile_today(conn, pv_id, today_start, now_ts)
                load_profile_today = _hourly_profile_today(conn, load_id, today_start, now_ts)
                pv_profile_hist = _hourly_profile_median(conn, pv_id, 14)
                load_profile_hist = _hourly_profile_median(conn, load_id, 14)
                safe_profile_fc = None
                safe_profile_today = None
                if safe_entities:
                    safe_profile_fc = _hourly_profile_multi(conn, safe_entities, 7)
                    safe_profile_today = _hourly_profile_today_multi(conn, safe_entities, today_start, now_ts)
                    safe_profile_hist = _hourly_profile_median_multi(conn, safe_entities, 14)
                else:
                    safe_profile_hist = None
                pv_sum = sum(pv_profile_fc)
                load_sum = sum(load_profile_fc)
                pv_scale = 1.0
                load_scale = 1.0

                # Intraday alignment (actual vs forecast so far)
                try:
                    intraday_actual_kwh = _daily_energy_kwh(conn, pv_id, today_start, now_ts)
                    now_lt = _local_dt(now_ts, _get_runtime_tz_name())
                    h_now = now_lt.hour
                    frac = (now_lt.minute + (now_lt.second / 60.0)) / 60.0
                    forecast_wh = 0.0
                    for h in range(0, min(24, h_now)):
                        forecast_wh += pv_profile_fc[h]
                    if 0 <= h_now < 24:
                        forecast_wh += pv_profile_fc[h_now] * max(0.0, min(1.0, frac))
                    intraday_forecast_kwh = round(forecast_wh / 1000.0, 3)
                    if intraday_forecast_kwh and intraday_forecast_kwh > 0:
                        intraday_error_pct = round((intraday_actual_kwh - intraday_forecast_kwh) / intraday_forecast_kwh * 100.0, 1)
                        # Live pv_adjust based on intraday ratio (updated frequently)
                        live_ratio = intraday_actual_kwh / intraday_forecast_kwh
                        live_ratio = max(0.5, min(1.5, live_ratio))
                        if pv_factor_hist is not None:
                            pv_factor = max(0.6, min(1.4, (0.3 * pv_factor_hist) + (0.7 * live_ratio)))
                        else:
                            pv_factor = max(0.6, min(1.4, live_ratio))
                        meta = pv_adjust_meta.get(f"s{site}", {}) if isinstance(pv_adjust_meta.get(f"s{site}"), dict) else {}
                        last_ts = int(meta.get("last_ts") or 0)
                        if (now_ts - last_ts) >= PV_ADJUST_INTERVAL_S:
                            pv_adjust_meta[f"s{site}"] = {
                                **(meta or {}),
                                "pv_adjust": round(pv_factor, 3),
                                "intraday_forecast_kwh": intraday_forecast_kwh,
                                "intraday_actual_kwh": round(intraday_actual_kwh, 3),
                                "intraday_error_pct": intraday_error_pct,
                                "last_ts": now_ts,
                            }
                            pv_meta_dirty = True
                except Exception:
                    intraday_actual_kwh = None
                    intraday_forecast_kwh = None
                    intraday_error_pct = None

                # Today: real; Tomorrow: forecast corrected by pv_adjust
                pv_today_kwh = pv_today_real_kwh if pv_today_real_kwh is not None else ((pv_fc_today * pv_factor) if pv_fc_today is not None else pv_base)
                pv_tom_kwh = (pv_fc_tom * pv_factor) if pv_fc_tom is not None else pv_base
                load_today_kwh = load_today_real_kwh if load_today_real_kwh is not None else (load_fc_today if load_fc_today is not None else load_base)
                load_tom_kwh = load_today_kwh

                # Scale forecast profile to daily forecast (today), then merge in real hours.
                pv_scale_fc = 1.0
                if pv_fc_today is not None and pv_sum > 0:
                    pv_scale_fc = (pv_fc_today * pv_factor * 1000.0) / pv_sum
                elif pv_base is not None and pv_sum > 0:
                    pv_scale_fc = (pv_base * 1000.0) / pv_sum
                pv_profile_fc = [v * pv_scale_fc for v in pv_profile_fc]

                # Build expected remaining energy using history vs forecast (ML-ish blending)
                pv_remaining_fc_kwh = max(0.0, (pv_fc_today * pv_factor - (intraday_actual_kwh or 0.0))) if pv_fc_today is not None else None
                pv_remaining_hist_kwh = _remaining_kwh_from_profile(pv_profile_hist, now_ts)
                # Confidence: if intraday error is large, trust history more
                hist_weight = 0.5
                if intraday_error_pct is not None:
                    if abs(intraday_error_pct) >= 30:
                        hist_weight = 0.8
                    elif abs(intraday_error_pct) >= 15:
                        hist_weight = 0.65
                    else:
                        hist_weight = 0.5
                if pv_remaining_fc_kwh is None:
                    pv_expected_today_kwh = (intraday_actual_kwh or 0.0) + pv_remaining_hist_kwh
                else:
                    pv_expected_today_kwh = (intraday_actual_kwh or 0.0) + (hist_weight * pv_remaining_hist_kwh) + ((1 - hist_weight) * max(0.0, pv_remaining_fc_kwh))

                # Re-scale forecast profile to expected today energy (intelligent correction)
                if pv_expected_today_kwh is not None and pv_sum > 0:
                    pv_scale_fc = (pv_expected_today_kwh * 1000.0) / pv_sum
                    pv_profile_fc = [v * pv_scale_fc for v in pv_profile_fc]

                # Merge real hours for today (up to current hour) with scaled forecast for remaining hours.
                now_lt = _local_dt(now_ts, _get_runtime_tz_name())
                h_now = now_lt.hour
                pv_profile = []
                load_profile = []
                for h in range(24):
                    pv_h = pv_profile_fc[h]
                    if pv_profile_today[h] is not None and h <= h_now:
                        pv_h = pv_profile_today[h]
                    pv_profile.append(pv_h)
                    load_h = load_profile_fc[h]
                    if load_profile_today[h] is not None and h <= h_now:
                        load_h = load_profile_today[h]
                    if safe_entities and safe_profile_fc is not None:
                        safe_h = None
                        if safe_profile_today is not None and safe_profile_today[h] is not None and h <= h_now:
                            safe_h = safe_profile_today[h]
                        else:
                            safe_h = safe_profile_fc[h]
                        load_h = max(0.0, load_h - (safe_h or 0.0))
                    load_profile.append(load_h)

                pv_sum = sum(pv_profile)
                load_sum = sum(load_profile)
                pv_scale = 1.0
                # Only scale the load profile if the user explicitly provides a daily load target.
                if (load_daily_id and not load_daily_is_today) and load_today_kwh is not None and load_sum > 0:
                    load_scale = (load_today_kwh * 1000.0) / load_sum

                solar_start_hour = None
                solar_end_hour = None
                real_start, real_end = _solar_window_today_real(conn, pv_id, now_ts)
                if real_start is not None:
                    solar_start_hour = real_start
                if real_end is not None:
                    solar_end_hour = real_end
                if pv_profile:
                    if solar_start_hour is None:
                        for h in range(0, 24):
                            if (pv_profile[h] * pv_scale) >= SOLAR_END_W_THRESHOLD:
                                solar_start_hour = h
                                break
                    if solar_end_hour is None:
                        for h in range(23, -1, -1):
                            if (pv_profile[h] * pv_scale) >= SOLAR_END_W_THRESHOLD:
                                solar_end_hour = h
                                break

                # Estimate surplus and end SOC (using adjusted forecast)
                surplus_today = None
                export_today = None
                end_soc = None
                if pv_today_kwh is not None and load_today_kwh is not None:
                    surplus = pv_today_kwh - load_today_kwh
                    surplus_today = round(surplus, 2)
                    if cap_kwh and soc_now is not None:
                        max_soc_eff = max_soc if max_soc is not None else 100.0
                        min_soc_eff = min_soc if min_soc is not None else 0.0
                        headroom_kwh = max(0.0, cap_kwh * max(0.0, (max_soc_eff - soc_now) / 100.0))
                        charge_kwh = min(max(0.0, surplus), headroom_kwh)
                        export_today = round(max(0.0, surplus - charge_kwh), 2)
                        end_soc = soc_now + (charge_kwh / cap_kwh * 100.0) if cap_kwh else None
                        if end_soc is not None:
                            end_soc = round(max(min_soc_eff, min(max_soc_eff, end_soc)), 1)
                    else:
                        export_today = round(max(0.0, surplus), 2)

                tomorrow_start = today_start + 86400
                pv_profile_tom = _hourly_from_forecast_entity(pv_fc_tom_hourly_id, tomorrow_start) or _hourly_profile(conn, pv_id, 7)
                load_profile_tom = _hourly_profile(conn, load_id, 7)
                if safe_entities:
                    safe_profile_tom = _hourly_profile_multi(conn, safe_entities, 7)
                    load_profile_tom = [max(0.0, a - b) for a, b in zip(load_profile_tom, safe_profile_tom)]
                pv_sum_tom = sum(pv_profile_tom)
                load_sum_tom = sum(load_profile_tom)
                pv_scale_tom = 1.0
                load_scale_tom = 1.0
                if pv_tom_kwh is not None and pv_sum_tom > 0:
                    pv_scale_tom = (pv_tom_kwh * 1000.0) / pv_sum_tom
                # Only scale the load profile if the user explicitly provides a daily load target.
                if (load_daily_id and not load_daily_is_today) and load_tom_kwh is not None and load_sum_tom > 0:
                    load_scale_tom = (load_tom_kwh * 1000.0) / load_sum_tom

                solar_start_hour_tom = None
                solar_end_hour_tom = None
                if pv_profile_tom:
                    for h in range(0, 24):
                        if (pv_profile_tom[h] * pv_scale_tom) >= SOLAR_END_W_THRESHOLD:
                            solar_start_hour_tom = h
                            break
                    for h in range(23, -1, -1):
                        if (pv_profile_tom[h] * pv_scale_tom) >= SOLAR_END_W_THRESHOLD:
                            solar_end_hour_tom = h
                            break

                max_soc_eff = max_soc if max_soc is not None else 100.0
                min_soc_eff = min_soc if min_soc is not None else 0.0

                # Target SOC: fixed to max (100%) with a safety margin
                if cap_kwh and soc_now is not None:
                    target_soc = max_soc_eff if max_soc is not None else 100.0
                    target_soc = max(min_soc_eff, min(max_soc_eff, round(target_soc, 1)))
                    target_reason = "fixed_target_100"

                soc_sim = soc_now if (cap_kwh and soc_now is not None) else None
                max_charge_eff = float(max_charge_w) if max_charge_w is not None else 1e9
                max_discharge_eff = float(max_discharge_w) if max_discharge_w is not None else 1e9
                for h in range(24):
                    pv_w = pv_profile[h] * pv_scale
                    load_w = load_profile[h] * load_scale
                    surplus_w = pv_w - load_w
                    batt_charge_w = 0.0
                    batt_discharge_w = 0.0
                    grid_export_w = 0.0
                    grid_import_w = 0.0
                    if soc_sim is not None and cap_kwh:
                        headroom_kwh = cap_kwh * max(0.0, (max_soc_eff - soc_sim) / 100.0)
                        avail_kwh = cap_kwh * max(0.0, (soc_sim - min_soc_eff) / 100.0)
                        if surplus_w >= 0:
                            batt_charge_w = min(surplus_w, max_charge_eff, headroom_kwh * 1000.0)
                            grid_export_w = max(0.0, surplus_w - batt_charge_w)
                            soc_sim += (batt_charge_w / 1000.0) / cap_kwh * 100.0
                            soc_sim = max(min_soc_eff, min(max_soc_eff, soc_sim))
                            in_solar_window = True
                            if solar_start_hour is not None and solar_end_hour is not None:
                                in_solar_window = solar_start_hour <= h <= solar_end_hour
                            if charge_complete_h is None and in_solar_window and soc_sim >= max_soc_eff - 0.01:
                                charge_complete_h = h
                        else:
                            deficit_w = -surplus_w
                            batt_discharge_w = min(deficit_w, max_discharge_eff, avail_kwh * 1000.0)
                            grid_import_w = max(0.0, deficit_w - batt_discharge_w)
                            soc_sim -= (batt_discharge_w / 1000.0) / cap_kwh * 100.0
                            soc_sim = max(min_soc_eff, min(max_soc_eff, soc_sim))
                    else:
                        if surplus_w >= 0:
                            grid_export_w = surplus_w
                        else:
                            grid_import_w = -surplus_w
                    export_sim_kwh += grid_export_w / 1000.0
                    import_sim_kwh += grid_import_w / 1000.0
                    charge_sim_kwh += batt_charge_w / 1000.0
                    discharge_sim_kwh += batt_discharge_w / 1000.0
                    extra_w = grid_export_w
                    hourly.append({
                        "h": h,
                        "pv_w": round(pv_w, 1),
                        "load_w": round(load_w, 1),
                        "surplus_w": round(max(0.0, surplus_w), 1),
                        "soc": round(soc_sim, 1) if soc_sim is not None else None,
                        "batt_charge_w": round(batt_charge_w, 1),
                        "batt_discharge_w": round(batt_discharge_w, 1),
                        "grid_export_w": round(grid_export_w, 1),
                        "grid_import_w": round(grid_import_w, 1),
                        "extra_w": round(extra_w, 1),
                    })
                    if hourly:
                        hour_now = _local_dt(now_ts, _get_runtime_tz_name()).hour
                        if 0 <= hour_now < len(hourly):
                            extra_now_w = hourly[hour_now].get("extra_w")
                # Real-time extra from current states (more reliable for "now")
                pv_now = _state_num(pv_id) or 0.0
                load_now = _state_num(load_id) or 0.0
                surplus_now = max(0.0, pv_now - load_now)
                extra_now_w = min(extra_now_w, surplus_now) if extra_now_w is not None else surplus_now
                if solar_start_hour is not None and charge_complete_h is not None and charge_complete_h < solar_start_hour:
                    charge_complete_h = solar_start_hour
                end_soc_solar = None
                if solar_end_hour is not None:
                    # solar_end_hour can be fractional (minute precision). Clamp to a valid list index.
                    idx = int(round(solar_end_hour))
                    idx = max(0, min(len(hourly) - 1, idx))
                    end_soc_solar = hourly[idx].get("soc")
                end_soc_sim = end_soc_solar if end_soc_solar is not None else soc_sim

            if pv_id and load_id:
                soc_sim_tom = end_soc_sim if (cap_kwh and end_soc_sim is not None) else (soc_now if (cap_kwh and soc_now is not None) else None)
                max_soc_eff = max_soc if max_soc is not None else 100.0
                min_soc_eff = min_soc if min_soc is not None else 0.0
                max_charge_eff = float(max_charge_w) if max_charge_w is not None else 1e9
                max_discharge_eff = float(max_discharge_w) if max_discharge_w is not None else 1e9
                for h in range(24):
                    pv_w = pv_profile_tom[h] * pv_scale_tom
                    load_w = load_profile_tom[h] * load_scale_tom
                    surplus_w = pv_w - load_w
                    batt_charge_w = 0.0
                    batt_discharge_w = 0.0
                    grid_export_w = 0.0
                    grid_import_w = 0.0
                    if soc_sim_tom is not None and cap_kwh:
                        headroom_kwh = cap_kwh * max(0.0, (max_soc_eff - soc_sim_tom) / 100.0)
                        avail_kwh = cap_kwh * max(0.0, (soc_sim_tom - min_soc_eff) / 100.0)
                        if surplus_w >= 0:
                            batt_charge_w = min(surplus_w, max_charge_eff, headroom_kwh * 1000.0)
                            grid_export_w = max(0.0, surplus_w - batt_charge_w)
                            soc_sim_tom += (batt_charge_w / 1000.0) / cap_kwh * 100.0
                            soc_sim_tom = max(min_soc_eff, min(max_soc_eff, soc_sim_tom))
                            in_solar_window_tom = True
                            if solar_start_hour_tom is not None and solar_end_hour_tom is not None:
                                in_solar_window_tom = solar_start_hour_tom <= h <= solar_end_hour_tom
                            if charge_complete_h_tom is None and in_solar_window_tom and soc_sim_tom >= max_soc_eff - 0.01:
                                charge_complete_h_tom = h
                        else:
                            deficit_w = -surplus_w
                            batt_discharge_w = min(deficit_w, max_discharge_eff, avail_kwh * 1000.0)
                            grid_import_w = max(0.0, deficit_w - batt_discharge_w)
                            soc_sim_tom -= (batt_discharge_w / 1000.0) / cap_kwh * 100.0
                            soc_sim_tom = max(min_soc_eff, min(max_soc_eff, soc_sim_tom))
                    else:
                        if surplus_w >= 0:
                            grid_export_w = surplus_w
                        else:
                            grid_import_w = -surplus_w
                    export_sim_kwh_tom += grid_export_w / 1000.0
                    import_sim_kwh_tom += grid_import_w / 1000.0
                    charge_sim_kwh_tom += batt_charge_w / 1000.0
                    discharge_sim_kwh_tom += batt_discharge_w / 1000.0
                if solar_start_hour_tom is not None and charge_complete_h_tom is not None and charge_complete_h_tom < solar_start_hour_tom:
                    charge_complete_h_tom = solar_start_hour_tom
                    extra_w = grid_export_w
                    hourly_tomorrow.append({
                        "h": h,
                        "pv_w": round(pv_w, 1),
                        "load_w": round(load_w, 1),
                        "surplus_w": round(max(0.0, surplus_w), 1),
                        "soc": round(soc_sim_tom, 1) if soc_sim_tom is not None else None,
                        "batt_charge_w": round(batt_charge_w, 1),
                        "batt_discharge_w": round(batt_discharge_w, 1),
                        "grid_export_w": round(grid_export_w, 1),
                        "grid_import_w": round(grid_import_w, 1),
                        "extra_w": round(extra_w, 1),
                    })

            # Safe extra simulation: surplus usable while still reaching target SOC
            if pv_id and load_id and target_soc is not None and cap_kwh and soc_now is not None:
                soc_safe = soc_now
                max_soc_safe = min(target_soc - SAFE_SOC_MARGIN_PCT, max_soc if max_soc is not None else 100.0)
                if max_soc_safe < (min_soc if min_soc is not None else 0.0):
                    max_soc_safe = min(target_soc, max_soc if max_soc is not None else 100.0)
                min_soc_eff = min_soc if min_soc is not None else 0.0
                max_charge_eff = float(max_charge_w) if max_charge_w is not None else 1e9
                max_discharge_eff = float(max_discharge_w) if max_discharge_w is not None else 1e9
                extra_safe_today_kwh = 0.0
                for h in range(24):
                    pv_w = pv_profile[h] * pv_scale
                    load_w = load_profile[h] * load_scale
                    surplus_w = pv_w - load_w
                    batt_charge_w = 0.0
                    batt_discharge_w = 0.0
                    grid_export_w = 0.0
                    grid_import_w = 0.0
                    if cap_kwh:
                        headroom_kwh = cap_kwh * max(0.0, (max_soc_safe - soc_safe) / 100.0)
                        avail_kwh = cap_kwh * max(0.0, (soc_safe - min_soc_eff) / 100.0)
                        if surplus_w >= 0:
                            batt_charge_w = min(surplus_w, max_charge_eff, headroom_kwh * 1000.0)
                            grid_export_w = max(0.0, surplus_w - batt_charge_w)
                            soc_safe += (batt_charge_w / 1000.0) / cap_kwh * 100.0
                            soc_safe = max(min_soc_eff, min(max_soc_safe, soc_safe))
                        else:
                            deficit_w = -surplus_w
                            batt_discharge_w = min(deficit_w, max_discharge_eff, avail_kwh * 1000.0)
                            grid_import_w = max(0.0, deficit_w - batt_discharge_w)
                            soc_safe -= (batt_discharge_w / 1000.0) / cap_kwh * 100.0
                            soc_safe = max(min_soc_eff, min(max_soc_safe, soc_safe))
                    else:
                        if surplus_w >= 0:
                            grid_export_w = surplus_w
                        else:
                            grid_import_w = -surplus_w
                    extra_safe_today_kwh += grid_export_w / 1000.0
                    hourly_safe.append({
                        "h": h,
                        "extra_safe_w": round(grid_export_w, 1),
                        "soc_target": round(soc_safe, 1) if soc_safe is not None else None,
                    })
                    if hourly_safe:
                        hour_now = time.localtime(now_ts).tm_hour
                        if 0 <= hour_now < len(hourly_safe):
                            extra_safe_now_w = hourly_safe[hour_now].get("extra_safe_w")
                # Blend real-time with forecast: mostly real, small forecast influence
                pv_now = _state_num(pv_id) or 0.0
                load_now = _state_num(load_id) or 0.0
                surplus_now = max(0.0, pv_now - load_now)
                if extra_safe_now_w is None:
                    extra_safe_now_w = surplus_now
                else:
                    extra_safe_now_w = (0.95 * surplus_now) + (0.05 * extra_safe_now_w)

                # Ensure enough power goes to battery to reach target by solar end
                required_charge_w = None
                if (
                    solar_end_hour is not None
                    and target_soc is not None
                    and soc_now is not None
                    and cap_kwh
                ):
                    now_lt = _local_dt(now_ts, _get_runtime_tz_name())
                    hour_now = now_lt.hour
                    frac = (now_lt.minute + (now_lt.second / 60.0)) / 60.0
                    hours_left = (solar_end_hour + 1) - (hour_now + frac)
                    if hours_left > 0:
                        remaining_kwh = cap_kwh * max(0.0, (target_soc - soc_now) / 100.0)
                        required_charge_w = (remaining_kwh * 1000.0) / hours_left
                        # Respect BMS max charge limit
                        if max_charge_eff is not None:
                            required_charge_w = min(required_charge_w, max_charge_eff)
                        extra_safe_now_w = max(0.0, min(extra_safe_now_w, surplus_now - required_charge_w))
                if extra_safe_now_w is not None and schedule_pct:
                    extra_safe_now_w = max(0.0, extra_safe_now_w * (1.0 + (schedule_pct / 100.0)))

                target_reachable = None
                if end_soc_sim is not None and target_soc is not None:
                    target_reachable = end_soc_sim >= (target_soc - 0.1)
                    # Allow extra if battery is already near target and charging with real surplus
                    override_reachable = False
                    if not target_reachable:
                        batt_now = _state_num(batt_id) if batt_id else None
                        if (
                            soc_now is not None
                            and target_soc is not None
                            and batt_now is not None
                            and soc_now >= (target_soc - 1.0)
                            and batt_now < 0
                            and surplus_now > 0
                        ):
                            override_reachable = True
                    if target_reachable or override_reachable:
                        target_reachable = True
                    else:
                        extra_safe_now_w = 0.0

                # Safe extra simulation for tomorrow (kWh)
                extra_safe_tomorrow_kwh = 0.0
                soc_safe_tom = end_soc_sim if end_soc_sim is not None else soc_now
                for h in range(24):
                    pv_w = pv_profile_tom[h] * pv_scale_tom
                    load_w = load_profile_tom[h] * load_scale_tom
                    surplus_w = pv_w - load_w
                    batt_charge_w = 0.0
                    batt_discharge_w = 0.0
                    grid_export_w = 0.0
                    grid_import_w = 0.0
                    if soc_safe_tom is not None and cap_kwh:
                        headroom_kwh = cap_kwh * max(0.0, (max_soc_safe - soc_safe_tom) / 100.0)
                        avail_kwh = cap_kwh * max(0.0, (soc_safe_tom - min_soc_eff) / 100.0)
                        if surplus_w >= 0:
                            batt_charge_w = min(surplus_w, max_charge_eff, headroom_kwh * 1000.0)
                            grid_export_w = max(0.0, surplus_w - batt_charge_w)
                            soc_safe_tom += (batt_charge_w / 1000.0) / cap_kwh * 100.0
                            soc_safe_tom = max(min_soc_eff, min(max_soc_safe, soc_safe_tom))
                        else:
                            deficit_w = -surplus_w
                            batt_discharge_w = min(deficit_w, max_discharge_eff, avail_kwh * 1000.0)
                            grid_import_w = max(0.0, deficit_w - batt_discharge_w)
                            soc_safe_tom -= (batt_discharge_w / 1000.0) / cap_kwh * 100.0
                            soc_safe_tom = max(min_soc_eff, min(max_soc_safe, soc_safe_tom))
                    else:
                        if surplus_w >= 0:
                            grid_export_w = surplus_w
                        else:
                            grid_import_w = -surplus_w
                    extra_safe_tomorrow_kwh += grid_export_w / 1000.0

            meta = pv_adjust_meta.get(f"s{site}", {}) if isinstance(pv_adjust_meta.get(f"s{site}"), dict) else {}
            forecast_last_kwh = meta.get("forecast")
            actual_last_kwh = meta.get("actual")
            error_pct = meta.get("error_pct")
            if forecast_last_kwh is None or actual_last_kwh is None:
                forecast_last_kwh = forecast_last_kwh if forecast_last_kwh is not None else fallback_fc_kwh
                actual_last_kwh = actual_last_kwh if actual_last_kwh is not None else fallback_act_kwh
                error_pct = error_pct if error_pct is not None else fallback_err_pct

            # Self-checks / anomaly detection
            warnings = []
            quality = 100
            now_local = _local_dt(now_ts, _get_runtime_tz_name())
            now_hour = now_local.hour + (now_local.minute / 60.0)
            pv_live = _state_num(pv_id) if pv_id else None
            if pv_live is not None and pv_live >= SOLAR_REAL_MIN_W and solar_end_hour is not None:
                if solar_end_hour < (now_hour - 0.2):
                    warnings.append("Fine produzione reale antecedente all'ora attuale con PV live > soglia.")
                    quality -= 25
            if intraday_error_pct is not None and abs(intraday_error_pct) >= 30:
                warnings.append("Forecast PV oggi molto distante dal reale (errore > 30%).")
                quality -= 15
            if pv_expected_today_kwh is not None and intraday_actual_kwh is not None:
                if pv_expected_today_kwh < intraday_actual_kwh - 0.1:
                    warnings.append("PV atteso oggi < PV già prodotto (incoerenza di forecast/consumi).")
                    quality -= 20
            if load_today_kwh is not None and load_today_kwh < 0:
                warnings.append("Consumo oggi negativo: dati sensori incoerenti.")
                quality -= 20
            quality = max(0, min(100, quality))

            # Auto-fix: if quality is low, tighten extra-safe automatically
            if extra_safe_now_w is not None:
                if quality < 70:
                    extra_safe_now_w = 0.0
                elif quality < 85:
                    extra_safe_now_w = max(0.0, extra_safe_now_w * 0.5)

            # Auto-fix: if quality is low, avoid optimistic early "fine carica"
            if charge_complete_h is not None:
                if quality < 70 and target_reachable is False:
                    charge_complete_h = None
                elif charge_complete_h < (now_hour - 0.1):
                    # If we are not yet near target, don't report a past completion time
                    if soc_now is not None and target_soc is not None and soc_now < (target_soc - 1.0):
                        charge_complete_h = None
                    else:
                        charge_complete_h = max(charge_complete_h, now_hour)

            results.append({
                "site": site,
                "name": (cfg.get("devices", {}).get(f"s{site}", {}) or {}).get("name", "") or f"Utenza {site}",
                "pv_today_kwh": round(pv_today_kwh, 2) if pv_today_kwh is not None else None,
                "pv_tomorrow_kwh": round(pv_tom_kwh, 2) if pv_tom_kwh is not None else None,
                "pv_expected_today_kwh": round(pv_expected_today_kwh, 2) if pv_expected_today_kwh is not None else None,
                "pv_remaining_fc_kwh": round(pv_remaining_fc_kwh, 2) if pv_remaining_fc_kwh is not None else None,
                "pv_remaining_hist_kwh": round(pv_remaining_hist_kwh, 2) if pv_remaining_hist_kwh is not None else None,
                "load_today_kwh": round(load_today_kwh, 2) if load_today_kwh is not None else None,
                "load_tomorrow_kwh": round(load_tom_kwh, 2) if load_tom_kwh is not None else None,
                "extra_safe_load_today_kwh": round(safe_today_kwh, 2) if safe_today_kwh is not None else None,
                "extra_safe_load_now_w": safe_now_w,
                "surplus_today_kwh": surplus_today,
                "export_today_kwh": export_today,
                "end_soc": round(end_soc_sim, 1) if end_soc_sim is not None else end_soc,
                "end_soc_solar": round(end_soc_solar, 1) if end_soc_solar is not None else None,
                "solar_start_hour": round(solar_start_hour, 2) if solar_start_hour is not None else None,
                "solar_end_hour": round(solar_end_hour, 2) if solar_end_hour is not None else None,
                "solar_start_hour_tom": solar_start_hour_tom,
                "solar_end_hour_tom": solar_end_hour_tom,
                "charge_complete_hour": charge_complete_h,
                "charge_complete_hour_tomorrow": charge_complete_h_tom,
                "extra_now_w": extra_now_w,
                "extra_safe_now_w": extra_safe_now_w,
                "extra_safe_schedule_pct": schedule_pct,
                "extra_safe_schedule": schedule_info,
                "export_sim_today_kwh": round(export_sim_kwh, 2),
                "import_sim_today_kwh": round(import_sim_kwh, 2),
                "charge_sim_today_kwh": round(charge_sim_kwh, 2),
                "discharge_sim_today_kwh": round(discharge_sim_kwh, 2),
                "extra_safe_today_kwh": round(extra_safe_today_kwh, 2) if extra_safe_today_kwh is not None else None,
                "extra_safe_tomorrow_kwh": round(extra_safe_tomorrow_kwh, 2) if extra_safe_tomorrow_kwh is not None else None,
                "export_sim_tomorrow_kwh": round(export_sim_kwh_tom, 2),
                "import_sim_tomorrow_kwh": round(import_sim_kwh_tom, 2),
                "charge_sim_tomorrow_kwh": round(charge_sim_kwh_tom, 2),
                "discharge_sim_tomorrow_kwh": round(discharge_sim_kwh_tom, 2),
                "required_charge_w": round(required_charge_w, 1) if required_charge_w is not None else None,
                "capacity_kwh": cap_kwh,
                "max_charge_w": max_charge_w,
                "max_discharge_w": max_discharge_w,
                "max_charge_w_cfg": max_charge_w_cfg,
                "max_discharge_w_cfg": max_discharge_w_cfg,
                "max_charge_w_learned": learned_max_charge,
                "max_discharge_w_learned": learned_max_discharge,
                "min_soc": min_soc,
                "max_soc": max_soc,
                "export_limit_w": export_limit,
                "target_soc": target_soc,
                "target_reason": target_reason,
                "target_reachable": target_reachable,
                "target_gap_pct": round(max(0.0, (target_soc or 0) - (end_soc_sim or 0)), 1) if (target_soc is not None and end_soc_sim is not None) else None,
                "factors": {
                    "pv_adjust": round(pv_factor, 3),
                    "forecast_last_kwh": forecast_last_kwh,
                    "actual_last_kwh": actual_last_kwh,
                    "error_pct": error_pct,
                    "intraday_forecast_kwh": intraday_forecast_kwh,
                    "intraday_actual_kwh": intraday_actual_kwh,
                    "intraday_error_pct": intraday_error_pct,
                },
                "hourly": hourly,
                "hourly_tomorrow": hourly_tomorrow,
                "hourly_safe": hourly_safe,
                "warnings": warnings,
                "quality": quality,
                "sources": {
                    "pv_forecast_today": pv_fc_today_id or None,
                    "pv_forecast_tomorrow": pv_fc_tom_id or None,
                    "pv_forecast_today_hourly": pv_fc_today_hourly_id or None,
                    "pv_forecast_tomorrow_hourly": pv_fc_tom_hourly_id or None,
                    "load_daily": load_daily_id or None,
                },
                "auto": {
                    "pv_base_kwh": pv_base,
                    "load_base_kwh": load_base,
                },
            })

    if pv_meta_dirty:
        save_config(cfg)
    return JSONResponse({
        "updated_at": now_ts,
        "sites": results,
    })


@app.get("/api/reports")
async def list_reports():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(REPORT_DIR.glob("report_e-energymind_*.md")):
        items.append(p.name)
    return JSONResponse({"items": items, "dir": str(REPORT_DIR)})


@app.get("/api/config")
async def get_config():
    return JSONResponse(load_config())


@app.post("/api/config")
async def set_config(payload: Dict[str, Any]):
    cfg = load_config()
    cfg = apply_config(cfg, payload)
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE config")
    _mqtt_publish_discovery(cfg)
    return JSONResponse({"ok": True})


@app.get("/api/entities")
async def get_entities():
    cfg = load_config()
    ent_cfg = cfg.get("entities", {})
    out: Dict[str, Any] = {}
    for key, eid in (ent_cfg or {}).items():
        out[key] = _entity_payload(eid)
    return JSONResponse(out)


@app.post("/api/entity_states")
async def entity_states(payload: Dict[str, Any]):
    entity_ids = payload.get("entity_ids", []) if isinstance(payload, dict) else []
    if not isinstance(entity_ids, list):
        raise HTTPException(status_code=400, detail="Invalid entity_ids")
    out = {}
    for eid in entity_ids:
        if not isinstance(eid, str):
            continue
        eid = eid.strip()
        if not eid:
            continue
        out[eid] = _entity_payload(eid)
    return JSONResponse({"items": out})


@app.get("/api/entities_all")
async def get_entities_all(site: int = 1):
    if site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    store = _load_all_entities_store()
    all_list = store.get(f"s{site}", []) or []
    if not all_list:
        cfg = load_config()
        all_list = (cfg.get("all_entities", {}) or {}).get(f"s{site}", []) or []
    items = []
    for item in all_list:
        eid = item.get("entity_id")
        payload = _entity_payload(eid)
        items.append({
            "entity_id": eid,
            "name": item.get("name"),
            "original_name": item.get("original_name"),
            "platform": item.get("platform"),
            "disabled_by": item.get("disabled_by"),
            "state": payload.get("state"),
            "attributes": payload.get("attributes"),
            "icon": payload.get("icon"),
        })
    return JSONResponse({"site": site, "items": items})


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


@app.post("/api/all_entities_sync")
async def all_entities_sync(payload: Dict[str, Any]):
    site = int(payload.get("site") or 0)
    if site not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Invalid site")
    device_id = str(payload.get("device_id") or "").strip()
    device_name = str(payload.get("device_name") or "").strip()
    if not device_id and not device_name:
        raise HTTPException(status_code=400, detail="Missing device_id")
    device, dev_entities = await _get_device_entities(device_id or None, device_name or None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    cfg = load_config()
    cfg.setdefault("all_entities", {})
    full_list = []
    for e in dev_entities:
        full_list.append({
            "entity_id": e.get("entity_id"),
            "name": e.get("name"),
            "original_name": e.get("original_name"),
            "platform": e.get("platform"),
            "disabled_by": e.get("disabled_by"),
        })
    cfg["all_entities"][f"s{site}"] = full_list
    save_config(cfg)
    store = _load_all_entities_store()
    store[f"s{site}"] = full_list
    _save_all_entities_store(store)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} ALL_ENTITIES site={site} total={len(full_list)}")
    return JSONResponse({"ok": True, "total": len(full_list), "device": device.get("name") or device.get("name_by_user") or device.get("id")})


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
    # Store full device entities list (unfiltered) for reference in Admin
    cfg.setdefault("all_entities", {})
    full_list = []
    for e in dev_entities:
        full_list.append({
            "entity_id": e.get("entity_id"),
            "name": e.get("name"),
            "original_name": e.get("original_name"),
            "platform": e.get("platform"),
            "disabled_by": e.get("disabled_by"),
        })
    cfg["all_entities"][f"s{site}"] = full_list
    store = _load_all_entities_store()
    store[f"s{site}"] = full_list
    _save_all_entities_store(store)
    save_config(cfg)
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} AUTO_MAP site={site} mapped={count}")
    return JSONResponse({
        "ok": True,
        "mapped": count,
        "matched": len(mapped),
        "skipped_existing": skipped_existing,
        "total_entities": len(dev_entities),
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
async def device_entities(device_id: str = "", device_name: str = "", debug: int = 0):
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
    resp = {
        "device_id": target_id or device_id,
        "device_name": device_name,
        "count": len(items),
        "items": items,
    }
    if debug:
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
        resp["devices"] = device_list
        resp["entity_device_ids_sample"] = sample_ids
    return JSONResponse(resp)


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
