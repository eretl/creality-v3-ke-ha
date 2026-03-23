"""API clients for Creality Ender-3 V3 KE.

Field names from live firmware dump (Ender3V3KE, model F005):
  TotalLayer        — total layers (capital T)
  layer             — current layer
  bedTemp0          — bed temp string "50.010000"
  targetBedTemp0    — bed target int
  nozzleTemp        — nozzle temp string "220.160000"
  targetNozzleTemp  — nozzle target int
  printProgress     — 0-100
  printJobTime      — elapsed seconds
  printLeftTime     — remaining seconds
  printFileName     — full path
  modelFanPct       — part fan 0-100 %
  curFeedratePct    — print speed %
  curFlowratePct    — flow rate %
  state             — numeric 0=idle 1=printing 2=paused 3=complete 4=error
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import (
    KEY_BED_TEMP, KEY_BED_TARGET,
    KEY_EXTRUDER_TEMP, KEY_EXTRUDER_TARGET,
    KEY_FAN_SPEED, KEY_FILENAME, KEY_FLOW_RATE,
    KEY_LAYER_CURRENT, KEY_LAYER_TOTAL,
    KEY_ONLINE, KEY_PRINT_SPEED,
    KEY_PRINT_TIME, KEY_PRINT_TIME_LEFT,
    KEY_PROGRESS, KEY_RAW_DATA, KEY_STATUS,
)

_LOGGER = logging.getLogger(__name__)
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)
WS_CONNECT_TIMEOUT = 8
WS_MESSAGE_TIMEOUT = 15
WS_MAX_FRAMES = 20


def _first(*candidates, default=None):
    for c in candidates:
        if c is not None:
            return c
    return default


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _unwrap_frame(data: dict) -> dict:
    merged = dict(data)
    params = data.get("params")
    if isinstance(params, dict):
        merged.update(params)
    return merged


_STATUS_MAP: dict[str, str] = {
    "0": "idle",      "1": "printing", "2": "paused",
    "3": "complete",  "4": "error",    "5": "error",
    "IDLE": "idle",   "STANDBY": "idle",
    "PRINTING": "printing",
    "PAUSED": "paused", "PAUSE": "paused",
    "COMPLETE": "complete", "COMPLETED": "complete",
    "FINISH": "complete",   "FINISHED": "complete",
    "ERROR": "error",       "FAILED": "error",
    "STOP": "idle",         "STOPPED": "idle",
    "CANCEL": "idle",       "CANCELLED": "idle",
}


class CrealityWebSocketAPI:
    def __init__(self, host: str, port: int,
                 bed_offset: float = 10.0, nozzle_offset: float = 0.0) -> None:
        self._url = f"ws://{host}:{port}"
        self._bed_offset = bed_offset
        self._nozzle_offset = nozzle_offset
        self._cache: dict = {}

    async def async_test_connection(self) -> bool:
        try:
            import websockets
            async with asyncio.timeout(WS_CONNECT_TIMEOUT + WS_MESSAGE_TIMEOUT):
                async with websockets.connect(
                    self._url, open_timeout=WS_CONNECT_TIMEOUT, ping_interval=None
                ) as ws:
                    try:
                        async with asyncio.timeout(WS_MESSAGE_TIMEOUT):
                            await ws.recv()
                        return True
                    except asyncio.TimeoutError:
                        return True
        except Exception as exc:
            _LOGGER.debug("WS test failed: %s", exc)
            return False

    async def async_get_data(self) -> dict:
        import websockets
        raw: dict = {}
        frames_read = 0
        try:
            async with asyncio.timeout(WS_CONNECT_TIMEOUT + WS_MESSAGE_TIMEOUT):
                async with websockets.connect(
                    self._url, open_timeout=WS_CONNECT_TIMEOUT,
                    ping_interval=None, close_timeout=2,
                ) as ws:
                    deadline = asyncio.get_event_loop().time() + WS_MESSAGE_TIMEOUT
                    while asyncio.get_event_loop().time() < deadline and frames_read < WS_MAX_FRAMES:
                        remaining = deadline - asyncio.get_event_loop().time()
                        if remaining <= 0:
                            break
                        try:
                            async with asyncio.timeout(remaining):
                                msg = await ws.recv()
                            frames_read += 1
                            frame = json.loads(msg)
                            if isinstance(frame, dict):
                                raw.update(_unwrap_frame(frame))
                        except asyncio.TimeoutError:
                            break
                        except (json.JSONDecodeError, ValueError):
                            pass
        except Exception as exc:
            if not raw and not self._cache:
                raise RuntimeError(f"No data from {self._url}: {exc}") from exc
            _LOGGER.warning("WS read error (using cache): %s", exc)

        if raw:
            _LOGGER.debug("WS %d frames, keys: %s", frames_read, sorted(raw.keys()))
            self._cache.update(raw)

        return self._normalise(self._cache)

    def _normalise(self, r: dict) -> dict:
        # Status
        raw_status = _first(r.get("state"), r.get("deviceState"),
                            r.get("printStatus"), r.get("status"), default=0)
        status = _STATUS_MAP.get(str(raw_status).upper(), str(raw_status).lower())

        # Temperatures — apply user-configurable offsets
        nozzle_temp = round(
            _f(_first(r.get("nozzleTemp"), r.get("hotendTemp"),
                      r.get("tempNozzle"), default=0)) + self._nozzle_offset, 1
        )
        nozzle_target = round(_f(_first(
            r.get("targetNozzleTemp"), r.get("nozzleTargetTemp"),
            r.get("nozzleTempTarget"), default=0)), 1)

        bed_temp = round(
            _f(_first(r.get("bedTemp0"), r.get("bedTemp"),
                      r.get("hotbedTemp"), r.get("tempBed"), default=0)) + self._bed_offset, 1
        )
        bed_target = round(
            _f(_first(r.get("targetBedTemp0"), r.get("bedTargetTemp"),
                      r.get("targetBedTemp"), r.get("bedTempTarget"), default=0))
            + self._bed_offset, 1
        )

        # Progress / time
        progress = _f(_first(r.get("printProgress"), r.get("progress"), default=0))
        print_time = _i(_first(r.get("printJobTime"), r.get("printTime"), default=0))
        time_left = _i(_first(r.get("printLeftTime"), r.get("remainingTime"), default=0))

        # Filename — strip full path
        raw_fn = str(_first(r.get("printFileName"), r.get("fileName"),
                            r.get("filename"), r.get("gcodeName"), default=""))
        filename = raw_fn.split("/")[-1] if "/" in raw_fn else raw_fn

        # Fan speed (modelFanPct = already %; fanSpeed = 0-255 PWM)
        fan_pct = _first(r.get("modelFanPct"), r.get("fanPct"), default=None)
        if fan_pct is not None:
            fan_speed = _f(fan_pct)
        else:
            fan_pwm = _first(r.get("fanSpeed"), r.get("partFanSpeed"), default=None)
            fan_speed = round(_f(fan_pwm) / 255 * 100, 1) if fan_pwm is not None else 0.0

        speed_level = _f(_first(r.get("curFeedratePct"), r.get("speedLevel"),
                                r.get("printSpeed"), default=100))
        flow_rate = _f(_first(r.get("curFlowratePct"), r.get("feedRate"),
                              r.get("flowRate"), default=100))

        # Layers — TotalLayer has capital T in your firmware
        layer_current = _i(_first(r.get("layer"), r.get("curLayer"),
                                  r.get("currentLayer"), default=0))
        layer_total = _i(_first(r.get("TotalLayer"), r.get("totalLayer"),
                                r.get("totalLayers"), default=0))

        raw_dump = {k: v for k, v in r.items() if k not in ("method", "params")}

        return {
            KEY_ONLINE: True,
            KEY_STATUS: status,
            KEY_EXTRUDER_TEMP: nozzle_temp,
            KEY_EXTRUDER_TARGET: nozzle_target,
            KEY_BED_TEMP: bed_temp,
            KEY_BED_TARGET: bed_target,
            KEY_PROGRESS: round(progress, 1),
            KEY_PRINT_TIME: print_time,
            KEY_PRINT_TIME_LEFT: max(0, time_left),
            KEY_FILENAME: filename,
            KEY_FAN_SPEED: round(fan_speed, 1),
            KEY_PRINT_SPEED: round(speed_level, 1),
            KEY_FLOW_RATE: round(flow_rate, 1),
            KEY_LAYER_CURRENT: layer_current,
            KEY_LAYER_TOTAL: layer_total,
            KEY_RAW_DATA: json.dumps(raw_dump, ensure_ascii=False, default=str),
        }


class CrealityMoonrakerAPI:
    def __init__(self, host: str, port: int,
                 bed_offset: float = 0.0, nozzle_offset: float = 0.0) -> None:
        self._base = f"http://{host}:{port}"
        self._bed_offset = bed_offset
        self._nozzle_offset = nozzle_offset

    async def async_test_connection(self) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
                async with s.get(f"{self._base}/server/info") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def async_get_data(self) -> dict:
        _MOONRAKER_OBJECTS = (
            "print_stats&extruder&heater_bed"
            "&display_status&virtual_sdcard&fan&gcode_move"
        )
        url = f"{self._base}/printer/objects/query?{_MOONRAKER_OBJECTS}"
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
            async with s.get(url) as resp:
                resp.raise_for_status()
                raw = await resp.json()

        objs = raw.get("result", {}).get("status", {})
        ps = objs.get("print_stats", {})
        ext = objs.get("extruder", {})
        bed = objs.get("heater_bed", {})
        vsd = objs.get("virtual_sdcard", {})
        disp = objs.get("display_status", {})
        fan = objs.get("fan", {})
        gm = objs.get("gcode_move", {})

        state = ps.get("state", "standby")
        duration = _f(ps.get("print_duration"))
        progress_raw = vsd.get("progress") if vsd.get("progress") is not None else (disp.get("progress") or 0)
        progress = _f(progress_raw) * 100
        time_left = int(duration / (progress / 100) - duration) if progress > 0 else 0

        return {
            KEY_ONLINE: True,
            KEY_STATUS: state,
            KEY_EXTRUDER_TEMP: round(_f(ext.get("temperature")) + self._nozzle_offset, 1),
            KEY_EXTRUDER_TARGET: round(_f(ext.get("target")), 1),
            KEY_BED_TEMP: round(_f(bed.get("temperature")) + self._bed_offset, 1),
            KEY_BED_TARGET: round(_f(bed.get("target")), 1),
            KEY_PROGRESS: round(progress, 1),
            KEY_PRINT_TIME: _i(duration),
            KEY_PRINT_TIME_LEFT: max(0, time_left),
            KEY_FILENAME: ps.get("filename", ""),
            KEY_FAN_SPEED: round(_f(fan.get("speed", 0)) * 100, 1),
            KEY_PRINT_SPEED: round(_f(gm.get("speed", 0)) / 60, 0),
            KEY_FLOW_RATE: round(_f(gm.get("extrude_factor", 1)) * 100, 1),
            KEY_LAYER_CURRENT: _i(ps.get("info", {}).get("current_layer")),
            KEY_LAYER_TOTAL: _i(ps.get("info", {}).get("total_layer")),
            KEY_RAW_DATA: json.dumps({"print_stats": ps, "extruder": ext, "heater_bed": bed}, default=str),
        }
