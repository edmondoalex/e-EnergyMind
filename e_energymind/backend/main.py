import asyncio
import json
import logging
import time
from typing import Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .storage import load_config, save_config, normalize_config, apply_setpoints, apply_entities, apply_actuators
from .ha_client import HAClient
from .logic import compute_decision

def _read_app_version() -> str:
    path = Path("/app/config.yaml")
    if not path.exists():
        return "0.0.0"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.0.0"

APP_VERSION = _read_app_version()
app = FastAPI(title="e-EnergyMind", version=APP_VERSION)
ha = HAClient()
cfg = load_config()
ws_task: asyncio.Task | None = None
off_deadline: dict[str, float] = {"r22": 0.0, "r23": 0.0, "r24": 0.0, "rg": 0.0}
on_deadline: dict[str, float] = {"r22": 0.0, "r23": 0.0, "r24": 0.0}
off_sequence_start: float = 0.0
action_log: list[str] = []

def _append_action_log(line: str) -> None:
    try:
        log_path = Path("/config/actions.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _log_action(line: str) -> None:
    action_log.append(line)
    _append_action_log(line)

entity_icon_map: dict[str, str] = {}
last_dry_run_signature: str | None = None
recent_ui_actuations: dict[str, float] = {}
pending_auto_off: dict[str, asyncio.Task] = {}
transfer_tasks: dict[str, asyncio.Task] = {}
transfer_desired: dict[str, bool] = {}
manual_overrides: dict[str, bool] = {}
last_hvac_cmd: dict[str, tuple[str, float]] = {}
solar_night_state: bool | None = None
solar_night_last_change: float = 0.0
ws_clients: set[WebSocket] = set()
miscelatrice_task: asyncio.Task | None = None
miscelatrice_pause_until: float = 0.0
miscelatrice_last_action: str = "STOP"
miscelatrice_shutdown_until: float = 0.0
impianto_last_source: str | None = None
impianto_heat_state: dict[str, float | bool] = {"active": False, "last_change": 0.0}
gas_emergenza_state: dict[str, Any] = {"vol_ok": False, "puf_ok": False, "active": False, "last_change": 0.0}
caldaia_legna_state: dict[str, Any] = {
    "startup_deadline": float(cfg.get("caldaia_legna", {}).get("startup_deadline_ts", 0.0) or 0.0),
    "last_enabled": False,
    "forced_off": bool(cfg.get("caldaia_legna", {}).get("forced_off", False)),
}
last_modules_payload: dict[str, bool] | None = None
last_modules_save_ts: float = 0.0
SUMMER_BLOCK_MODULES = {
    "volano_to_acs",
    "volano_to_puffer",
    "resistenze_volano",
    "impianto",
    "gas_emergenza",
    "miscelatrice",
    "curva_climatica",
}

def _season_blocks_heating() -> bool:
    season = str(cfg.get("impianto", {}).get("season_mode", "winter")).lower()
    return season == "summer"

def _apply_season_block(modules: dict[str, bool]) -> tuple[dict[str, bool], bool]:
    if not _season_blocks_heating():
        return modules, False
    out = dict(modules)
    changed = False
    for key in SUMMER_BLOCK_MODULES:
        if out.get(key):
            out[key] = False
            changed = True
    return out, changed

@app.on_event("startup")
async def on_startup():
    global cfg
    global ws_task
    cfg = load_config()
    logging.basicConfig(
        level=str(cfg.get("log_level", "info")).upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    await ha.start()
    ha.set_state_callback(_on_state_changed)
    if ha.enabled:
        ws_task = asyncio.create_task(ha.run())
        asyncio.create_task(_refresh_entity_registry_loop())

@app.on_event("shutdown")
async def on_shutdown():
    global ws_task
    if ws_task:
        ws_task.cancel()
    await ha.close()

async def _refresh_entity_registry_loop():
    if not ha.enabled:
        return
    while True:
        try:
            async with ha._session.get(f"{ha._http_url}/config/entity_registry/list") as r:
                if r.status == 200:
                    data = await r.json()
                    entity_icon_map.clear()
                    for item in data:
                        eid = item.get("entity_id")
                        icon = item.get("icon")
                        if eid and icon:
                            entity_icon_map[eid] = icon
        except Exception:
            pass
        await asyncio.sleep(60)

app.mount("/assets", StaticFiles(directory="/app/static/assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def ui():
    with open("/app/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/config")
async def get_config():
    return JSONResponse(cfg)

@app.post("/api/config")
async def set_config(payload: dict):
    global cfg
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    cfg = normalize_config(payload)
    save_config(cfg)
    return JSONResponse({"ok": True})

@app.get("/api/decision")
async def decision():
    data = compute_decision(cfg, ha.states)
    await _apply_resistance_live(data)
    await _apply_transfer_live(data)
    await _apply_solar_live(data)
    await _apply_impianto_live()
    await _apply_gas_emergenza_live()
    await _apply_caldaia_legna_live()
    await _apply_miscelatrice_live(data)
    _apply_legna_timer_reason(data)
    data["zones"] = _build_zones_state()
    return JSONResponse(data)



def _state_is_on(entity_id: str | None) -> bool:
    if not entity_id:
        return False
    val = ha.states.get(entity_id, {}).get("state")
    if val is None:
        return False
    sval = str(val).strip().lower()
    return sval in ("on", "true", "1", "yes", "heat", "heating")
def _get_state(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    return ha.states.get(entity_id, {}).get("state")
def _get_num(entity_id: str | None) -> float | None:
    if not entity_id:
        return None
    raw = ha.states.get(entity_id, {}).get("state")
    if raw is None:
        return None
    try:
        return float(raw)
    except Exception:
        return None

def _gas_sources_ok() -> bool:
    gas_cfg = cfg.get("gas_emergenza", {})
    ent = cfg.get("entities", {})
    t_volano = _get_num(ent.get("t_volano"))
    if t_volano is None:
        t_volano = _get_num(ent.get("t_volano_alto"))
    t_puffer = _get_num(ent.get("t_puffer"))
    if t_puffer is None:
        t_puffer = _get_num(ent.get("t_puffer_alto"))
    vol_min = float(gas_cfg.get("volano_min_c", 35.0))
    vol_h = float(gas_cfg.get("volano_hyst_c", 2.0))
    puf_min = float(gas_cfg.get("puffer_min_c", 35.0))
    puf_h = float(gas_cfg.get("puffer_hyst_c", 2.0))
    vol_prev = bool(gas_emergenza_state.get("vol_ok"))
    puf_prev = bool(gas_emergenza_state.get("puf_ok"))
    # se sensori mancanti/unavailable, trattali come NON ok per evitare flapping
    if t_volano is None:
        vol_ok = False
    else:
        vol_ok = t_volano > vol_min if vol_prev else t_volano >= (vol_min + vol_h)
    if t_puffer is None:
        puf_ok = False
    else:
        puf_ok = t_puffer > puf_min if puf_prev else t_puffer >= (puf_min + puf_h)
    gas_emergenza_state["vol_ok"] = vol_ok
    gas_emergenza_state["puf_ok"] = puf_ok
    return bool(vol_ok or puf_ok)

def _gas_emergenza_active() -> bool:
    if not cfg.get("modules_enabled", {}).get("gas_emergenza", False):
        gas_emergenza_state["active"] = False
        return False
    gas_cfg = cfg.get("gas_emergenza", {})
    need = not _gas_sources_ok()
    now = time.time()
    min_on = float(gas_cfg.get("min_on_s", 120.0))
    min_off = float(gas_cfg.get("min_off_s", 120.0))
    active = bool(gas_emergenza_state.get("active"))
    last_change = float(gas_emergenza_state.get("last_change") or 0.0)
    if need:
        if not active and (now - last_change) < min_off:
            return False
        if not active:
            gas_emergenza_state["active"] = True
            gas_emergenza_state["last_change"] = now
        return True
    # not needed
    if active and (now - last_change) < min_on:
        return True
    if active:
        gas_emergenza_state["active"] = False
        gas_emergenza_state["last_change"] = now
    return False


def _impianto_auto_heat(desired: bool, imp_cfg: dict) -> bool:
    # anti-flap per termostati in modalit? normale
    min_on = float(imp_cfg.get("auto_heat_min_on_s", 60.0))
    min_off = float(imp_cfg.get("auto_heat_min_off_s", 60.0))
    now = time.time()
    active = bool(impianto_heat_state.get("active"))
    last = float(impianto_heat_state.get("last_change") or 0.0)
    if desired:
        if not active and (now - last) < min_off:
            return False
        if not active:
            impianto_heat_state["active"] = True
            impianto_heat_state["last_change"] = now
        return True
    # desired false
    if active and (now - last) < min_on:
        return True
    if active:
        impianto_heat_state["active"] = False
        impianto_heat_state["last_change"] = now
    return False

def _collect_zones(imp: dict) -> list[str]:
    zones: list[str] = []
    for key in ("zones_pt", "zones_p1", "zones_mans", "zones_lab"):
        zones.extend([z for z in (imp.get(key) or []) if z])
    zone_scala = imp.get("zone_scala") or ""
    if zone_scala:
        zones.append(zone_scala)
    # unique preserve order
    seen = set()
    out = []
    for z in zones:
        if z not in seen:
            seen.add(z)
            out.append(z)
    return out

async def _build_snapshot() -> dict:
    data = compute_decision(cfg, ha.states)
    await _apply_resistance_live(data)
    await _apply_transfer_live(data)
    await _apply_solar_live(data)
    await _apply_impianto_live()
    await _apply_gas_emergenza_live()
    await _apply_caldaia_legna_live()
    _apply_legna_timer_reason(data)
    act = {}
    for k, eid in (cfg.get("actuators", {}) or {}).items():
        if eid:
            st = ha.states.get(eid, {})
            act[k] = {
                "entity_id": eid,
                "state": st.get("state"),
                "attributes": st.get("attributes", {}),
                "icon": entity_icon_map.get(eid)
            }
        else:
            act[k] = {"entity_id": None, "state": None, "attributes": {}, "icon": None}
    ent = {}
    for k, eid in (cfg.get("entities", {}) or {}).items():
        if eid:
            st = ha.states.get(eid, {})
            ent[k] = {
                "entity_id": eid,
                "state": st.get("state"),
                "attributes": st.get("attributes", {}),
                "icon": entity_icon_map.get(eid)
            }
        else:
            ent[k] = {"entity_id": None, "state": None, "attributes": {}, "icon": None}
    return {
        "decision": data,
        "status": {
            "ha_connected": bool(ha.enabled),
            "token_source": getattr(ha, "token_source", None),
            "version": APP_VERSION,
            "runtime_mode": cfg.get("runtime", {}).get("mode", "dry-run"),
        },
        "actions": action_log[-50:],
        "actuators": act,
        "entities": ent,
        "modules": cfg.get("modules_enabled", {}),
    }

def _apply_legna_timer_reason(data: dict) -> None:
    if not cfg.get("modules_enabled", {}).get("caldaia_legna", False):
        return
    forced_off = bool(caldaia_legna_state.get("forced_off"))
    deadline = float(caldaia_legna_state.get("startup_deadline") or 0.0)
    now = time.time()
    computed = data.setdefault("computed", {})
    reasons = computed.setdefault("module_reasons", {})
    reason = reasons.get("caldaia_legna")
    legna_block = computed.get("caldaia_legna")
    if forced_off:
        reason = "Timer scaduto: modulo inattivo."
        reasons["caldaia_legna"] = reason
        if isinstance(legna_block, dict):
            legna_block["enabled"] = False
            legna_block["power"] = False
            legna_block["ta"] = False
            legna_block["reason"] = reason
            legna_block["timer_remaining_s"] = 0
        return
    if deadline <= now:
        return
    remaining = int(max(0.0, deadline - now))
    suffix = f"Timer spegnimento attivo: {remaining}s"
    if reason:
        reason = f"{reason} | {suffix}"
    else:
        reason = suffix
    reasons["caldaia_legna"] = reason
    if isinstance(legna_block, dict):
        legna_block["reason"] = reason
        legna_block["timer_remaining_s"] = remaining


def _build_zones_state() -> list[dict]:
    imp = cfg.get("impianto", {})
    cooling_blocked = set(imp.get("cooling_blocked", []))
    zones = []
    def add_group(group_name: str, lst: list):
        for eid in lst:
            if not eid:
                continue
            st = ha.states.get(eid, {})
            state = st.get("state")
            attr = st.get("attributes", {})
            zones.append({
                "group": group_name,
                "entity_id": eid,
                "state": state,
                "hvac_action": attr.get("hvac_action"),
                "temperature": attr.get("current_temperature"),
                "setpoint": attr.get("temperature"),
                "active": _zone_active(eid, cooling_blocked)
            })
    add_group("PT", imp.get("zones_pt", []))
    add_group("1P", imp.get("zones_p1", []))
    add_group("MANSARDA", imp.get("zones_mans", []))
    add_group("LAB", imp.get("zones_lab", []))
    scala = imp.get("zone_scala")
    if scala:
        add_group("SCALA", [scala])
    return zones
def _actuator_key_for_entity(entity_id: str) -> str | None:
    for key, eid in (cfg.get("actuators", {}) or {}).items():
        if eid == entity_id:
            return key
    return None

def _module_for_actuator_key(key: str) -> str | None:
    if "resistenza" in key:
        return "resistenze_volano"
    if "impianto" in key or "comparto" in key or "mandata" in key:
        return "impianto"
    if "solare" in key or "ritorno_solare" in key:
        return "solare"
    if "miscelatrice" in key:
        return "miscelatrice"
    if "puffer_to_acs" in key:
        return "puffer_to_acs"
    if "pdc" in key or "antigelo" in key or "comparto_pdc" in key:
        return "pdc"
    if "gas_boiler" in key or "caldaia_gas" in key:
        return "gas_emergenza"
    if "caldaia_legna" in key:
        return "caldaia_legna"
    return None



def _zone_active(entity_id: str | None, cooling_blocked: set[str]) -> bool:
    if not entity_id:
        return False
    st = ha.states.get(entity_id, {})
    state = str(st.get("state") or "").lower()
    dom = entity_id.split(".", 1)[0] if "." in entity_id else ""
    hvac_action = str(st.get("attributes", {}).get("hvac_action") or "").lower()
    is_cool = state in ("cool", "cooling") or hvac_action == "cooling"
    if is_cool and entity_id in cooling_blocked:
        return False
    if dom in ("switch", "binary_sensor", "input_boolean"):
        return state in ("on", "true", "1", "yes")
    if dom == "climate":
        if state in ("off", "idle", "unavailable", "unknown"):
            return False
        # usa azione reale, ma solo se lo stato non è OFF
        return hvac_action in ("heating", "cooling") or state in ("heat", "heating", "cool", "cooling")
    # default: treat truthy text as active
    return state in ("on", "true", "1", "yes", "heat", "heating")

def _gas_zone_demand(eid: str | None, cooling_blocked: set[str]) -> bool:
    if not eid:
        return False
    st = ha.states.get(eid, {})
    dom = eid.split(".", 1)[0] if "." in eid else ""
    action = str(st.get("attributes", {}).get("hvac_action") or "").lower()
    if dom == "climate":
        # in gas: richiesta solo se realmente in heating
        return action == "heating"
    return _zone_active(eid, cooling_blocked)

async def _set_pump_delayed(name: str, pump_eid: str | None, want_on: bool, delay_on: float, delay_off: float) -> None:
    prev = transfer_desired.get(name)
    transfer_desired[name] = want_on
    if want_on:
        _cancel_transfer_task(f"{name}:off")
        if f"{name}:on" not in transfer_tasks:
            transfer_tasks[f"{name}:on"] = asyncio.create_task(_delayed_actuate(f"{name}:on", pump_eid, True, delay_on))
    else:
        _cancel_transfer_task(f"{name}:on")
        if f"{name}:off" not in transfer_tasks:
            transfer_tasks[f"{name}:off"] = asyncio.create_task(_delayed_actuate(f"{name}:off", pump_eid, False, delay_off))

async def _force_pump_off(name: str, pump_eid: str | None) -> None:
    transfer_desired[name] = False
    _cancel_transfer_task(f"{name}:on")
    _cancel_transfer_task(f"{name}:off")
    await _set_actuator(pump_eid, False)
def _is_recent_ui(entity_id: str, window_s: float = 4.0) -> bool:
    ts = recent_ui_actuations.get(entity_id)
    if not ts:
        return False
    if time.time() - ts > window_s:
        recent_ui_actuations.pop(entity_id, None)
        return False
    return True

def _is_manual(entity_id: str | None) -> bool:
    if not entity_id:
        return False
    return bool(manual_overrides.get(entity_id))

async def _auto_off_after_delay(entity_id: str, module_key: str | None) -> None:
    try:
        await asyncio.sleep(2)
        if _is_recent_ui(entity_id):
            return
        current = _get_state(entity_id)
        if current != "on":
            return
        if module_key and not cfg.get("modules_enabled", {}).get(module_key, True):
            return
        await ha.call_service(entity_id, "off")
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} AUTO-OFF {entity_id} (HA manual guard)")
    finally:
        pending_auto_off.pop(entity_id, None)

async def _on_state_changed(entity_id: str, new_state: dict) -> None:
    if not entity_id or not isinstance(new_state, dict):
        return
    if new_state.get("state") != "on":
        return
    if _is_recent_ui(entity_id):
        return
    if _is_manual(entity_id):
        return
    key = _actuator_key_for_entity(entity_id)
    if not key:
        return
    module_key = _module_for_actuator_key(key)
    if module_key and not cfg.get("modules_enabled", {}).get(module_key, True):
        return
    # Se non appartiene a nessun modulo, lascialo manuale (no auto-off)
    if module_key is None:
        return
    if entity_id in pending_auto_off:
        return
    pending_auto_off[entity_id] = asyncio.create_task(_auto_off_after_delay(entity_id, module_key))

def _log_dry_run(decision_data: dict) -> None:
    global last_dry_run_signature
    step = int(decision_data.get("computed", {}).get("resistance_step", 0))
    export_w = decision_data.get("inputs", {}).get("grid_export_w")
    dest = decision_data.get("computed", {}).get("dest")
    source = decision_data.get("computed", {}).get("source_to_acs")
    act = cfg.get("actuators", {})
    flags = decision_data.get("computed", {}).get("flags", {})
    modules = cfg.get("modules_enabled", {})
    r22 = act.get("r22_resistenza_1_volano_pdc")
    r23 = act.get("r23_resistenza_2_volano_pdc")
    r24 = act.get("r24_resistenza_3_volano_pdc")
    rg = act.get("generale_resistenze_volano_pdc")
    want = {
        "R22": "ON" if step >= 1 else "OFF",
        "R23": "ON" if step >= 2 else "OFF",
        "R24": "ON" if step >= 3 else "OFF",
        "RG": "ON" if step >= 1 else "OFF",
    }
    notes: list[str] = []
    def _mod_state(key: str, active: bool, has_logic: bool = True) -> str:
        if not modules.get(key, True):
            return "DISABLED"
        if not has_logic:
            notes.append(key)
            return "OFF"
        return "ON" if active else "OFF"

    res_module = "DISABLED"
    if modules.get("resistenze_volano", True):
        res_module = f"STEP {step}"

    module_states = {
        "resistenze_volano": res_module,
        "volano_to_acs": _mod_state("volano_to_acs", bool(flags.get("volano_to_acs"))),
        "volano_to_puffer": _mod_state("volano_to_puffer", bool(flags.get("volano_to_puffer"))),
        "puffer_to_acs": _mod_state("puffer_to_acs", bool(flags.get("puffer_to_acs"))),
        "solare": _mod_state("solare", bool(flags.get("solare_to_acs"))),
        "miscelatrice": _mod_state("miscelatrice", False, has_logic=False),
        "pdc": _mod_state("pdc", False, has_logic=False)
    }

    signature = json.dumps({
        "dest": dest,
        "source": source,
        "export_w": export_w,
        "step": step,
        "modules": module_states,
        "want": want
    }, sort_keys=True)
    if signature == last_dry_run_signature:
        return
    last_dry_run_signature = signature
    action_log.append(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} DRY-RUN dest={dest} source={source} "
        f"export={export_w}W step={step}"
    )
    action_log.append(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} DRY-RUN would set "
        f"{want['RG']} {rg} | {want['R22']} {r22} | {want['R23']} {r23} | {want['R24']} {r24}"
    )
    action_log.append(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} DRY-RUN modules "
        f"resistenze_volano={module_states['resistenze_volano']}, "
        f"volano_to_acs={module_states['volano_to_acs']}, "
        f"volano_to_puffer={module_states['volano_to_puffer']}, "
        f"puffer_to_acs={module_states['puffer_to_acs']}, "
        f"solare={module_states['solare']}, "
        f"miscelatrice={module_states['miscelatrice']}, "
        f"pdc={module_states['pdc']}"
    )
    if notes:
        action_log.append(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} DRY-RUN note: no logic for {', '.join(notes)}"
        )

