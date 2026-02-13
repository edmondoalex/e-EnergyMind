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

    security = raw.get("security", {})
    if isinstance(security, dict) and isinstance(security.get("user_pin"), str):
        cfg["security"]["user_pin"] = security.get("user_pin", "")

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

    security = payload.get("security", {})
    if isinstance(security, dict) and isinstance(security.get("user_pin"), str):
        cfg["security"]["user_pin"] = security.get("user_pin", "")

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
