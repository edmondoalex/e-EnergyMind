import json
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path("/data")
CONF_PATH = DATA_DIR / "energymind_config.json"

ENERGY_ENTITY_KEYS = [
    "pv_power", "pv_power_aux", "pv_power_total",
    "load_power", "grid_power", "grid_import_power", "grid_export_power",
    "battery_power", "battery_voltage", "battery_current", "battery_soc", "battery_soh", "battery_temp",
    "storage_control_mode",
    "timed_charge_start", "timed_charge_end", "timed_charge_power",
    "timed_discharge_start", "timed_discharge_end", "timed_discharge_power",
    "today_production_kwh", "today_load_kwh", "today_import_kwh", "today_export_kwh",
    "forecast_today_kwh", "forecast_tomorrow_kwh",
    "inverter_status", "device_fault", "grid_frequency",
    "ambient_temp_1", "ambient_temp_2",
    "module_temp_1", "module_temp_2", "module_temp_3",
    "radiator_temp_1", "radiator_temp_2", "radiator_temp_3", "radiator_temp_4", "radiator_temp_5", "radiator_temp_6",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "entities": {
        **{f"s{site}_{key}": None for site in (1, 2, 3) for key in ENERGY_ENTITY_KEYS}
    },
    "runtime": {
        "mode": "dry-run",
        "ui_poll_ms": 3000,
        "sites_count": 2,
        "grid_export_positive": True,
        "timezone": "Europe/Rome",
        "learned_rules": {},
        "ui_flags": {},
        "ui_history_flags": {},
    },
    "automation": {
        "flow_entities": {
            "s1": {"pv_a": "", "pv_b": "", "pv_total": "", "pv": "", "load_total": "", "load": "", "battery": "", "grid": "", "soc": "", "soc_min": "", "battery_v": "", "battery_a": "", "today_prod": "", "today_load": "", "today_house": "", "today_export": "", "today_charge": "", "today_discharge": "", "voltage": "", "frequency": ""},
            "s2": {"pv_a": "", "pv_b": "", "pv_total": "", "pv": "", "load_total": "", "load": "", "battery": "", "grid": "", "soc": "", "soc_min": "", "battery_v": "", "battery_a": "", "today_prod": "", "today_load": "", "today_house": "", "today_export": "", "today_charge": "", "today_discharge": "", "voltage": "", "frequency": ""},
            "s3": {"pv_a": "", "pv_b": "", "pv_total": "", "pv": "", "load_total": "", "load": "", "battery": "", "grid": "", "soc": "", "soc_min": "", "battery_v": "", "battery_a": "", "today_prod": "", "today_load": "", "today_house": "", "today_export": "", "today_charge": "", "today_discharge": "", "voltage": "", "frequency": ""},
        },
        "extra_datalog_entities": [],
        "extra_safe_entities": [],
        "extra_safe_export_factor": 0.97,
        "extra_safe_schedule": {
            "enabled": True,
            "days": {
                "mon": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "tue": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "wed": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "thu": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "fri": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "sat": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
                "sun": [{"start": "06:00", "end": "10:00", "percent": -30}, {"start": "10:00", "end": "14:00", "percent": -10}, {"start": "14:00", "end": "18:00", "percent": 0}],
            },
        },
    },
    "forecast": {
        "s1": {
            "pv_forecast_today": "",
            "pv_forecast_tomorrow": "",
            "pv_forecast_today_hourly": "",
            "pv_forecast_tomorrow_hourly": "",
            "load_daily": "",
            "battery_capacity_kwh": None,
            "max_charge_w": None,
            "max_discharge_w": None,
            "min_soc": None,
            "max_soc": None,
            "export_limit_w": None,
        },
        "s2": {
            "pv_forecast_today": "",
            "pv_forecast_tomorrow": "",
            "pv_forecast_today_hourly": "",
            "pv_forecast_tomorrow_hourly": "",
            "load_daily": "",
            "battery_capacity_kwh": None,
            "max_charge_w": None,
            "max_discharge_w": None,
            "min_soc": None,
            "max_soc": None,
            "export_limit_w": None,
        },
        "s3": {
            "pv_forecast_today": "",
            "pv_forecast_tomorrow": "",
            "pv_forecast_today_hourly": "",
            "pv_forecast_tomorrow_hourly": "",
            "load_daily": "",
            "battery_capacity_kwh": None,
            "max_charge_w": None,
            "max_discharge_w": None,
            "min_soc": None,
            "max_soc": None,
            "export_limit_w": None,
        },
    },
    "devices": {
        "s1": {"name": "", "id": ""},
        "s2": {"name": "", "id": ""},
        "s3": {"name": "", "id": ""},
    },
    "view_card": {
        "count": 3,
        "ha_base_url": "/ha",
        "cards": [
            {"title": "Card 1", "path": ""},
            {"title": "Card 2", "path": ""},
            {"title": "Card 3", "path": ""},
        ],
    },
    "all_entities": {
        "s1": [],
        "s2": [],
        "s3": [],
    },
    "security": {
        "user_pin": "",
    },
}


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def normalize_config(raw: Dict[str, Any]) -> Dict[str, Any]:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if not isinstance(raw, dict):
        return cfg

    ent = raw.get("entities", {})
    if isinstance(ent, dict):
        for key in cfg["entities"].keys():
            val = ent.get(key)
            if val is None:
                cfg["entities"][key] = None
            elif isinstance(val, str):
                cfg["entities"][key] = val.strip() or None

    runtime = raw.get("runtime", {})
    if isinstance(runtime, dict):
        if isinstance(runtime.get("mode"), str):
            cfg["runtime"]["mode"] = runtime["mode"]
        if "ui_poll_ms" in runtime:
            cfg["runtime"]["ui_poll_ms"] = int(_float(runtime["ui_poll_ms"], cfg["runtime"]["ui_poll_ms"]))
        if "sites_count" in runtime:
            n = int(_float(runtime["sites_count"], cfg["runtime"]["sites_count"]))
            cfg["runtime"]["sites_count"] = max(1, min(3, n))
        if "grid_export_positive" in runtime:
            cfg["runtime"]["grid_export_positive"] = bool(runtime.get("grid_export_positive"))
        if isinstance(runtime.get("timezone"), str):
            cfg["runtime"]["timezone"] = runtime.get("timezone") or cfg["runtime"]["timezone"]
        if isinstance(runtime.get("learned_rules"), dict):
            cfg["runtime"]["learned_rules"] = runtime.get("learned_rules", {})
        if isinstance(runtime.get("ui_flags"), dict):
            cfg["runtime"]["ui_flags"] = runtime.get("ui_flags", {})
        if isinstance(runtime.get("ui_history_flags"), dict):
            cfg["runtime"]["ui_history_flags"] = runtime.get("ui_history_flags", {})

    devices = raw.get("devices", {})
    if isinstance(devices, dict):
        for key in ("s1", "s2", "s3"):
            src = devices.get(key, {}) if isinstance(devices.get(key, {}), dict) else {}
            cfg["devices"][key]["name"] = str(src.get("name") or "").strip()
            cfg["devices"][key]["id"] = str(src.get("id") or "").strip()

    all_entities = raw.get("all_entities", {})
    if isinstance(all_entities, dict):
        for key in ("s1", "s2", "s3"):
            items = all_entities.get(key, [])
            if isinstance(items, list):
                cfg["all_entities"][key] = items

    security = raw.get("security", {})
    if isinstance(security, dict) and isinstance(security.get("user_pin"), str):
        cfg["security"]["user_pin"] = security.get("user_pin", "")

    automation = raw.get("automation", {})
    if isinstance(automation, dict):
        raw_extra = automation.get("extra_datalog_entities", [])
        extra_list = []
        if isinstance(raw_extra, list):
            for item in raw_extra:
                if not isinstance(item, dict):
                    continue
                try:
                    site = int(item.get("site") or 0)
                except Exception:
                    site = 0
                entity_id = str(item.get("entity_id") or "").strip()
                if site in (1, 2, 3) and entity_id:
                    enabled = bool(item.get("enabled", True))
                    extra_list.append({"site": site, "entity_id": entity_id, "enabled": enabled})
        cfg["automation"]["extra_datalog_entities"] = extra_list

        raw_safe = automation.get("extra_safe_entities", [])
        safe_list = []
        if isinstance(raw_safe, list):
            for item in raw_safe:
                if not isinstance(item, dict):
                    continue
                try:
                    site = int(item.get("site") or 0)
                except Exception:
                    site = 0
                entity_id = str(item.get("entity_id") or "").strip()
                if site in (1, 2, 3) and entity_id:
                    enabled = bool(item.get("enabled", True))
                    safe_list.append({"site": site, "entity_id": entity_id, "enabled": enabled})
        cfg["automation"]["extra_safe_entities"] = safe_list

        if "extra_safe_export_factor" in automation:
            try:
                v = float(automation.get("extra_safe_export_factor"))
            except Exception:
                v = cfg["automation"]["extra_safe_export_factor"]
            cfg["automation"]["extra_safe_export_factor"] = max(0.0, min(1.0, v))

        if "extra_safe_schedule" in automation:
            sched = automation.get("extra_safe_schedule", {})
        else:
            sched = None
        if isinstance(sched, dict):
            enabled = bool(sched.get("enabled", False))
            days = sched.get("days", {})
            safe_days = {k: [] for k in ("mon","tue","wed","thu","fri","sat","sun")}
            if isinstance(days, dict):
                for k in safe_days.keys():
                    items = days.get(k, [])
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        start = str(item.get("start") or "").strip()
                        end = str(item.get("end") or "").strip()
                        try:
                            pct = float(item.get("percent") or 0)
                        except Exception:
                            pct = 0.0
                        if start and end:
                            safe_days[k].append({"start": start, "end": end, "percent": pct})
            cfg["automation"]["extra_safe_schedule"] = {"enabled": enabled, "days": safe_days}

    forecast = raw.get("forecast", {})
    if isinstance(forecast, dict):
        for key in ("s1", "s2", "s3"):
            src = forecast.get(key, {}) if isinstance(forecast.get(key, {}), dict) else {}
            for fkey in cfg["forecast"][key].keys():
                val = src.get(fkey, cfg["forecast"][key][fkey])
                if fkey in ("pv_forecast_today", "pv_forecast_tomorrow", "pv_forecast_today_hourly", "pv_forecast_tomorrow_hourly", "load_daily"):
                    cfg["forecast"][key][fkey] = str(val or "").strip()
                else:
                    cfg["forecast"][key][fkey] = val
        flow = automation.get("flow_entities", {})
        if isinstance(flow, dict):
            for key in ("s1", "s2", "s3"):
                src = flow.get(key, {})
                if isinstance(src, dict):
                    for k in cfg["automation"]["flow_entities"][key].keys():
                        v = src.get(k, "")
                        cfg["automation"]["flow_entities"][key][k] = str(v or "")

    view_card = raw.get("view_card", {})
    if isinstance(view_card, dict):
        count = int(_float(view_card.get("count"), cfg["view_card"]["count"]))
        cfg["view_card"]["count"] = max(1, min(6, count))
        if isinstance(view_card.get("ha_base_url"), str):
            cfg["view_card"]["ha_base_url"] = view_card.get("ha_base_url", "").strip()
        cards = view_card.get("cards", [])
        out_cards = []
        if isinstance(cards, list):
            for item in cards:
                if not isinstance(item, dict):
                    continue
                out_cards.append({
                    "title": str(item.get("title") or "").strip(),
                    "path": str(item.get("path") or "").strip(),
                })
        while len(out_cards) < cfg["view_card"]["count"]:
            out_cards.append({"title": "", "path": ""})
        cfg["view_card"]["cards"] = out_cards

    return cfg