async def _set_resistance(entity_id: str | None, want_on: bool) -> None:
    if not entity_id or not ha.enabled:
        return
    if _is_manual(entity_id):
        return
    current = _get_state(entity_id)
    if want_on and current != "on":
        recent_ui_actuations[entity_id] = time.time()
        await ha.call_service(entity_id, "on")
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} ON {entity_id}")
    if (not want_on) and current != "off":
        recent_ui_actuations[entity_id] = time.time()
        await ha.call_service(entity_id, "off")
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} OFF {entity_id}")

async def _set_actuator(entity_id: str | None, want_on: bool) -> None:
    if not entity_id or not ha.enabled:
        return
    if _is_manual(entity_id):
        return
    current = _get_state(entity_id)
    if want_on and current != "on":
        recent_ui_actuations[entity_id] = time.time()
        await ha.call_service(entity_id, "on")
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} ON {entity_id}")
    if (not want_on) and current != "off":
        recent_ui_actuations[entity_id] = time.time()
        await ha.call_service(entity_id, "off")
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} OFF {entity_id}")

def _sun_is_night() -> bool | None:
    st = ha.states.get("sun.sun", {})
    state = st.get("state")
    if state == "below_horizon":
        return True
    if state == "above_horizon":
        return False
    return None

def _solar_night_debounced() -> bool:
    global solar_night_state, solar_night_last_change
    now = time.time()
    sol_cfg = cfg.get("solare", {})
    pv_entity = sol_cfg.get("pv_entity", "")
    pv_day = float(sol_cfg.get("pv_day_w", 1000.0))
    pv_night = float(sol_cfg.get("pv_night_w", 300.0))
    debounce_s = float(sol_cfg.get("pv_debounce_s", 300))

    desired = None
    if pv_entity:
        try:
            pv_val = float(ha.states.get(pv_entity, {}).get("state"))
        except Exception:
            pv_val = None
        if pv_val is not None:
            if solar_night_state is None:
                desired = pv_val < pv_night
            else:
                if solar_night_state:
                    desired = pv_val < pv_day
                else:
                    desired = pv_val < pv_night
    if desired is None:
        desired = _sun_is_night()
    if desired is None:
        # keep last if unknown
        return bool(solar_night_state)
    if solar_night_state is None:
        solar_night_state = desired
        solar_night_last_change = now
        return desired
    if desired != solar_night_state and (now - solar_night_last_change) < debounce_s:
        return solar_night_state
    if desired != solar_night_state:
        solar_night_state = desired
        solar_night_last_change = now
    return solar_night_state

