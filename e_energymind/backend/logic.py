from typing import Any, Dict
import time

def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default



def _is_on_state(state: Any) -> bool:
    if state is None:
        return False
    sval = str(state).strip().lower()
    return sval in ("on", "true", "1", "yes", "heat", "heating")
def _thr_list(value: Any) -> list[float]:
    base = [1100.0, 2200.0, 3300.0]
    if not isinstance(value, (list, tuple)):
        return base
    out: list[float] = []
    for idx in range(3):
        if idx < len(value):
            out.append(_f(value[idx], base[idx]))
        else:
            out.append(base[idx])
    return out

_LAST: Dict[str, Any] = {
    "dest": None,
    "source_to_acs": None,
    "volano_to_puffer": False,
    "gas_vol_ok": False,
    "gas_puf_ok": False,
    "res_step": 0,
    "res_step_ts": 0.0
}

def _zone_active(state: Any, hvac_action: Any, cooling_blocked: bool) -> bool:
    if cooling_blocked:
        return False
    sval = str(state or "").strip().lower()
    action = str(hvac_action or "").strip().lower()
    if sval in ("off", "idle", "unavailable", "unknown"):
        return False
    return action in ("heating", "cooling") or sval in ("on", "true", "1", "yes", "heat", "heating", "cool", "cooling")