def apply_config(cfg: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = normalize_config(cfg)
    if not isinstance(payload, dict):
        return cfg

    runtime = payload.get("runtime", {})
    if isinstance(runtime, dict):
        if "ui_poll_ms" in runtime:
            cfg["runtime"]["ui_poll_ms"] = int(_float(runtime["ui_poll_ms"], cfg["runtime"]["ui_poll_ms"]))
        if isinstance(runtime.get("mode"), str):
            cfg["runtime"]["mode"] = runtime["mode"]
        if "sites_count" in runtime:
            n = int(_float(runtime["sites_count"], cfg["runtime"]["sites_count"]))
            cfg["runtime"]["sites_count"] = max(1, min(3, n))
        if "grid_export_positive" in runtime:
            cfg["runtime"]["grid_export_positive"] = bool(runtime.get("grid_export_positive"))
        if isinstance(runtime.get("timezone"), str):
            cfg["runtime"]["timezone"] = runtime.get("timezone") or cfg["runtime"]["timezone"]
        if isinstance(runtime.get("learned_rules"), dict):
            cfg["runtime"]["learned_rules"] = runtime.get("learned_rules", {})
        if isinstance(runtime.get("ui_flags"), dict):
            cfg["runtime"]["ui_flags"] = runtime.get("ui_flags", {})
        if isinstance(runtime.get("ui_history_flags"), dict):
            cfg["runtime"]["ui_history_flags"] = runtime.get("ui_history_flags", {})

    devices = payload.get("devices", {})
    if isinstance(devices, dict):
        for key in ("s1", "s2", "s3"):
            src = devices.get(key, {}) if isinstance(devices.get(key, {}), dict) else {}
            if "name" in src:
                cfg["devices"][key]["name"] = str(src.get("name") or "").strip()
            if "id" in src:
                cfg["devices"][key]["id"] = str(src.get("id") or "").strip()

    all_entities = payload.get("all_entities", {})
    if isinstance(all_entities, dict):
        for key in ("s1", "s2", "s3"):
            items = all_entities.get(key)
            if isinstance(items, list):
                cfg["all_entities"][key] = items

    security = payload.get("security", {})
    if isinstance(security, dict) and isinstance(security.get("user_pin"), str):
        cfg["security"]["user_pin"] = security.get("user_pin", "")

    automation = payload.get("automation", {})
    if isinstance(automation, dict):
        if isinstance(automation.get("extra_datalog_entities"), list):
            raw_extra = automation.get("extra_datalog_entities") or []
            extra_list = []
            for item in raw_extra:
                if not isinstance(item, dict):
                    continue
                try:
                    site = int(item.get("site") or 0)
                except Exception:
                    site = 0
                entity_id = str(item.get("entity_id") or "").strip()
                if site in (1, 2, 3) and entity_id:
                    enabled = bool(item.get("enabled", True))
                    extra_list.append({"site": site, "entity_id": entity_id, "enabled": enabled})
                    cfg["automation"]["extra_datalog_entities"] = extra_list

        if isinstance(automation.get("extra_safe_entities"), list):
            raw_safe = automation.get("extra_safe_entities") or []
            safe_list = []
            for item in raw_safe:
                if not isinstance(item, dict):
                    continue
                try:
                    site = int(item.get("site") or 0)
                except Exception:
                    site = 0
                entity_id = str(item.get("entity_id") or "").strip()
                if site in (1, 2, 3) and entity_id:
                    enabled = bool(item.get("enabled", True))
                    safe_list.append({"site": site, "entity_id": entity_id, "enabled": enabled})
                    cfg["automation"]["extra_safe_entities"] = safe_list

        if "extra_safe_schedule" in automation:
            sched = automation.get("extra_safe_schedule", {})
        else:
            sched = None
        if isinstance(sched, dict):
            enabled = bool(sched.get("enabled", False))
            days = sched.get("days", {})
            safe_days = {k: [] for k in ("mon","tue","wed","thu","fri","sat","sun")}
            if isinstance(days, dict):
                for k in safe_days.keys():
                    items = days.get(k, [])
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        start = str(item.get("start") or "").strip()
                        end = str(item.get("end") or "").strip()
                        try:
                            pct = float(item.get("percent") or 0)
                        except Exception:
                            pct = 0.0
                        if start and end:
                            safe_days[k].append({"start": start, "end": end, "percent": pct})
            cfg["automation"]["extra_safe_schedule"] = {"enabled": enabled, "days": safe_days}

    forecast = payload.get("forecast", {})
    if isinstance(forecast, dict):
        for key in ("s1", "s2", "s3"):
            src = forecast.get(key, {}) if isinstance(forecast.get(key, {}), dict) else {}
            for fkey in cfg["forecast"][key].keys():
                if fkey in src:
                    val = src.get(fkey)
                    if fkey in ("pv_forecast_today", "pv_forecast_tomorrow", "pv_forecast_today_hourly", "pv_forecast_tomorrow_hourly", "load_daily"):
                        cfg["forecast"][key][fkey] = str(val or "").strip()
                    else:
                        cfg["forecast"][key][fkey] = val
        flow = automation.get("flow_entities", {})
        if isinstance(flow, dict):
            for key in ("s1", "s2", "s3"):
                src = flow.get(key, {})
                if isinstance(src, dict):
                    for k in cfg["automation"]["flow_entities"][key].keys():
                        if k in src:
                            cfg["automation"]["flow_entities"][key][k] = str(src.get(k) or "")

    view_card = payload.get("view_card", {})
    if isinstance(view_card, dict):
        count = int(_float(view_card.get("count"), cfg["view_card"]["count"]))
        cfg["view_card"]["count"] = max(1, min(6, count))
        if isinstance(view_card.get("ha_base_url"), str):
            cfg["view_card"]["ha_base_url"] = view_card.get("ha_base_url", "").strip()
        cards = view_card.get("cards", [])
        out_cards = []
        if isinstance(cards, list):
            for item in cards:
                if not isinstance(item, dict):
                    continue
                out_cards.append({
                    "title": str(item.get("title") or "").strip(),
                    "path": str(item.get("path") or "").strip(),
                })
        while len(out_cards) < cfg["view_card"]["count"]:
            out_cards.append({"title": "", "path": ""})
        cfg["view_card"]["cards"] = out_cards

    return cfg


def apply_entities(cfg: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = normalize_config(cfg)
    if not isinstance(payload, dict):
        return cfg
    ent = payload.get("entities", payload)
    if not isinstance(ent, dict):
        return cfg
    for key in cfg["entities"].keys():
        if key in ent:
            val = ent.get(key)
            if val is None:
                cfg["entities"][key] = None
            elif isinstance(val, str):
                cfg["entities"][key] = val.strip() or None
    return cfg


def load_config() -> Dict[str, Any]:
    if not CONF_PATH.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        raw = json.loads(CONF_PATH.read_text(encoding="utf-8"))
        return normalize_config(raw)
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONF_PATH.write_text(json.dumps(normalize_config(cfg), indent=2, ensure_ascii=False), encoding="utf-8")