def _cancel_transfer_task(key: str) -> None:
    task = transfer_tasks.pop(key, None)
    if task:
        task.cancel()

async def _delayed_actuate(task_key: str, entity_id: str, want_on: bool, delay_s: float) -> None:
    try:
        await asyncio.sleep(max(0.0, delay_s))
        await _set_actuator(entity_id, want_on)
    finally:
        transfer_tasks.pop(task_key, None)

async def _set_transfer_pair(
    name: str,
    valve_eid: str | None,
    pump_eid: str | None,
    want_on: bool,
    start_s: float,
    stop_s: float,
) -> None:
    prev = transfer_desired.get(name)
    transfer_desired[name] = want_on
    if want_on:
        await _set_actuator(valve_eid, True)
        if pump_eid and _get_state(pump_eid) != "on":
            if prev is False:
                _cancel_transfer_task(f"{name}:pump_off")
            if f"{name}:pump_on" not in transfer_tasks:
                transfer_tasks[f"{name}:pump_on"] = asyncio.create_task(
                    _delayed_actuate(f"{name}:pump_on", pump_eid, True, start_s)
                )
    else:
        await _set_actuator(valve_eid, False)
        if pump_eid and _get_state(pump_eid) != "off":
            if prev is True:
                _cancel_transfer_task(f"{name}:pump_on")
            if f"{name}:pump_off" not in transfer_tasks:
                transfer_tasks[f"{name}:pump_off"] = asyncio.create_task(
                    _delayed_actuate(f"{name}:pump_off", pump_eid, False, stop_s)
                )

async def _set_pump_only(name: str, pump_eid: str | None, want_on: bool) -> None:
    prev = transfer_desired.get(name)
    transfer_desired[name] = want_on
    if prev is not None and prev == want_on:
        await _set_actuator(pump_eid, want_on)
        return
    _cancel_transfer_task(f"{name}:pump_on")
    _cancel_transfer_task(f"{name}:pump_off")
    await _set_actuator(pump_eid, want_on)

async def _set_valve_only(valve_eid: str | None, want_on: bool) -> None:
    await _set_actuator(valve_eid, want_on)

async def _pulse_actuator(task_name: str, eid: str | None, duration_s: float) -> None:
    if not eid:
        return
    try:
        await _set_actuator(eid, True)
        await asyncio.sleep(max(0.1, duration_s))
    finally:
        await _set_actuator(eid, False)