def compute_decision(cfg: Dict[str, Any], ha_states: Dict[str, Any], now: float | None = None) -> Dict[str, Any]:
    now_ts = time.time() if now is None else float(now)
    ent = cfg.get("entities", {})
    acs_cfg = cfg.get("acs", {})
    puf_cfg = cfg.get("puffer", {})
    vol_cfg = cfg.get("volano", {})
    res_cfg = cfg.get("resistance", {})
    curve_cfg = cfg.get("curva_climatica", {})
    curve_enabled = cfg.get("modules_enabled", {}).get("curva_climatica", True)
    gas_cfg = cfg.get("gas_emergenza", {})
    gas_enabled = cfg.get("modules_enabled", {}).get("gas_emergenza", False)
    legna_cfg = cfg.get("caldaia_legna", {})
    legna_enabled = cfg.get("modules_enabled", {}).get("caldaia_legna", False)

    def get_num(eid: str | None, default: float = 0.0) -> float:
        if not eid:
            return default
        st = ha_states.get(eid, {}).get("state")
        return _f(st, default)
    def get_text(eid: str | None, default: str = "") -> str:
        if not eid:
            return default
        st = ha_states.get(eid, {}).get("state")
        return default if st is None else str(st)
    def get_num_optional(eid: str | None):
        if not eid:
            return None
        st = ha_states.get(eid, {}).get("state")
        return _f(st, None)

    t_acs = get_num_optional(ent.get("t_acs"))
    if t_acs is None:
        t_acs = get_num(ent.get("t_acs_alto"), 0.0)
    t_acs_alto = get_num(ent.get("t_acs_alto"), 0.0)
    t_acs_medio = get_num(ent.get("t_acs_medio"), 0.0)
    t_acs_basso = get_num(ent.get("t_acs_basso"), 0.0)
    t_puffer = get_num_optional(ent.get("t_puffer"))
    if t_puffer is None:
        t_puffer = get_num(ent.get("t_puffer_alto"), 0.0)
    t_puffer_alto = get_num(ent.get("t_puffer_alto"), 0.0)
    t_puffer_medio = get_num(ent.get("t_puffer_medio"), 0.0)
    t_puffer_basso = get_num(ent.get("t_puffer_basso"), 0.0)
    t_volano = get_num_optional(ent.get("t_volano"))
    if t_volano is None:
        t_volano = get_num(ent.get("t_volano_alto"), 0.0)
    t_volano_alto = get_num(ent.get("t_volano_alto"), 0.0)
    t_volano_basso = get_num(ent.get("t_volano_basso"), 0.0)
    t_sol = get_num(ent.get("t_solare_mandata"), 0.0)
    col_status_code = get_text(ent.get("collettore_status_code"), "")
    col_status = get_text(ent.get("collettore_status"), "")
    col_datetime = get_text(ent.get("collettore_datetime"), "")
    col_energy_day = get_num(ent.get("collettore_energy_day_kwh"), 0.0)
    col_energy_total = get_num(ent.get("collettore_energy_total_kwh"), 0.0)
    col_flow = get_num(ent.get("collettore_flow_lmin"), 0.0)
    col_pwm = get_num(ent.get("collettore_pwm_pct"), 0.0)
    col_status2 = get_text(ent.get("collettore_status2"), "")
    col_t_ext = get_num(ent.get("collettore_temp_esterna"), None)
    col_tsa1 = get_num(ent.get("collettore_tsa1"), 0.0)
    col_tse = get_num(ent.get("collettore_tse"), 0.0)
    col_tsv = get_num(ent.get("collettore_tsv"), 0.0)
    col_twu = get_num(ent.get("collettore_twu"), 0.0)
    t_esterna = get_num(ent.get("t_esterna"), None)
    t_mandata_mix = get_num(ent.get("t_mandata_miscelata"), 0.0)
    t_ritorno_mix = get_num(ent.get("t_ritorno_miscelato"), 0.0)
    export_w = get_num(ent.get("grid_export_w"), 0.0)
    res_power_w = get_num(ent.get("resistenze_volano_power"), 0.0)
    if res_power_w < 0:
        res_power_w = 0.0
    t_mandata_legna = get_num(ent.get("t_mandata_caldaia_legna"), None)
    t_ritorno_legna = get_num(ent.get("t_ritorno_caldaia_legna"), None)
    t_caldaia_legna = get_num(ent.get("t_caldaia_legna"), None)

    if res_cfg.get("invert_export_sign"):
        export_w = -export_w

    acs_sp = float(acs_cfg.get("setpoint_c", 55.0))
    acs_off_h = float(acs_cfg.get("off_hyst_c", 1.0))
    acs_on_delta = float(acs_cfg.get("on_delta_c", 2.0))
    acs_off_delta = float(acs_cfg.get("off_hyst_c", 1.0))
    acs_ok = t_acs >= (acs_sp + acs_off_delta)
    acs_need = t_acs <= (acs_sp - acs_on_delta)

    acs_max = float(acs_cfg.get("max_c", 60.0))
    vol_max = float(vol_cfg.get("max_c", 60.0))
    puf_max = float(puf_cfg.get("max_c", 75.0))

    acs_max_hit = t_acs >= acs_max
    vol_max_hit = t_volano >= vol_max
    puf_max_hit = t_puffer >= puf_max

    puf_sp = float(puf_cfg.get("setpoint_c", 55.0))
    puf_off_h = float(puf_cfg.get("off_hyst_c", 1.0))
    puf_need = (t_puffer <= (puf_sp - puf_off_h)) and (not puf_max_hit)

    if acs_max_hit:
        dest = "OFF"
        dest_reason = f"ACS_MAX: {t_acs:.1f}°C >= {acs_max:.1f}°C"
    elif acs_need:
        dest = "ACS"
        dest_reason = f"ACS sotto target: {t_acs:.1f}°C <= {acs_sp - acs_on_delta:.1f}°C"
    elif puf_need:
        dest = "PUFFER"
        dest_reason = f"ACS ok; puffer sotto target: {t_puffer:.1f}°C < {puf_sp - puf_off_h:.1f}°C"
    else:
        dest = "OFF"
        dest_reason = "Nessuna destinazione utile."

    solar_cfg = cfg.get("solare", {})
    misc_cfg = cfg.get("miscelatrice", {})
    solar_delta_on = float(solar_cfg.get("delta_on_c", 5.0))
    solar_delta_hold = float(solar_cfg.get("delta_hold_c", 2.5))
    last_source = _LAST.get("source_to_acs")
    delta_start = float(vol_cfg.get("delta_to_acs_start_c", 5.0))
    delta_hold = float(vol_cfg.get("delta_to_acs_hold_c", 2.5))
    puf_delta_start = float(vol_cfg.get("delta_to_puffer_start_c", 5.0))
    puf_delta_hold = float(vol_cfg.get("delta_to_puffer_hold_c", 2.5))
    vol_min_puf = float(vol_cfg.get("min_to_puffer_c", 55.0))
    vol_h_puf = float(vol_cfg.get("hyst_to_puffer_c", 2.0))
    puf_to_acs_start = float(puf_cfg.get("delta_to_acs_start_c", 3.0))
    puf_to_acs_hold = float(puf_cfg.get("delta_to_acs_hold_c", 1.5))
    vol_min_acs = float(vol_cfg.get("min_to_acs_c", 50.0))
    vol_h_acs = float(vol_cfg.get("hyst_to_acs_c", 5.0))
    puf_min_acs = float(puf_cfg.get("min_to_acs_c", 60.0))
    puf_h_acs = float(puf_cfg.get("hyst_to_acs_c", 5.0))
    last_vol_to_puf = bool(_LAST.get("volano_to_puffer"))

    if dest == "ACS" and (t_sol >= t_acs + solar_delta_on) and (not acs_max_hit):
        source_to_acs = "SOLAR"
        source_reason = f"T_SOL {t_sol:.1f}°C >= T_ACS+delta {t_acs + solar_delta_on:.1f}°C"
    elif dest == "ACS" and last_source == "SOLAR" and (t_sol >= t_acs + solar_delta_hold) and (not acs_max_hit):
        source_to_acs = "SOLAR"
        source_reason = f"T_SOL {t_sol:.1f}°C >= T_ACS+delta_hold {t_acs + solar_delta_hold:.1f}°C"
    elif dest == "ACS" and (t_volano >= t_acs + delta_start) and (not vol_max_hit) and (t_volano >= vol_min_acs + vol_h_acs):
        source_to_acs = "VOLANO"
        source_reason = f"T_VOL {t_volano:.1f}°C >= T_ACS+{delta_start:.1f}°C ({t_acs + delta_start:.1f}°C)"
    elif dest == "ACS" and last_source == "VOLANO" and (t_volano >= t_acs + delta_hold) and (not vol_max_hit) and (t_volano >= vol_min_acs):
        source_to_acs = "VOLANO"
        source_reason = f"T_VOL {t_volano:.1f}°C >= T_ACS+{delta_hold:.1f}°C ({t_acs + delta_hold:.1f}°C)"
    elif dest == "ACS" and (t_puffer >= t_acs + puf_to_acs_start) and (t_puffer >= puf_min_acs + puf_h_acs):
        source_to_acs = "PUFFER"
        source_reason = f"T_PUF {t_puffer:.1f}°C >= T_ACS+delta {t_acs + puf_to_acs_start:.1f}°C"
    elif dest == "ACS" and last_source == "PUFFER" and (t_puffer >= t_acs + puf_to_acs_hold) and (t_puffer >= puf_min_acs):
        source_to_acs = "PUFFER"
        source_reason = f"T_PUF {t_puffer:.1f}°C >= T_ACS+delta_hold {t_acs + puf_to_acs_hold:.1f}°C"
    else:
        source_to_acs = "OFF"
        source_reason = "Nessuna sorgente selezionata (v0.1)."

    volano_to_puffer = False
    if dest == "PUFFER" and (not vol_max_hit):
        if (t_volano >= t_puffer + puf_delta_start) and (t_volano >= vol_min_puf + vol_h_puf):
            volano_to_puffer = True
        elif last_vol_to_puf and (t_volano >= t_puffer + puf_delta_hold) and (t_volano >= vol_min_puf):
            volano_to_puffer = True

    desired_step = 0
    if dest in ("ACS", "PUFFER") and (not vol_max_hit) and res_cfg.get("enabled", True):
        thr = _thr_list(res_cfg.get("thresholds_w", [1100, 2200, 3300]))
        if export_w >= thr[2]:
            desired_step = 3
        elif export_w >= thr[1]:
            desired_step = 2
        elif export_w >= thr[0]:
            desired_step = 1

    off_thr = float(res_cfg.get("off_threshold_w", 0.0))
    step_up_delay = int(_f(res_cfg.get("step_up_delay_s", 10), 10))
    off_delay = int(_f(res_cfg.get("off_delay_s", 5), 5))
    last_step = int(_LAST.get("res_step", 0) or 0)
    last_step_ts = float(_LAST.get("res_step_ts", 0.0) or 0.0)
    if export_w <= off_thr:
        step = 0
    else:
        if desired_step > last_step:
            if now_ts - last_step_ts >= step_up_delay:
                step = min(desired_step, last_step + 1)
            else:
                step = last_step
        else:
            # do not decrease step while export is positive
            step = last_step

    charge_buffer = "RESISTANCE" if step > 0 else "OFF"
    if vol_max_hit:
        charge_reason = f"VOLANO_MAX: {t_volano:.1f}°C >= {vol_max:.1f}°C"
    elif dest == "OFF":
        charge_reason = dest_reason
    elif export_w <= off_thr:
        charge_reason = f"Export {export_w:.0f}W <= OFF {off_thr:.0f}W | off_delay {off_delay}s | step_up_delay {step_up_delay}s"
    else:
        charge_reason = f"Export {export_w:.0f}W | off_delay {off_delay}s | step_up_delay {step_up_delay}s"

    _LAST["dest"] = dest
    _LAST["source_to_acs"] = source_to_acs
    _LAST["volano_to_puffer"] = volano_to_puffer
    if step != last_step:
        _LAST["res_step_ts"] = now_ts
    _LAST["res_step"] = step

    timers_cfg = cfg.get("timers", {})
    vta_start = int(timers_cfg.get("volano_to_acs_start_s", 5))
    vta_stop = int(timers_cfg.get("volano_to_acs_stop_s", 2))
    vtp_start = int(timers_cfg.get("volano_to_puffer_start_s", 5))
    vtp_stop = int(timers_cfg.get("volano_to_puffer_stop_s", 2))
    volano_to_acs_reason = (
        f"Dest={dest} | ACS_MAX={'SI' if acs_max_hit else 'NO'} | "
        f"Source={source_to_acs} | T_VOL {t_volano:.1f}C | T_ACS {t_acs:.1f}C | "
        f"d_start {delta_start:.1f}C / d_hold {delta_hold:.1f}C | "
        f"Min {vol_min_acs:.1f}C (+{vol_h_acs:.1f}C) | "
        f"Delay start {vta_start}s / stop {vta_stop}s | "
        f"LastSource={last_source or 'None'}"
    )
    volano_to_puffer_reason = (
        f"Dest={dest} | VOL_MAX={'SI' if vol_max_hit else 'NO'} | "
        f"T_VOL {t_volano:.1f}C | T_PUF {t_puffer:.1f}C | "
        f"d_start {puf_delta_start:.1f}C / d_hold {puf_delta_hold:.1f}C | "
        f"Min {vol_min_puf:.1f}C (+{vol_h_puf:.1f}C) | "
        f"Delay start {vtp_start}s / stop {vtp_stop}s | "
        f"LastVolToPuf={'SI' if last_vol_to_puf else 'NO'}"
    )

    ent_cfg = cfg.get("entities", {})
    imp_cfg = cfg.get("impianto", {})
    sel_eid = ent_cfg.get("hvac_riscaldamento_select")
    req_eid = ent_cfg.get("richiesta_heat_piani")
    pdc_eid = ent_cfg.get("source_pdc_ready")
    vol_eid = ent_cfg.get("source_volano_ready")

    sel_state = ha_states.get(sel_eid, {}).get("state") if sel_eid else imp_cfg.get("source_mode", "AUTO")
    req_state = ha_states.get(req_eid, {}).get("state") if req_eid else ("on" if imp_cfg.get("richiesta_heat") else "off")
    pdc_ready = _is_on_state(ha_states.get(pdc_eid, {}).get("state") if pdc_eid else ("on" if imp_cfg.get("pdc_ready") else "off"))
    vol_ready = _is_on_state(ha_states.get(vol_eid, {}).get("state") if vol_eid else ("on" if imp_cfg.get("volano_ready") else "off"))
    pdc_vol_ready = pdc_ready or vol_ready
    puf_ready = _is_on_state(ha_states.get(ent_cfg.get("source_puffer_ready"), {}).get("state")) if ent_cfg.get("source_puffer_ready") else bool(imp_cfg.get("puffer_ready", True))
    # richiesta: se esiste un'entitÃ , usa quella; altrimenti deriva dai termostati
    zones_pt = imp_cfg.get("zones_pt", []) or []
    zones_p1 = imp_cfg.get("zones_p1", []) or []
    zones_mans = imp_cfg.get("zones_mans", []) or []
    zones_lab = imp_cfg.get("zones_lab", []) or []
    zone_scala = imp_cfg.get("zone_scala") or ""
    zones_configured = bool(zones_pt or zones_p1 or zones_mans or zones_lab or zone_scala)
    cooling_blocked = set(imp_cfg.get("cooling_blocked", []))
    if req_eid:
        req_on = _is_on_state(req_state)
    else:
        def _is_zone_on(eid: str) -> bool:
            st = ha_states.get(eid, {})
            return _zone_active(st.get("state"), st.get("attributes", {}).get("hvac_action"), eid in cooling_blocked)
        any_active = any(_is_zone_on(z) for z in (zones_pt + zones_p1 + zones_mans + zones_lab + ([zone_scala] if zone_scala else [])))
        req_on = any_active if zones_configured else bool(imp_cfg.get("richiesta_heat"))
    season_mode = str(imp_cfg.get("season_mode", "winter")).lower()
    if season_mode == "summer":
        req_on = False
    sel_norm = str(sel_state or "AUTO").strip().upper()
    vol_min = float(imp_cfg.get("volano_min_c", 35.0))
    vol_h = float(imp_cfg.get("volano_hyst_c", 2.0))
    puf_min = float(imp_cfg.get("puffer_min_c", 35.0))
    puf_h = float(imp_cfg.get("puffer_hyst_c", 2.0))
    vol_ok = t_volano >= (vol_min + vol_h)
    puf_ok = t_puffer >= puf_min

    if sel_norm not in ("AUTO", "PDC", "PUFFER"):
        sel_norm = "AUTO"
    if sel_norm == "AUTO" or (
        (sel_norm == "PDC" and (not pdc_vol_ready or not vol_ok)) or
        (sel_norm == "PUFFER" and (not puf_ready or not puf_ok))
    ):
        if pdc_vol_ready and vol_ok:
            source = "PDC"
        else:
            source = "PUFFER" if (puf_ready and puf_ok) else "OFF"
    else:
        source = sel_norm if ((sel_norm == "PDC" and vol_ok) or (sel_norm == "PUFFER" and puf_ok)) else "OFF"
    if not req_on:
        source = "OFF"

    def _float_list(val, default_list):
        if isinstance(val, (list, tuple)):
            out = []
            for v in val:
                try:
                    out.append(float(v))
                except Exception:
                    continue
            if out:
                return out
        return list(default_list)

    def _interp_curve(x_val, xs, ys):
        n = len(xs)
        if n == 0 or len(ys) != n:
            return None
        x_min = min(xs)
        x_max = max(xs)
        if x_val <= x_min:
            for i in range(n):
                if xs[i] == x_min:
                    return ys[i]
            return ys[0]
        if x_val >= x_max:
            for i in range(n):
                if xs[i] == x_max:
                    return ys[i]
            return ys[-1]
        for i in range(n - 1):
            xi = xs[i]
            xj = xs[i + 1]
            yi = ys[i]
            yj = ys[i + 1]
            if (xi <= x_val <= xj) or (xj <= x_val <= xi):
                if xj == xi:
                    return yi
                return yi + ((yj - yi) * ((x_val - xi) / (xj - xi)))
        return ys[0]

    default_x = [-15, -11.25, -7.5, -3.75, 0, 3.75, 7.5, 11.25, 15]
    default_y = [60, 57.6, 55, 52.6, 50, 47.6, 45, 42.6, 40]
    curve_x = _float_list(curve_cfg.get("x"), default_x)
    curve_y = _float_list(curve_cfg.get("y"), default_y)
    if len(curve_x) != len(curve_y) or len(curve_x) < 2:
        curve_x = list(default_x)
        curve_y = list(default_y)
    curve_slope = float(curve_cfg.get("slope", 0.0))
    curve_offset = float(curve_cfg.get("offset", 0.0))
    curve_min = float(curve_cfg.get("min_c", 40.0))
    curve_max = float(curve_cfg.get("max_c", 60.0))

    curve_base = None
    curve_setpoint = None
    if curve_enabled and t_esterna is not None:
        curve_base = _interp_curve(float(t_esterna), curve_x, curve_y)
        if curve_base is not None:
            y_avg = sum(curve_y) / len(curve_y)
            mod = y_avg + (1.0 + curve_slope) * (curve_base - y_avg) + curve_offset
            curve_setpoint = max(curve_min, min(curve_max, mod))

    mix_sp = get_num(ent.get("miscelatrice_setpoint"), float(misc_cfg.get("setpoint_c", 45.0)))
    if curve_enabled and curve_setpoint is not None:
        mix_sp = float(curve_setpoint)
    mix_h = float(misc_cfg.get("hyst_c", 0.5))
    mix_dt_ref = float(misc_cfg.get("dt_ref_c", 10.0))
    mix_dt_min_f = float(misc_cfg.get("dt_min_factor", 0.6))
    mix_dt_max_f = float(misc_cfg.get("dt_max_factor", 1.4))
    mix_dt = max(0.0, t_mandata_mix - t_ritorno_mix)
    mix_kp_eff = float(misc_cfg.get("kp", 2.0))
    if mix_dt_ref > 0:
        mix_kp_eff = mix_kp_eff * max(mix_dt_min_f, min(mix_dt_max_f, mix_dt / mix_dt_ref))
    mix_enabled = cfg.get("modules_enabled", {}).get("miscelatrice", True)
    mix_action = "STOP"
    mix_reason = "Miscelatrice non attiva."
    mix_delay_info = f"pause {int(misc_cfg.get('pause_s', 5))}s | min_imp {int(misc_cfg.get('min_imp_s', 1))}s | max_imp {int(misc_cfg.get('max_imp_s', 8))}s"
    if mix_enabled:
        if cfg.get("modules_enabled", {}).get("gas_emergenza", False):
            mix_action = "ALZA"
            mix_reason = f"Gas attivo: miscelatrice ALZA fissa. | {mix_delay_info}"
        else:
            err = mix_sp - t_mandata_mix
            if abs(err) <= mix_h:
                mix_reason = f"Delta entro isteresi. | {mix_delay_info}"
            elif err > 0:
                mix_action = "ALZA"
                mix_reason = f"T_MAND {t_mandata_mix:.1f}°C < SP {mix_sp:.1f}°C | dT {mix_dt:.1f}°C | KpEff {mix_kp_eff:.2f} | {mix_delay_info}"
            else:
                mix_action = "ABBASSA"
                mix_reason = f"T_MAND {t_mandata_mix:.1f}°C > SP {mix_sp:.1f}°C | dT {mix_dt:.1f}°C | KpEff {mix_kp_eff:.2f} | {mix_delay_info}"

    gas_enabled = cfg.get("modules_enabled", {}).get("gas_emergenza", False)
    blocked_cold = req_on and (source == "OFF")
    imp_active = req_on and (source != "OFF") and (not blocked_cold) and (not gas_enabled)
    miscelatrice_on = imp_active and cfg.get("modules_enabled", {}).get("miscelatrice", True)
    if not miscelatrice_on:
        mix_action = "STOP"
        if cfg.get("modules_enabled", {}).get("gas_emergenza", False):
            mix_reason = f"Impianto inattivo. Alza fisso per caldaia a GAS emergenza. | {mix_delay_info}"
        else:
            mix_reason = f"Impianto inattivo. | {mix_delay_info}"

    pump_start_delay = int(imp_cfg.get("pump_start_delay_s", 9))
    pump_stop_delay = int(imp_cfg.get("pump_stop_delay_s", 0))
    auto_heat_min_on = int(imp_cfg.get("auto_heat_min_on_s", 60))
    auto_heat_min_off = int(imp_cfg.get("auto_heat_min_off_s", 60))
    impianto_delay_info = f"pump_start {pump_start_delay}s | pump_stop {pump_stop_delay}s | auto_heat_on {auto_heat_min_on}s | auto_heat_off {auto_heat_min_off}s"

    if season_mode == "summer":
        impianto_reason = "Estate: riscaldamento bloccato."
    elif gas_enabled:
        impianto_reason = "Gas emergenza attivo: impianto inattivo."
    elif blocked_cold:
        impianto_reason = "Bloccato: nessuna fonte disponibile o troppo fredda."
    else:
        impianto_reason = (
            f"Richiesta={ 'ON' if req_on else 'OFF' } | Sel={sel_norm} | "
        f"PDC/VOL={'ON' if pdc_vol_ready else 'OFF'} "
        f"PUF={'ON' if puf_ready else 'OFF'} "
        f"Source={source} "
        f"| Miscelatrice={'ON' if miscelatrice_on else 'OFF'}"
        )
    impianto_reason = f"{impianto_reason} | {impianto_delay_info}"

    cooling_blocked = set(imp_cfg.get("cooling_blocked", []))
    gas_zones = gas_cfg.get("zones", []) if isinstance(gas_cfg.get("zones"), list) else []
    gas_zones = [str(z).strip() for z in gas_zones if str(z).strip()]
    zones_pt = set(imp_cfg.get("zones_pt", []))
    zones_p1 = set(imp_cfg.get("zones_p1", []))
    zones_mans = set(imp_cfg.get("zones_mans", []))
    zones_lab = set(imp_cfg.get("zones_lab", []))
    zone_scala = (imp_cfg.get("zone_scala") or "").strip()
    gas_active_any = False
    gas_pt = gas_p1 = gas_mans = gas_lab = gas_scala = False
    for z in gas_zones:
        st = ha_states.get(z, {})
        is_active = _zone_active(st.get("state"), st.get("attributes", {}).get("hvac_action"), z in cooling_blocked)
        gas_active_any = gas_active_any or is_active
        if z == zone_scala:
            gas_scala = gas_scala or is_active
        if z in zones_pt:
            gas_pt = gas_pt or is_active
        if z in zones_p1:
            gas_p1 = gas_p1 or is_active
        if z in zones_mans:
            gas_mans = gas_mans or is_active
        if z in zones_lab:
            gas_lab = gas_lab or is_active

    gas_vol_min = float(gas_cfg.get("volano_min_c", 35.0))
    gas_vol_h = float(gas_cfg.get("volano_hyst_c", 2.0))
    gas_puf_min = float(gas_cfg.get("puffer_min_c", 35.0))
    gas_puf_h = float(gas_cfg.get("puffer_hyst_c", 2.0))
    gas_vol_prev = bool(_LAST.get("gas_vol_ok"))
    gas_puf_prev = bool(_LAST.get("gas_puf_ok"))
    if t_volano is None:
        gas_vol_ok = True
    else:
        gas_vol_ok = t_volano > gas_vol_min if gas_vol_prev else t_volano >= (gas_vol_min + gas_vol_h)
    if t_puffer is None:
        gas_puf_ok = True
    else:
        gas_puf_ok = t_puffer > gas_puf_min if gas_puf_prev else t_puffer >= (gas_puf_min + gas_puf_h)
    _LAST["gas_vol_ok"] = gas_vol_ok
    _LAST["gas_puf_ok"] = gas_puf_ok
    gas_need = bool(gas_enabled and (not (gas_vol_ok or gas_puf_ok)))
    gas_reason = "Modulo gas OFF."
    if gas_enabled:
        if gas_need:
            gas_reason = f"Gas attivo: domanda={'ON' if gas_active_any else 'OFF'} | VOL_OK={gas_vol_ok} PUF_OK={gas_puf_ok}"
        else:
            gas_reason = "Gas standby: fonte principale disponibile."
    gas_reason = f"{gas_reason} | min_on {int(gas_cfg.get('min_on_s', 120))}s | min_off {int(gas_cfg.get('min_off_s', 120))}s"

    legna_min = float(legna_cfg.get("temp_min_alim_c", 35.0))
    legna_min_hyst = float(legna_cfg.get("temp_min_alim_hyst_c", 5.0))
    legna_sp_puf = float(legna_cfg.get("puffer_alto_sp_c", 80.0))
    legna_puf_hyst = float(legna_cfg.get("puffer_alto_hyst_c", 3.0))
    legna_startup_s = int(legna_cfg.get("startup_check_s", 600))
    legna_forced_off = bool(legna_cfg.get("forced_off", False))
    if not legna_enabled:
        legna_reason = "Modulo legna OFF."
        legna_power = False
        legna_ta = False
    elif legna_forced_off:
        legna_reason = "Timer scaduto: modulo inattivo."
        legna_power = False
        legna_ta = False
    else:
        if t_mandata_legna is None:
            legna_reason = f"Sonda mandata assente. Min {legna_min:.1f}C"
            legna_power = False
        elif t_mandata_legna < legna_min:
            legna_reason = f"Mandata bassa: {t_mandata_legna:.1f}C < {legna_min:.1f}C"
            legna_power = False
        else:
            legna_reason = f"Mandata ok: {t_mandata_legna:.1f}C >= {legna_min:.1f}C"
            legna_power = True
        legna_ta = bool(t_puffer_alto < legna_sp_puf) if t_puffer_alto is not None else False
    legna_reason = f"{legna_reason} | startup_check {legna_startup_s}s"

    return {
        "inputs": {
            "t_acs": t_acs,
            "t_acs_alto": t_acs_alto,
            "t_acs_medio": t_acs_medio,
            "t_acs_basso": t_acs_basso,
            "t_puffer": t_puffer,
            "t_puffer_alto": t_puffer_alto,
            "t_puffer_medio": t_puffer_medio,
            "t_puffer_basso": t_puffer_basso,
            "t_volano": t_volano,
            "t_volano_alto": t_volano_alto,
            "t_volano_basso": t_volano_basso,
            "t_solare_mandata": t_sol,
            "collettore_status_code": col_status_code,
            "collettore_status": col_status,
            "collettore_datetime": col_datetime,
            "collettore_energy_day_kwh": col_energy_day,
            "collettore_energy_total_kwh": col_energy_total,
            "collettore_flow_lmin": col_flow,
            "collettore_pwm_pct": col_pwm,
            "collettore_status2": col_status2,
            "collettore_temp_esterna": col_t_ext,
            "collettore_tsa1": col_tsa1,
            "collettore_tse": col_tse,
            "collettore_tsv": col_tsv,
            "collettore_twu": col_twu,
            "t_esterna": t_esterna,
            "t_mandata_miscelata": t_mandata_mix,
            "t_ritorno_miscelato": t_ritorno_mix,
            "grid_export_w": export_w,
            "resistenze_volano_power": res_power_w,
            "t_mandata_caldaia_legna": t_mandata_legna,
            "t_ritorno_caldaia_legna": t_ritorno_legna,
            "t_caldaia_legna": t_caldaia_legna
        },
        "computed": {
            "acs_sp": acs_sp,
            "acs_ok": acs_ok,
            "acs_need": acs_need,
            "dest": dest,
            "dest_reason": dest_reason,
            "source_to_acs": source_to_acs,
            "source_reason": source_reason,
            "charge_buffer": charge_buffer,
            "charge_reason": charge_reason,
            "resistance_step": step,
            "flags": {
                "volano_to_acs": source_to_acs == "VOLANO",
                "puffer_to_acs": source_to_acs == "PUFFER",
                "solare_to_acs": source_to_acs == "SOLAR",
                "volano_to_puffer": volano_to_puffer
            },
            "impianto": {
                "source": source,
                "richiesta": req_on,
                "miscelatrice": miscelatrice_on,
                "pdc_ready": pdc_vol_ready,
                "volano_ready": vol_ready,
                "puffer_ready": puf_ready,
                "volano_temp_ok": vol_ok,
                "puffer_temp_ok": puf_ok,
                "blocked_cold": blocked_cold,
                "reason": impianto_reason,
                "selector": sel_norm
            },
            "miscelatrice": {
                "enabled": mix_enabled,
                "setpoint": mix_sp,
                "hyst": mix_h,
                "t_mandata": t_mandata_mix,
                "t_ritorno": t_ritorno_mix,
                "delta_tr": mix_dt,
                "kp_eff": mix_kp_eff,
                "action": mix_action,
                "reason": mix_reason
            },
            "curva_climatica": {
                "enabled": curve_enabled,
                "t_ext": t_esterna,
                "base": curve_base,
                "setpoint": curve_setpoint,
                "slope": curve_slope,
                "offset": curve_offset,
                "min_c": curve_min,
                "max_c": curve_max,
                "x": curve_x,
                "y": curve_y
            },
            "gas_emergenza": {
                "enabled": gas_enabled,
                "need": gas_need,
                "vol_ok": gas_vol_ok,
                "puf_ok": gas_puf_ok,
                "demand": gas_active_any,
                "pt": gas_pt,
                "p1": gas_p1,
                "mans": gas_mans,
                "lab": gas_lab,
                "scala": gas_scala
            },
        "caldaia_legna": {
                "enabled": legna_enabled,
                "power": legna_power,
                "ta": legna_ta,
                "t_mandata": t_mandata_legna,
                "t_puffer_alto": t_puffer_alto,
                "min_alim": legna_min,
                "min_alim_hyst": legna_min_hyst,
                "sp_puffer_alto": legna_sp_puf,
                "puffer_hyst": legna_puf_hyst,
                "reason": legna_reason
            },
            "module_reasons": {
                "solare": (
                    f"{source_reason} | T_SOL {t_sol:.1f}C | T_ACS {t_acs:.1f}C | d_on {solar_delta_on:.1f}C / d_hold {solar_delta_hold:.1f}C | pv_debounce {int(solar_cfg.get('pv_debounce_s', 300))}s"
                    if source_to_acs == "SOLAR"
                    else f"Solare non attivo. T_SOL {t_sol:.1f}C | T_ACS {t_acs:.1f}C | d_on {solar_delta_on:.1f}C / d_hold {solar_delta_hold:.1f}C | pv_debounce {int(solar_cfg.get('pv_debounce_s', 300))}s"
                ),
                "volano_to_acs": (
                    f"{volano_to_acs_reason}"
                    if source_to_acs == "VOLANO"
                    else f"Volano -> ACS non attivo. {volano_to_acs_reason}"
                ),
                "puffer_to_acs": (
                    f"{source_reason} | T_PUF {t_puffer:.1f}C | T_ACS {t_acs:.1f}C | d_start {puf_to_acs_start:.1f}C / d_hold {puf_to_acs_hold:.1f}C | Min {puf_min_acs:.1f}C (+{puf_h_acs:.1f}C)"
                    if source_to_acs == "PUFFER"
                    else f"Puffer -> ACS non attivo. T_PUF {t_puffer:.1f}C | T_ACS {t_acs:.1f}C | d_start {puf_to_acs_start:.1f}C / d_hold {puf_to_acs_hold:.1f}C | Min {puf_min_acs:.1f}C (+{puf_h_acs:.1f}C)"
                ),
                "volano_to_puffer": (
                    f"{volano_to_puffer_reason}"
                    if volano_to_puffer
                    else f"Volano -> Puffer non attivo. {volano_to_puffer_reason}"
                ),
                "curva_climatica": (
                    f"T_EXT {t_esterna:.1f}C -> SP {curve_setpoint:.1f}C"
                    if curve_enabled and curve_setpoint is not None and t_esterna is not None
                    else "Curva climatica non attiva o senza T_EXT."
                ),
                "resistenze_volano": f"{charge_reason} | Export {export_w:.0f}W",
                "impianto": impianto_reason,
                "gas_emergenza": gas_reason,
                "caldaia_legna": legna_reason,
                "miscelatrice": mix_reason
            },
            "state": {
                "last_dest": _LAST.get("dest"),
                "last_source_to_acs": _LAST.get("source_to_acs")
            },
            "safety": {
                "acs_max_hit": acs_max_hit,
                "volano_max_hit": vol_max_hit,
                "puffer_max_hit": puf_max_hit
            }
        }
    }

