from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt


@dataclass(frozen=True)
class MqttStatus:
    connected: bool
    last_error: str | None


class MqttClient:
    def __init__(self, *, host: str, port: int, username: str, password: str, client_id: str):
        self._host = host
        self._port = port
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)

        self._lock = threading.Lock()
        self._connected = False
        self._last_error: str | None = None

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        with self._lock:
            self._connected = True
            self._last_error = None

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        with self._lock:
            self._connected = False
            if getattr(reason_code, "value", reason_code) != 0:
                self._last_error = f"disconnect reason_code={reason_code}"

    def connect(self) -> None:
        try:
            self._client.connect(self._host, self._port, keepalive=30)
            self._client.loop_start()
        except Exception as e:
            with self._lock:
                self._connected = False
                self._last_error = str(e)

    def disconnect(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            with self._lock:
                self._connected = False

    def status(self) -> MqttStatus:
        with self._lock:
            return MqttStatus(connected=self._connected, last_error=self._last_error)

    def publish(self, topic: str, payload: Any, *, retain: bool = False, qos: int = 0) -> None:
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False)
        else:
            data = str(payload)
        self._client.publish(topic, data, qos=qos, retain=retain)