async def _apply_resistance_live(decision_data: dict) -> None:
    if cfg.get("runtime", {}).get("mode") != "live":
        _log_dry_run(decision_data)
        return
    if not cfg.get("modules_enabled", {}).get("resistenze_volano", True):
        act = cfg.get("actuators", {})
        r22 = act.get("r22_resistenza_1_volano_pdc")
        r23 = act.get("r23_resistenza_2_volano_pdc")
        r24 = act.get("r24_resistenza_3_volano_pdc")
        rg = act.get("generale_resistenze_volano_pdc")
        for ent in (r22, r23, r24, rg):
            await _set_resistance(ent, False)
        return
    act = cfg.get("actuators", {})
    r22 = act.get("r22_resistenza_1_volano_pdc")
    r23 = act.get("r23_resistenza_2_volano_pdc")
    r24 = act.get("r24_resistenza_3_volano_pdc")
    rg = act.get("generale_resistenze_volano_pdc")
    step = int(decision_data.get("computed", {}).get("resistance_step", 0))
    export_w = float(decision_data.get("inputs", {}).get("grid_export_w") or 0.0)
    off_thr = float(cfg.get("resistance", {}).get("off_threshold_w", 0.0))
    desired = {
        "r22": step >= 1,
        "r23": step >= 2,
        "r24": step >= 3,
    }

    off_delay = int(cfg.get("resistance", {}).get("off_delay_s", 5))
    on_delay = int(cfg.get("resistance", {}).get("step_up_delay_s", 10))
    now = time.time()

    global off_sequence_start
    if export_w <= off_thr:
        if off_sequence_start == 0.0:
            off_sequence_start = now
    else:
        off_sequence_start = 0.0

    def _allow_off(key: str) -> bool:
        if export_w > off_thr:
            return True
        if off_sequence_start == 0.0:
            return False
        elapsed = now - off_sequence_start
        if key == "r24":
            return elapsed >= off_delay
        if key == "r23":
            return elapsed >= (off_delay * 2)
        if key == "r22":
            return elapsed >= (off_delay * 3)
        return False

    for key, ent in (("r22", r22), ("r23", r23), ("r24", r24)):
        want_on = desired[key]
        current = _get_state(ent)
        if want_on:
            off_deadline[key] = 0.0
            if current != "on":
                if on_deadline[key] == 0.0:
                    on_deadline[key] = now + on_delay
                elif now >= on_deadline[key]:
                    await _set_resistance(ent, True)
                    on_deadline[key] = 0.0
            else:
                on_deadline[key] = 0.0
        else:
            on_deadline[key] = 0.0
            if current == "on":
                if export_w > off_thr:
                    off_deadline[key] = 0.0
                elif _allow_off(key):
                    if off_deadline[key] == 0.0:
                        off_deadline[key] = now + off_delay
                    elif now >= off_deadline[key]:
                        await _set_resistance(ent, False)
                        off_deadline[key] = 0.0
            else:
                off_deadline[key] = 0.0

    if rg:
        any_desired = desired["r22"] or desired["r23"] or desired["r24"]
        any_actual = _get_state(r22) == "on" or _get_state(r23) == "on" or _get_state(r24) == "on"
        want_general = any_desired or any_actual
        current_rg = _get_state(rg)
        if want_general:
            off_deadline["rg"] = 0.0
            if current_rg != "on":
                await _set_resistance(rg, True)
        else:
            if current_rg == "on":
                if off_deadline["rg"] == 0.0:
                    off_deadline["rg"] = now + off_delay
                elif now >= off_deadline["rg"]:
                    await _set_resistance(rg, False)
                    off_deadline["rg"] = 0.0
            else:
                off_deadline["rg"] = 0.0

    # reflect real step from actuators for UI
    actual_step = 0
    if _get_state(r24) == "on":
        actual_step = 3
    elif _get_state(r23) == "on":
        actual_step = 2
    elif _get_state(r22) == "on":
        actual_step = 1
    computed = decision_data.setdefault("computed", {})
    computed["resistance_step"] = actual_step if actual_step > 0 else computed.get("resistance_step", 0)

    # annotate live delay info in decision payload
    reasons = computed.setdefault("module_reasons", {})
    delay_notes: list[str] = []
    if off_sequence_start > 0.0:
        delay_notes.append(f"off_seq {int(now - off_sequence_start)}s")
    for key in ("r22", "r23", "r24"):
        if on_deadline[key] > now:
            delay_notes.append(f"{key} ON in {int(on_deadline[key] - now)}s")
        if off_deadline[key] > now:
            delay_notes.append(f"{key} OFF in {int(off_deadline[key] - now)}s")
    if off_deadline.get("rg", 0.0) > now:
        delay_notes.append(f"RG OFF in {int(off_deadline['rg'] - now)}s")
    if delay_notes:
        base_reason = reasons.get("resistenze_volano", "")
        suffix = " | Delay: " + ", ".join(delay_notes)
        reasons["resistenze_volano"] = (base_reason + suffix) if base_reason else ("Delay: " + ", ".join(delay_notes))

async def _apply_transfer_live(decision_data: dict) -> None:
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return

    flags = decision_data.get("computed", {}).get("flags", {})
    modules = cfg.get("modules_enabled", {})
    act = cfg.get("actuators", {})

    r6 = act.get("r6_valve_pdc_to_integrazione_acs")
    r7 = act.get("r7_valve_pdc_to_integrazione_puffer")
    r13 = act.get("r13_pump_pdc_to_acs_puffer")
    r14 = act.get("r14_pump_puffer_to_acs")

    if not (modules.get("volano_to_acs", True) or modules.get("volano_to_puffer", True) or modules.get("puffer_to_acs", True)):
        await _set_valve_only(r6, False)
        await _set_valve_only(r7, False)
        await _set_pump_only("volano_to_acs", r13, False)
        await _set_pump_only("volano_to_puffer", r13, False)
        await _set_pump_only("puffer_to_acs", r14, False)
        return

    want_vol_acs = bool(flags.get("volano_to_acs")) and modules.get("volano_to_acs", True)
    want_vol_puf = bool(flags.get("volano_to_puffer")) and modules.get("volano_to_puffer", True)
    want_puf_acs = bool(flags.get("puffer_to_acs")) and modules.get("puffer_to_acs", True)

    if want_vol_acs:
        want_vol_puf = False
        want_puf_acs = False

    timers = cfg.get("timers", {})
    vta_start = float(timers.get("volano_to_acs_start_s", 5))
    vta_stop = float(timers.get("volano_to_acs_stop_s", 2))
    vtp_start = float(timers.get("volano_to_puffer_start_s", 5))
    vtp_stop = float(timers.get("volano_to_puffer_stop_s", 2))

    if want_vol_acs:
        await _set_transfer_pair("volano_to_acs", r6, r13, True, vta_start, vta_stop)
        await _set_valve_only(r7, False)
    elif want_vol_puf:
        await _set_valve_only(r6, False)
        await _set_transfer_pair("volano_to_puffer", r7, r13, True, vtp_start, vtp_stop)
    else:
        await _set_transfer_pair("volano_to_acs", r6, r13, False, vta_start, vta_stop)
        await _set_transfer_pair("volano_to_puffer", r7, r13, False, vtp_start, vtp_stop)

    await _set_pump_only("puffer_to_acs", r14, want_puf_acs)

async def _apply_solar_live(decision_data: dict) -> None:
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return
    if not cfg.get("modules_enabled", {}).get("solare", True):
        act = cfg.get("actuators", {})
        r8 = act.get("r8_valve_solare_notte_low_temp")
        r9 = act.get("r9_valve_solare_normal_funz")
        r10 = act.get("r10_valve_solare_precedenza_acs")
        await _set_actuator(r8, False)
        await _set_actuator(r9, False)
        await _set_actuator(r10, False)
        return

    sol_cfg = cfg.get("solare", {})
    mode = sol_cfg.get("mode", "auto")
    night = (mode == "night") or (mode == "auto" and _solar_night_debounced())

    act = cfg.get("actuators", {})
    r8 = act.get("r8_valve_solare_notte_low_temp")
    r9 = act.get("r9_valve_solare_normal_funz")
    r10 = act.get("r10_valve_solare_precedenza_acs")

    # R8/R9/R10 non devono restare in manuale: forza auto
    for eid in (r8, r9, r10):
        if eid:
            manual_overrides.pop(eid, None)

    # Cutback: se ACS o solare troppo caldi
    ent = cfg.get("entities", {})
    t_acs = ha.states.get(ent.get("t_acs"), {}).get("state")
    t_sol = ha.states.get(ent.get("t_solare_mandata"), {}).get("state")
    try:
        t_acs = float(t_acs)
    except Exception:
        t_acs = None
    try:
        t_sol = float(t_sol)
    except Exception:
        t_sol = None
    acs_max = float(cfg.get("acs", {}).get("max_c", 60.0))
    sol_max = float(sol_cfg.get("max_c", 90.0))
    cutback = (t_acs is not None and t_acs >= acs_max) or (t_sol is not None and t_sol >= sol_max)

    # R10: precedenza ACS quando solare attivo e non in cutback (vale anche di notte)
    solar_active = decision_data.get("computed", {}).get("source_to_acs") == "SOLAR"
    r10_on = bool(solar_active and (not cutback))
    await _set_actuator(r10, r10_on)

    # R8/R9: mai tutte chiuse. Se R10 ON, R8 e R9 devono essere OFF.
    if r10_on:
        await _set_actuator(r8, False)
        await _set_actuator(r9, False)
    elif night:
        await _set_actuator(r8, True)
        await _set_actuator(r9, False)
    else:
        await _set_actuator(r8, False)
        await _set_actuator(r9, True)

