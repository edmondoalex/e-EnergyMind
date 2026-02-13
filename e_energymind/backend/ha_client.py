import asyncio
import json
import logging
import os
import inspect
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp

class HAClient:
    def __init__(self):
        self._token, self._base_url = self._load_auth()
        self._ws_url = self._build_ws_url(self._base_url)
        self._http_url = f"{self._base_url}/api"
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.states: Dict[str, Dict[str, Any]] = {}
        self._log = logging.getLogger("ha_client")
        self.enabled = bool(self._token)
        self.token_source = "env" if os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN") else "secret"
        self._state_cb = None

    def set_state_callback(self, callback):
        self._state_cb = callback

    def _load_auth(self) -> tuple[Optional[str], str]:
        base_url = "http://supervisor/core"
        env_token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")
        if env_token:
            self.token_source = "env"
            return env_token, base_url
        secret_candidates = [
            Path("/run/secrets/supervisor_token"),
            Path("/var/run/s6/container_environment/SUPERVISOR_TOKEN"),
            Path("/run/s6/container_environment/SUPERVISOR_TOKEN"),
            Path("/var/run/s6/container_environment/HASSIO_TOKEN"),
            Path("/run/s6/container_environment/HASSIO_TOKEN"),
        ]
        for secret_path in secret_candidates:
            if secret_path.exists():
                try:
                    self.token_source = f"secret:{secret_path}"
                    return secret_path.read_text(encoding="utf-8").strip(), base_url
                except Exception:
                    return None, base_url

        options_path = Path("/data/options.json")
        if options_path.exists():
            try:
                data = json.loads(options_path.read_text(encoding="utf-8"))
                ha_token = data.get("ha_token")
                ha_url = data.get("ha_url") or "http://homeassistant:8123"
                if isinstance(ha_token, str) and ha_token.strip():
                    self.token_source = "options"
                    return ha_token.strip(), ha_url.rstrip("/")
            except Exception:
                pass

        return None, base_url

    def _build_ws_url(self, base_url: str) -> str:
        url = base_url.rstrip("/")
        if url.startswith("https://"):
            return url.replace("https://", "wss://", 1) + "/api/websocket"
        if url.startswith("http://"):
            return url.replace("http://", "ws://", 1) + "/api/websocket"
        return "ws://homeassistant:8123/api/websocket"

    async def start(self):
        if not self._token:
            self._log.warning("Missing SUPERVISOR_TOKEN / HASSIO_TOKEN; running in standalone mode.")
            self.enabled = False
            return
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        )
        await self._connect_ws()

    async def close(self):
        if self._ws is not None:
            await self._ws.close()
        if self._session is not None:
            await self._session.close()

    async def _connect_ws(self):
        assert self._session is not None
        if self._ws is not None:
            await self._ws.close()
        self._ws = await self._session.ws_connect(self._ws_url, heartbeat=30)
        hello = await self._ws.receive_json()
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"Unexpected WS hello: {hello}")
        await self._ws.send_json({"type": "auth", "access_token": self._token})
        auth_ok = await self._ws.receive_json()
        if auth_ok.get("type") != "auth_ok":
            raise RuntimeError(f"Auth failed: {auth_ok}")
        await self._ws.send_json({"id": 1, "type": "subscribe_events", "event_type": "state_changed"})
        sub_ok = await self._ws.receive_json()
        if not sub_ok.get("success", False):
            raise RuntimeError(f"Subscribe failed: {sub_ok}")
        await self._prime_states()

    async def _prime_states(self):
        assert self._session is not None
        async with self._session.get(f"{self._http_url}/states") as r:
            r.raise_for_status()
            data = await r.json()
        for st in data:
            self.states[st["entity_id"]] = st

    async def call_service(self, entity_id: str, action: str) -> bool:
        if not self._session:
            return False
        if "." not in entity_id:
            return False
        domain, _ = entity_id.split(".", 1)
        service = "turn_on" if action == "on" else "turn_off"
        payload = {"entity_id": entity_id}
        url = f"{self._http_url}/services/{domain}/{service}"
        async with self._session.post(url, json=payload) as r:
            return r.status == 200

    async def call_service_named(self, domain: str, service: str, data: Dict[str, Any]) -> bool:
        if not self._session:
            return False
        if not domain or not service:
            return False
        payload = data or {}
        url = f"{self._http_url}/services/{domain}/{service}"
        async with self._session.post(url, json=payload) as r:
            return r.status == 200


    async def api_get(self, path: str, params: Dict[str, Any] | None = None) -> Any:
        if not self._session:
            return None
        url = f"{self._http_url}/{path.lstrip('/')}"
        async with self._session.get(url, params=params or {}) as r:
            if r.status != 200:
                return None
            return await r.json()

    async def loop(self):
        if self._ws is None:
            return
        while True:
            msg = await self._ws.receive_json()
            if msg.get("type") == "event" and msg.get("event", {}).get("event_type") == "state_changed":
                ev = msg["event"]["data"]
                ent = ev.get("entity_id")
                new_state = ev.get("new_state")
                if ent and new_state:
                    self.states[ent] = new_state
                    if self._state_cb:
                        try:
                            res = self._state_cb(ent, new_state)
                            if inspect.isawaitable(res):
                                await res
                        except Exception as exc:
                            self._log.debug("State callback error: %s", exc)

    async def run(self):
        backoff = 1
        while True:
            try:
                self._log.info("Connecting to Home Assistant WS...")
                await self._connect_ws()
                self._log.info("WS connected.")
                backoff = 1
                await self.loop()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._log.warning("WS loop error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