async def _apply_miscelatrice_live(decision_data: dict) -> None:
    global miscelatrice_task, miscelatrice_pause_until, miscelatrice_last_action, miscelatrice_shutdown_until
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return
    # In gas emergenza la miscelatrice resta sempre in ALZA
    if cfg.get("modules_enabled", {}).get("gas_emergenza", False) and _gas_emergenza_active():
        act = cfg.get("actuators", {})
        r16 = act.get("r16_cmd_miscelatrice_alza")
        r17 = act.get("r17_cmd_miscelatrice_abbassa")
        if miscelatrice_task and not miscelatrice_task.done():
            miscelatrice_task.cancel()
            miscelatrice_task = None
        miscelatrice_shutdown_until = 0.0
        miscelatrice_pause_until = 0.0
        await _set_actuator(r17, False)
        await _set_actuator(r16, True)
        miscelatrice_last_action = "ALZA"
        return
    if not cfg.get("modules_enabled", {}).get("miscelatrice", True):
        act = cfg.get("actuators", {})
        await _set_actuator(act.get("r16_cmd_miscelatrice_alza"), False)
        await _set_actuator(act.get("r17_cmd_miscelatrice_abbassa"), False)
        return

    ent = cfg.get("entities", {})
    act = cfg.get("actuators", {})
    cfg_misc = cfg.get("miscelatrice", {})
    imp_cfg = cfg.get("impianto", {})
    imp = (decision_data.get("computed", {}) or {}).get("impianto", {}) or {}

    imp_active = (
        cfg.get("modules_enabled", {}).get("impianto", True)
        and imp.get("richiesta")
        and (not imp.get("blocked_cold"))
        and (imp.get("source") not in (None, "OFF"))
    )

    # miscelatrice: se impianto inattivo -> chiusura forzata 180s, poi stop
    if not imp_active:
        now = time.time()
        close_s = 180.0
        r16 = act.get("r16_cmd_miscelatrice_alza")
        r17 = act.get("r17_cmd_miscelatrice_abbassa")
        # shutdown completato: non riarmare finché impianto non torna attivo
        if miscelatrice_shutdown_until < 0:
            await _set_actuator(r16, False)
            await _set_actuator(r17, False)
            miscelatrice_last_action = "STOP"
            return
        # shutdown in corso: continua senza riarmare
        if miscelatrice_shutdown_until > now:
            await _set_actuator(r16, False)
            return
        # se era in corso ed è finito, segna completato
        if miscelatrice_shutdown_until > 0 and miscelatrice_shutdown_until <= now:
            miscelatrice_shutdown_until = -1.0
            await _set_actuator(r16, False)
            await _set_actuator(r17, False)
            miscelatrice_last_action = "STOP"
            return
        # avvia chiusura lunga una sola volta
        if miscelatrice_task and not miscelatrice_task.done():
            miscelatrice_task.cancel()
            miscelatrice_task = None
        await _set_actuator(r16, False)
        miscelatrice_shutdown_until = now + close_s
        miscelatrice_last_action = "ABBASSA"
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MISCELATRICE SHUTDOWN close {int(close_s)}s")
        miscelatrice_task = asyncio.create_task(
            _pulse_actuator("miscelatrice_shutdown_close", r17, close_s)
        )
        return

    # impianto tornato attivo: cancella eventuale chiusura
    if miscelatrice_shutdown_until != 0:
        miscelatrice_shutdown_until = 0.0
        if miscelatrice_task and not miscelatrice_task.done():
            miscelatrice_task.cancel()
            miscelatrice_task = None
        await _set_actuator(act.get("r16_cmd_miscelatrice_alza"), False)
        await _set_actuator(act.get("r17_cmd_miscelatrice_abbassa"), False)

    r16 = act.get("r16_cmd_miscelatrice_alza")
    r17 = act.get("r17_cmd_miscelatrice_abbassa")
    # interblocco hard: mai entrambi ON
    if _get_state(r16) == "on":
        await _set_actuator(r17, False)
    if _get_state(r17) == "on":
        await _set_actuator(r16, False)

    t_mandata = _get_num(ent.get("t_mandata_miscelata"))
    if t_mandata is None:
        return

    sp = None
    sp_eid = ent.get("miscelatrice_setpoint")
    if sp_eid:
        sp = _get_num(sp_eid)
    if sp is None:
        try:
            sp = float(cfg_misc.get("setpoint_c", 45.0))
        except Exception:
            sp = 45.0
    curve = (decision_data.get("computed", {}) or {}).get("curva_climatica", {}) or {}
    if cfg.get("modules_enabled", {}).get("curva_climatica", True) and curve.get("setpoint") is not None:
        try:
            sp = float(curve.get("setpoint"))
        except Exception:
            pass

    hyst = float(cfg_misc.get("hyst_c", 0.5))
    kp_base = float(cfg_misc.get("kp", 2.0))
    min_imp = float(cfg_misc.get("min_imp_s", 1.0))
    max_imp = float(cfg_misc.get("max_imp_s", 8.0))
    pause_s = float(cfg_misc.get("pause_s", 5.0))
    dt_ref = float(cfg_misc.get("dt_ref_c", 10.0))
    dt_min_f = float(cfg_misc.get("dt_min_factor", 0.6))
    dt_max_f = float(cfg_misc.get("dt_max_factor", 1.4))
    err = sp - t_mandata
    t_rit = _get_num(ent.get("t_ritorno_miscelato"))
    dt = None
    kp_eff = kp_base
    if t_rit is not None and dt_ref > 0:
        dt = max(0.0, t_mandata - t_rit)
        factor = max(dt_min_f, min(dt_max_f, dt / dt_ref))
        kp_eff = kp_base * factor
    if abs(err) <= hyst:
        await _set_actuator(r16, False)
        await _set_actuator(r17, False)
        miscelatrice_last_action = "STOP"
        return

    now = time.time()
    if now < miscelatrice_pause_until:
        return

    direction = "ALZA" if err > 0 else "ABBASSA"
    duration = max(min_imp, min(max_imp, abs(err) * kp_eff))

    # cancel previous pulse
    if miscelatrice_task and not miscelatrice_task.done():
        miscelatrice_task.cancel()
        miscelatrice_task = None
        # ensure both outputs are off after cancellation
        await _set_actuator(act.get("r16_cmd_miscelatrice_alza"), False)
        await _set_actuator(act.get("r17_cmd_miscelatrice_abbassa"), False)

    if direction == "ALZA":
        await _set_actuator(r17, False)
        miscelatrice_task = asyncio.create_task(
            _pulse_actuator("miscelatrice_alza", r16, duration)
        )
    else:
        await _set_actuator(r16, False)
        miscelatrice_task = asyncio.create_task(
            _pulse_actuator("miscelatrice_abbassa", r17, duration)
        )

    miscelatrice_last_action = direction
    miscelatrice_pause_until = now + pause_s

async def _set_climate_hvac_mode(entity_id: str | None, mode: str, reason: str | None = None) -> None:
    if not entity_id or not ha.enabled:
        return
    prev = last_hvac_cmd.get(entity_id)
    now = time.time()
    if prev and prev[0] == mode and (now - prev[1]) < 30:
        return
    current = _get_state(entity_id)
    if current == mode:
        return
    await ha.call_service_named("climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": mode})
    reason_txt = f" ({reason})" if reason else ""
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} HVAC {entity_id} -> {mode}{reason_txt}")
    last_hvac_cmd[entity_id] = (mode, now)


async def _set_climate_hvac_mode_guard(entity_id: str | None, mode: str, min_switch_s: float) -> None:
    if not entity_id or not ha.enabled:
        return
    prev = last_hvac_cmd.get(entity_id)
    now = time.time()
    if prev and prev[0] != mode and (now - prev[1]) < min_switch_s:
        return
    await _set_climate_hvac_mode(entity_id, mode, reason)

async def _set_input_select(entity_id: str | None, option: str) -> None:
    if not entity_id or not ha.enabled:
        return
    current = _get_state(entity_id)
    if current == option:
        return
    await ha.call_service_named("input_select", "select_option", {"entity_id": entity_id, "option": option})
    action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SELECT {entity_id} -> {option}")

async def _apply_impianto_live() -> None:
    global impianto_last_source
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return
    if cfg.get("modules_enabled", {}).get("gas_emergenza", False):
        # gas emergenza ON: non interferire con impianto
        return
    if not cfg.get("modules_enabled", {}).get("impianto", True):
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} IMPIANTO module OFF state={cfg.get('modules_enabled', {})}")
        ent = cfg.get("entities", {})
        act = cfg.get("actuators", {})
        imp = cfg.get("impianto", {})
        r4 = act.get("r4_valve_impianto_da_puffer")
        r5 = act.get("r5_valve_impianto_da_pdc")
        r31 = act.get("r31_valve_impianto_da_volano")
        r12 = act.get("r12_pump_mandata_piani")
        r11 = act.get("r11_pump_mandata_laboratorio")
        clima = ent.get("puffer_consenso_riscaldamento_piani")
        off_centralina = ent.get("off_centralina_termoregolazione")
        for z in _collect_zones(imp):
            await _set_climate_hvac_mode(z, "off", "IMPIANTO module OFF")
        await _set_pump_delayed("impianto:pump", r12, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        await _set_pump_delayed("impianto:lab_pump", r11, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        await _set_actuator(r4, False)
        await _set_actuator(r5, False)
        await _set_actuator(r31, False)
        await _set_climate_hvac_mode(clima, "off", "IMPIANTO module OFF")
        await _set_actuator(off_centralina, True)
        return

    ent = cfg.get("entities", {})
    act = cfg.get("actuators", {})

    sel = ent.get("hvac_riscaldamento_select")
    richiesta = ent.get("richiesta_heat_piani")
    clima = ent.get("puffer_consenso_riscaldamento_piani")
    off_centralina = ent.get("off_centralina_termoregolazione")
    r4 = act.get("r4_valve_impianto_da_puffer")

    imp_cfg = cfg.get("impianto", {})
    sel_state = str(_get_state(sel) or imp_cfg.get("source_mode", "AUTO") or "AUTO").strip().upper()
    richiesta_on = _state_is_on(richiesta) if richiesta else bool(imp_cfg.get("richiesta_heat"))

    pdc_ready = _state_is_on(ent.get("source_pdc_ready")) if ent.get("source_pdc_ready") else bool(imp_cfg.get("pdc_ready"))
    volano_ready = _state_is_on(ent.get("source_volano_ready")) if ent.get("source_volano_ready") else bool(imp_cfg.get("volano_ready"))
    pdc_volano_ready = pdc_ready or volano_ready
    puffer_ready = _state_is_on(ent.get("source_puffer_ready")) if ent.get("source_puffer_ready") else bool(imp_cfg.get("puffer_ready", True))

    if sel_state not in ("AUTO", "PDC", "PUFFER"):
        sel_state = "AUTO"

    t_volano = _get_num(ent.get("t_volano"))
    t_puffer = _get_num(ent.get("t_puffer"))
    vol_min = float(imp_cfg.get("volano_min_c", 35.0))
    vol_h = float(imp_cfg.get("volano_hyst_c", 2.0))
    puf_min = float(imp_cfg.get("puffer_min_c", 35.0))
    puf_h = float(imp_cfg.get("puffer_hyst_c", 2.0))

    forced_source = sel_state != "AUTO"

    # soglie temperatura con isteresi (start e hold)
    vol_ok_start = (t_volano is None) or (t_volano >= vol_min + vol_h)
    vol_ok_hold = (t_volano is None) or (t_volano > (vol_min - vol_h))
    puf_ok_start = (t_puffer is None) or (t_puffer >= puf_min + puf_h)
    puf_ok_hold = (t_puffer is None) or (t_puffer > (puf_min - puf_h))

    # Se selector AUTO o sorgente non disponibile -> fallback con priorit?
    if sel_state == "AUTO" or (
        (sel_state == "PDC" and (not pdc_volano_ready or not (vol_ok_start or (impianto_last_source == "PDC" and vol_ok_hold)))) or
        (sel_state == "PUFFER" and (not puffer_ready or not (puf_ok_start or (impianto_last_source == "PUFFER" and puf_ok_hold))))
    ):
        if pdc_volano_ready and (vol_ok_start or (impianto_last_source == "PDC" and vol_ok_hold)):
            source = "PDC"
        else:
            source = "PUFFER" if (puffer_ready and (puf_ok_start or (impianto_last_source == "PUFFER" and puf_ok_hold))) else None
    else:
        source = sel_state

    r5 = act.get("r5_valve_impianto_da_pdc")

    imp = cfg.get("impianto", {})
    cooling_blocked = set(imp.get("cooling_blocked", []))
    zones_pt = imp.get("zones_pt", [])
    zones_p1 = imp.get("zones_p1", [])
    zones_mans = imp.get("zones_mans", [])
    zones_lab = imp.get("zones_lab", [])
    zone_scala = imp.get("zone_scala") or ""
    season = str(imp.get("season_mode", "winter")).lower()

    pt_active = any(_zone_active(z, cooling_blocked) for z in zones_pt)
    p1_active = any(_zone_active(z, cooling_blocked) for z in zones_p1)
    mans_active = any(_zone_active(z, cooling_blocked) for z in zones_mans)
    lab_active = any(_zone_active(z, cooling_blocked) for z in zones_lab)
    scala_active = _zone_active(zone_scala, cooling_blocked) if zone_scala else False

    any_active = pt_active or p1_active or mans_active or lab_active or scala_active

    # Se non ci sono zone configurate, usa richiesta_on
    zones_configured = (zones_pt or zones_p1 or zones_mans or zones_lab or zone_scala)
    if richiesta is not None:
        demand_on = bool(richiesta_on)
    else:
        demand_on = (any_active if zones_configured else bool(richiesta_on))
    if season == "summer":
        demand_on = False
        impianto_heat_state["active"] = False
        impianto_heat_state["last_change"] = time.time()

    r12 = act.get("r12_pump_mandata_piani")
    r11 = act.get("r11_pump_mandata_laboratorio")
    r2 = act.get("r2_valve_comparto_mandata_imp_pt")
    r3 = act.get("r3_valve_comparto_mandata_imp_m1p")
    r1 = act.get("r1_valve_comparto_laboratorio")

    # blocco se nessuna fonte valida o troppo fredda
    # latch: se era attiva una sorgente, mantienila finch? non scende sotto min (con isteresi)
    if demand_on and source is None and impianto_last_source:
        if impianto_last_source == "PDC" and pdc_volano_ready:
            if vol_ok_hold:
                source = "PDC"
        if impianto_last_source == "PUFFER" and puffer_ready:
            if puf_ok_hold:
                source = "PUFFER"

    # Auto-heat: termostati in HEAT quando impianto ? OK (fonte valida)
    auto_heat = False
    if season == "winter":
        auto_heat = bool(source)

    heat_reason = f"IMPIANTO auto_heat={'ON' if auto_heat else 'OFF'} source={source or 'OFF'}"
    for z in _collect_zones(imp):
        await _set_climate_hvac_mode(z, "heat" if auto_heat else "off", heat_reason)

    blocked_cold = bool(demand_on and source is None)
    if not source:
        if r2:
            await _set_actuator(r2, False)
        if r3:
            await _set_actuator(r3, False)
        if r1:
            await _set_actuator(r1, False)
        if blocked_cold:
            await _force_pump_off("impianto:pump", r12)
            await _force_pump_off("impianto:lab_pump", r11)
        else:
            await _set_pump_delayed("impianto:pump", r12, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
            await _set_pump_delayed("impianto:lab_pump", r11, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        await _set_actuator(r4, False)
        await _set_actuator(r5, False)
        await _set_climate_hvac_mode(clima, "off", "IMPIANTO no source")
        await _set_actuator(off_centralina, True)
        # miscelatrice gestita solo dal suo modulo
        return

    impianto_last_source = source

    if not demand_on:
        if r2:
            await _set_actuator(r2, False)
        if r3:
            await _set_actuator(r3, False)
        if r1:
            await _set_actuator(r1, False)
        await _set_actuator(r4, False)
        await _set_actuator(r5, False)
        await _set_pump_delayed("impianto:pump", r12, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        await _set_pump_delayed("impianto:lab_pump", r11, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        await _set_climate_hvac_mode(clima, "off", "IMPIANTO no demand")
        await _set_actuator(off_centralina, True)
        # miscelatrice gestita solo dal suo modulo
        return

    # Consenso/centralina
    await _set_actuator(off_centralina, False)

    # Valvole zone (mansarda e 1P condividono R3)
    if r2:
        await _set_actuator(r2, pt_active or scala_active)
    if r3:
        await _set_actuator(r3, p1_active or mans_active or scala_active)
    if r1:
        await _set_actuator(r1, lab_active)

    # Pompa con ritardi
    await _set_pump_delayed("impianto:pump", r12, True, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
    await _set_pump_delayed("impianto:lab_pump", r11, lab_active, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))

    if source == "PDC":
        await _set_actuator(r5, True)
        await _set_actuator(r4, False)
        await _set_climate_hvac_mode(clima, "off", "IMPIANTO source=PDC")
    else:  # PUFFER
        await _set_actuator(r4, True)
        await _set_actuator(r5, False)
        await _set_climate_hvac_mode(clima, "cool", "IMPIANTO source=PUFFER")

async def _apply_gas_emergenza_live() -> None:
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return
    ent = cfg.get("entities", {})
    act = cfg.get("actuators", {})
    imp = cfg.get("impianto", {})
    gas_cfg = cfg.get("gas_emergenza", {})

    power = act.get("gas_boiler_power")
    ta = act.get("gas_boiler_ta")

    if not cfg.get("modules_enabled", {}).get("gas_emergenza", False):
        await _set_actuator(power, False)
        await _set_actuator(ta, False)
        # se impianto attivo: non toccare attuatori condivisi
        if cfg.get("modules_enabled", {}).get("impianto", True):
            return
        r2 = act.get("r2_valve_comparto_mandata_imp_pt")
        r3 = act.get("r3_valve_comparto_mandata_imp_m1p")
        r1 = act.get("r1_valve_comparto_laboratorio")
        r11 = act.get("r11_pump_mandata_laboratorio")
        r16 = act.get("r16_cmd_miscelatrice_alza")
        r17 = act.get("r17_cmd_miscelatrice_abbassa")
        if r2: await _set_actuator(r2, False)
        if r3: await _set_actuator(r3, False)
        if r1: await _set_actuator(r1, False)
        await _set_pump_delayed("gas:lab_pump", r11, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        if r16: await _set_actuator(r16, False)
        if r17: await _set_actuator(r17, False)
        # non toccare i termostati se impianto ? attivo (evita conflitti)
        if not cfg.get("modules_enabled", {}).get("impianto", True):
            for z in (gas_cfg.get("zones") or []):
                await _set_climate_hvac_mode(z, "off", "GAS module OFF")
        return

    zones = gas_cfg.get("zones", [])
    if not isinstance(zones, list):
        zones = []
    zones = [str(z).strip() for z in zones if str(z).strip()]

    if not _gas_emergenza_active():
        await _set_actuator(power, False)
        await _set_actuator(ta, False)
        # solo se impianto ? OFF possiamo spegnere i termostati gas
        if not cfg.get("modules_enabled", {}).get("impianto", True):
            for z in zones:
                await _set_climate_hvac_mode(z, "off", "GAS inactive")
        return

    cooling_blocked = set(imp.get("cooling_blocked", []))
    zones_pt = set(imp.get("zones_pt", []))
    zones_p1 = set(imp.get("zones_p1", []))
    zones_mans = set(imp.get("zones_mans", []))
    zones_lab = set(imp.get("zones_lab", []))
    zone_scala = (imp.get("zone_scala") or "").strip()

    pt_active = any(_gas_zone_demand(z, cooling_blocked) for z in zones if z in zones_pt)
    p1_active = any(_gas_zone_demand(z, cooling_blocked) for z in zones if z in zones_p1)
    mans_active = any(_gas_zone_demand(z, cooling_blocked) for z in zones if z in zones_mans)
    lab_active = any(_gas_zone_demand(z, cooling_blocked) for z in zones if z in zones_lab)
    scala_active = _gas_zone_demand(zone_scala, cooling_blocked) if zone_scala and (zone_scala in zones) else False
    demand_any = pt_active or p1_active or mans_active or lab_active or scala_active

    # In gas emergenza metti sempre i termostati in heat
    for z in zones:
        await _set_climate_hvac_mode(z, "heat", "GAS emergency")
    for z in _collect_zones(imp):
        if z not in zones:
            await _set_climate_hvac_mode(z, "off", "GAS emergency (non mappato)")
    await _set_actuator(power, bool(demand_any))
    await _set_actuator(ta, bool(demand_any))

    r2 = act.get("r2_valve_comparto_mandata_imp_pt")
    r3 = act.get("r3_valve_comparto_mandata_imp_m1p")
    r1 = act.get("r1_valve_comparto_laboratorio")
    r11 = act.get("r11_pump_mandata_laboratorio")
    r4 = act.get("r4_valve_impianto_da_puffer")
    r5 = act.get("r5_valve_impianto_da_pdc")
    r12 = act.get("r12_pump_mandata_piani")
    r16 = act.get("r16_cmd_miscelatrice_alza")
    r17 = act.get("r17_cmd_miscelatrice_abbassa")

    await _set_actuator(r4, False)
    await _set_actuator(r5, False)
    await _force_pump_off("gas:pump", r12)
    if r16:
        await _set_actuator(r16, True)
    if r17:
        await _set_actuator(r17, False)

    if not demand_any:
        if r2:
            await _set_actuator(r2, True)
        if r3:
            await _set_actuator(r3, True)
        if r1:
            await _set_actuator(r1, False)
        await _set_pump_delayed("gas:lab_pump", r11, False, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))
        return

    if r2:
        await _set_actuator(r2, True)
    if r3:
        await _set_actuator(r3, True)
    if r1:
        await _set_actuator(r1, lab_active)
    await _set_pump_delayed("gas:lab_pump", r11, lab_active, imp.get("pump_start_delay_s", 9), imp.get("pump_stop_delay_s", 0))

async def _apply_caldaia_legna_live() -> None:
    if cfg.get("runtime", {}).get("mode") != "live":
        return
    if not ha.enabled:
        return
    ent = cfg.get("entities", {})
    act = cfg.get("actuators", {})
    legna_cfg = cfg.get("caldaia_legna", {})

    power = act.get("r30_alimentazione_caldaia_legna")
    ta = act.get("r20_ta_caldaia_legna")

    enabled = cfg.get("modules_enabled", {}).get("caldaia_legna", False)
    now = time.time()
    if not enabled:
        caldaia_legna_state["last_enabled"] = False
        caldaia_legna_state["startup_deadline"] = 0.0
        if caldaia_legna_state.get("forced_off"):
            caldaia_legna_state["forced_off"] = False
            if cfg.get("caldaia_legna", {}).get("forced_off", False):
                cfg["caldaia_legna"]["forced_off"] = False
                cfg["caldaia_legna"]["startup_deadline_ts"] = 0.0
                save_config(cfg)
        await _set_actuator(power, False)
        await _set_actuator(ta, False)
        return

    if caldaia_legna_state.get("forced_off"):
        caldaia_legna_state["last_enabled"] = False
        caldaia_legna_state["startup_deadline"] = 0.0
        await _set_actuator(power, False)
        await _set_actuator(ta, False)
        return

    if not caldaia_legna_state.get("last_enabled"):
        caldaia_legna_state["last_enabled"] = True
        startup_s = float(legna_cfg.get("startup_check_s", 600.0))
        saved_deadline = float(cfg.get("caldaia_legna", {}).get("startup_deadline_ts", 0.0) or 0.0)
        if saved_deadline > now:
            caldaia_legna_state["startup_deadline"] = saved_deadline
        elif saved_deadline == 0.0:
            caldaia_legna_state["startup_deadline"] = now + max(0.0, startup_s)
            cfg["caldaia_legna"]["startup_deadline_ts"] = caldaia_legna_state["startup_deadline"]
            save_config(cfg)
        else:
            caldaia_legna_state["startup_deadline"] = saved_deadline

    t_mandata = _get_num(ent.get("t_mandata_caldaia_legna"))
    t_puffer_alto = _get_num(ent.get("t_puffer_alto"))
    min_alim = float(legna_cfg.get("temp_min_alim_c", 35.0))
    min_alim_hyst = float(legna_cfg.get("temp_min_alim_hyst_c", 5.0))
    sp_puf_alto = float(legna_cfg.get("puffer_alto_sp_c", 80.0))
    sp_puf_hyst = float(legna_cfg.get("puffer_alto_hyst_c", 3.0))
    allow_startup = now < float(caldaia_legna_state.get("startup_deadline") or 0.0)

    if not allow_startup and (t_mandata is not None) and (t_mandata < min_alim):
        caldaia_legna_state["forced_off"] = True
        if not cfg.get("caldaia_legna", {}).get("forced_off", False):
            cfg["caldaia_legna"]["forced_off"] = True
            cfg["caldaia_legna"]["startup_deadline_ts"] = 0.0
            save_config(cfg)
        await _set_actuator(power, False)
        await _set_actuator(ta, False)
        return

    if t_mandata is None:
        power_on = bool(allow_startup)
    elif allow_startup and t_mandata < min_alim:
        power_on = True
    elif t_mandata <= (min_alim - min_alim_hyst):
        power_on = False
    elif t_mandata >= min_alim:
        power_on = True
    else:
        power_on = _is_on(power)

    if t_puffer_alto is None:
        ta_on = False
    elif t_puffer_alto <= (sp_puf_alto - sp_puf_hyst):
        ta_on = True
    elif t_puffer_alto >= sp_puf_alto:
        ta_on = False
    else:
        ta_on = _is_on(ta)

    await _set_actuator(power, power_on)
    await _set_actuator(ta, ta_on)

@app.get("/api/status")
async def status():
    return JSONResponse({
        "ha_connected": bool(ha.enabled),
        "token_source": getattr(ha, "token_source", None),
        "version": APP_VERSION,
        "runtime_mode": cfg.get("runtime", {}).get("mode", "dry-run"),
    })

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        while True:
            await websocket.send_json(await _build_snapshot())
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)

@app.get("/api/actions")
async def actions(limit: int = 300):
    limit = max(10, min(int(limit), 1000))
    return JSONResponse({"items": action_log[-limit:]})


@app.get("/api/actions.txt")
async def actions_txt(limit: int = 500):
    limit = max(10, min(int(limit), 2000))
    return HTMLResponse("\n".join(action_log[-limit:]), media_type="text/plain")

@app.get("/api/assets")
async def list_assets():
    assets_dir = Path("/app/static/assets")
    if not assets_dir.exists():
        return JSONResponse({"exists": False, "files": []})
    files = sorted([p.name for p in assets_dir.glob("*") if p.is_file()])
    return JSONResponse({"exists": True, "files": files})

@app.get("/api/setpoints")
async def get_setpoints():
    return JSONResponse({
        "acs": cfg.get("acs", {}),
        "puffer": cfg.get("puffer", {}),
        "volano": cfg.get("volano", {}),
        "miscelatrice": cfg.get("miscelatrice", {}),
        "curva_climatica": cfg.get("curva_climatica", {}),
        "resistance": cfg.get("resistance", {}),
        "solare": cfg.get("solare", {}),
        "timers": cfg.get("timers", {}),
        "runtime": cfg.get("runtime", {}),
        "modules_enabled": cfg.get("modules_enabled", {}),
        "gas_emergenza": cfg.get("gas_emergenza", {}),
        "caldaia_legna": cfg.get("caldaia_legna", {}),
        "impianto": cfg.get("impianto", {}),
        "history": cfg.get("history", {}),
        "security": cfg.get("security", {}),
    })

@app.post("/api/setpoints")
async def set_setpoints(payload: dict):
    global cfg
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    cfg = apply_setpoints(cfg, payload)
    modules = cfg.get("modules_enabled", {})
    modules, changed = _apply_season_block(modules)
    if changed:
        cfg = apply_setpoints(cfg, {"modules_enabled": modules})
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES summer block (setpoints)")
    save_config(cfg)
    return JSONResponse({"ok": True})

@app.post("/api/climate_setpoint")
async def climate_setpoint(payload: dict):
    if cfg.get("runtime", {}).get("mode") != "live":
        raise HTTPException(status_code=400, detail="Runtime not live")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    entity_id = payload.get("entity_id")
    temperature = payload.get("temperature")
    if not entity_id or temperature is None:
        raise HTTPException(status_code=400, detail="Missing params")
    try:
        temperature = float(temperature)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid temperature")
    await ha.call_service_named("climate", "set_temperature", {"entity_id": entity_id, "temperature": temperature})
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} CLIMATE {entity_id} -> {temperature:.1f}")
    return JSONResponse({"ok": True})

@app.get("/api/modules")
async def get_modules():
    return JSONResponse(cfg.get("modules_enabled", {}))

@app.post("/api/modules")
async def set_modules(payload: dict, request: Request):
    global cfg
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    pin_required = cfg.get("security", {}).get("user_pin", "")
    provided = payload.get("pin", "")
    if pin_required and provided != pin_required:
        raise HTTPException(status_code=403, detail="Invalid PIN")
    modules = payload.get("modules", {})
    if not isinstance(modules, dict):
        raise HTTPException(status_code=400, detail="Invalid modules")
    modules, changed = _apply_season_block(modules)
    global last_modules_payload, last_modules_save_ts
    client = getattr(getattr(request, 'client', None), 'host', None)
    # skip if unchanged or too frequent
    if modules == cfg.get('modules_enabled', {}):
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES skip (unchanged) client={client}")
        return JSONResponse({"ok": True})
    now = time.time()
    if last_modules_payload == modules and (now - last_modules_save_ts) < 2.0:
        action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES skip (debounce) client={client}")
        return JSONResponse({"ok": True})
    cfg = apply_setpoints(cfg, {"modules_enabled": modules})
    save_config(cfg)
    last_modules_payload = modules
    last_modules_save_ts = now
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE modules")
    if changed:
        _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES summer block applied")
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES client={client} payload={modules}")
    _log_action(f"{time.strftime('%Y-%m-%d %H:%M:%S')} MODULES state={cfg.get('modules_enabled', {})}")
    return JSONResponse({"ok": True})

@app.get("/api/history")
async def history(entity_id: str, hours: int = 24):
    if not ha.enabled:
        raise HTTPException(status_code=400, detail="HA offline")
    hours = max(1, min(int(hours), 48))
    # allow only configured temp sensors with history flag
    ent_cfg = cfg.get("entities", {})
    hist_cfg = cfg.get("history", {})
    allowed = {
        "t_acs",
        "t_acs_alto",
        "t_acs_medio",
        "t_acs_basso",
        "t_puffer",
        "t_puffer_alto",
        "t_puffer_medio",
        "t_puffer_basso",
        "collettore_energy_day_kwh",
        "collettore_energy_total_kwh",
        "collettore_flow_lmin",
        "collettore_pwm_pct",
        "collettore_temp_esterna",
        "collettore_tsa1",
        "collettore_tse",
        "collettore_tsv",
        "collettore_twu",
        "t_volano",
        "t_volano_alto",
        "t_volano_basso",
        "t_solare_mandata",
        "t_esterna",
        "t_mandata_miscelata",
        "t_ritorno_miscelato",
        "miscelatrice_setpoint",
        "delta_puffer_acs",
        "delta_volano_acs",
        "delta_mandata_ritorno",
        "kp_eff",
        "t_mandata_caldaia_legna",
        "t_ritorno_caldaia_legna",
        "t_caldaia_legna",
    }
    key = None
    for k in allowed:
        if ent_cfg.get(k) == entity_id:
            key = k
            break
    if not key or not hist_cfg.get(key):
        raise HTTPException(status_code=403, detail="History disabled")

    import datetime as dt
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(hours=hours)
    path = f"history/period/{start.isoformat()}"
    params = {
        "filter_entity_id": entity_id,
        "end_time": end.isoformat(),
        "minimal_response": "1",
        "no_attributes": "1"
    }
    data = await ha.api_get(path, params=params)
    return JSONResponse({"items": data or []})

@app.get("/api/entities")
async def get_entities():
    ent = cfg.get("entities", {})
    out = {}
    for k, eid in ent.items():
        if eid:
            st = ha.states.get(eid, {})
            out[k] = {
                "entity_id": eid,
                "state": st.get("state"),
                "attributes": st.get("attributes", {}),
                "icon": entity_icon_map.get(eid)
            }
        else:
            out[k] = {"entity_id": None, "state": None, "attributes": {}, "icon": None}
    return JSONResponse(out)

@app.post("/api/entities")
async def set_entities(payload: dict):
    global cfg
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    cfg = apply_entities(cfg, payload)
    save_config(cfg)
    action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE entities")
    return JSONResponse({"ok": True})

@app.get("/api/actuators")
async def get_actuators():
    act = cfg.get("actuators", {})
    states = {}
    for k, eid in act.items():
        if eid:
            st = ha.states.get(eid, {})
            states[k] = {
                "entity_id": eid,
                "state": st.get("state"),
                "attributes": st.get("attributes", {}),
                "icon": entity_icon_map.get(eid)
            }
        else:
            states[k] = {"entity_id": None, "state": None, "attributes": {}, "icon": None}
    return JSONResponse(states)

@app.post("/api/actuators")
async def set_actuators(payload: dict):
    global cfg
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    cfg = apply_actuators(cfg, payload)
    save_config(cfg)
    action_log.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} SAVE actuators")
    return JSONResponse({"ok": True})

@app.post("/api/actuate")
async def actuate(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    entity_id = payload.get("entity_id")
    action = payload.get("action")
    manual = bool(payload.get("manual", False))
    if action not in ("on", "off"):
        raise HTTPException(status_code=400, detail="Invalid action")
    if not entity_id or not isinstance(entity_id, str):
        raise HTTPException(status_code=400, detail="Invalid entity_id")
    if not ha.enabled:
        raise HTTPException(status_code=400, detail="HA offline")
    recent_ui_actuations[entity_id] = time.time()
    if manual:
        # R8/R9/R10 restano automatici: non mettere override manuale
        act = cfg.get("actuators", {})
        r8 = act.get("r8_valve_solare_notte_low_temp")
        r9 = act.get("r9_valve_solare_normal_funz")
        r10 = act.get("r10_valve_solare_precedenza_acs")
        if entity_id in (r8, r9, r10):
            manual = False

    if manual:
        # Manuale puro in Admin: non va toccato dalla logica
        if action == "on":
            manual_overrides[entity_id] = True
        else:
            manual_overrides.pop(entity_id, None)
        # Interlock R18/R19: accendine una spegne l'altra
        act = cfg.get("actuators", {})
        r18 = act.get("r18_valve_ritorno_solare_basso")
        r19 = act.get("r19_valve_ritorno_solare_alto")
        if entity_id in (r18, r19) and action == "on":
            other = r19 if entity_id == r18 else r18
            if other:
                manual_overrides.pop(other, None)
                await ha.call_service(other, "off")
    ok = await ha.call_service(entity_id, action)
    return JSONResponse({"ok": bool(ok)})
