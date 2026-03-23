# ⚠️ Vibe coded use at your own risk

# Creality Ender-3 V3 KE — Home Assistant Integration

A custom component that exposes your **Creality Ender-3 V3 KE** 3D printer states as native Home Assistant entities. Fully local, no cloud required.

---

## How it works

The V3 KE exposes a **WebSocket server on port 9999** that continuously pushes JSON telemetry frames — the same stream used by Creality Print software and the built-in LAN dashboard. This integration connects to that stream directly; **no extra software, no SSH, no rooting needed**.

Optionally, if you have installed **Moonraker** (via the Creality Helper Script), you can use the Moonraker REST API mode instead for richer Klipper-level data.

---

## Entities

| Entity | Type | Description |
|---|---|---|
| Print Status | Sensor | `idle`, `printing`, `paused`, `complete`, `error` |
| Extruder Temperature | Sensor | Current hotend temp (°C) |
| Extruder Target Temperature | Sensor | Hotend set-point (°C) |
| Bed Temperature | Sensor | Current heated bed temp (°C) |
| Bed Target Temperature | Sensor | Bed set-point (°C) |
| Print Progress | Sensor | 0–100 % |
| Print Time Elapsed | Sensor | Seconds since print started |
| Print Time Remaining | Sensor | Estimated seconds left |
| Current File | Sensor | Filename currently printing |
| Fan Speed | Sensor | Part cooling fan % |
| Print Speed | Sensor | Speed level % |
| Flow Rate | Sensor | Extrusion flow rate % |
| Current Layer | Sensor | Current layer number |
| Total Layers | Sensor | Total layer count |
| Printing | Binary Sensor | `on` while actively printing |
| Paused | Binary Sensor | `on` while paused |
| Printer Error | Binary Sensor | `on` on error state |
| Printer Online | Binary Sensor | Connectivity indicator |
| Bed Heating | Binary Sensor | `on` while bed target > 0 °C |
| Extruder Heating | Binary Sensor | `on` while extruder target > 0 °C |

---

## Installation

### Manual (always works)

1. Copy the `custom_components/creality_v3_ke/` folder into your
   Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

### Via HACS

1. HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/your-repo/ha-creality-v3-ke` as **Integration**.
3. Install **Creality Ender-3 V3 KE** and restart Home Assistant.

---

## Setup

1. Find your printer's IP address on the printer screen:
   **Settings (gear icon) → Network → your WiFi network → IP address**

2. Go to **Settings → Devices & Services → Add Integration** in Home Assistant.

3. Search for **Creality Ender-3 V3 KE**.

4. Choose connection mode:

   | Mode | Port | Requirements |
   |---|---|---|
   | **Native WebSocket** ✅ recommended | **9999** | None — works with stock firmware |
   | Moonraker API | 7125 | Moonraker must be installed via SSH |

5. Enter the IP address, confirm the port, click Submit.

All 20 entities will appear under a single device.

---

## Troubleshooting

### "Cannot connect" during setup

- Double-check the IP on the printer screen (Settings → Network).
- Make sure the printer is **on the same WiFi network** as Home Assistant.
- Confirm you're using **port 9999** (not 80) for Native WebSocket mode.
- Try pinging the printer IP from your HA host:
  ```
  ping 192.168.x.x
  ```
- Some routers use **AP/client isolation** which blocks device-to-device LAN traffic. Check your router settings and disable client isolation if present.
- Verify no firewall rule is blocking port 9999 between HA and the printer.

### Can I check the WebSocket manually?

From any computer on the same network, you can verify the printer's WebSocket is working by opening the Creality web dashboard in a browser:
```
http://<printer-ip>
```
Then open browser DevTools (F12) → Network tab → filter by **WS** (WebSocket). You should see a connection to `ws://<printer-ip>:9999` with a stream of JSON messages.

### Sensors show 0 / empty values

The printer only sends certain fields while actively printing (progress, layer, time remaining, etc.). Temperature fields are always present. This is normal.

### Sensors stuck after printer power-off

The coordinator will mark entities unavailable within one polling cycle (10 s) once the WebSocket disconnects. They'll recover automatically when the printer powers back on.

---

## Lovelace Dashboard Example

```yaml
type: entities
title: 🖨 Creality V3 KE
entities:
  - entity: sensor.creality_v3_ke_print_status
  - entity: sensor.creality_v3_ke_print_progress
  - entity: sensor.creality_v3_ke_current_file
  - entity: sensor.creality_v3_ke_print_time_elapsed
  - entity: sensor.creality_v3_ke_print_time_remaining
  - entity: sensor.creality_v3_ke_current_layer
  - entity: sensor.creality_v3_ke_total_layers
  - entity: sensor.creality_v3_ke_extruder_temperature
  - entity: sensor.creality_v3_ke_bed_temperature
  - entity: sensor.creality_v3_ke_fan_speed
  - entity: binary_sensor.creality_v3_ke_printing
  - entity: binary_sensor.creality_v3_ke_printer_online
```

### Progress gauge card

```yaml
type: gauge
entity: sensor.creality_v3_ke_print_progress
name: Print Progress
min: 0
max: 100
severity:
  green: 0
  yellow: 70
  red: 95
```

---

## Automation Examples

### Notify when print completes

```yaml
alias: 3D print finished
trigger:
  - platform: state
    entity_id: sensor.creality_v3_ke_print_status
    to: "complete"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "🖨 Print done!"
      message: "Your 3D print has finished."
```

### Alert if printer goes offline during a print

```yaml
alias: Printer lost connection while printing
trigger:
  - platform: state
    entity_id: binary_sensor.creality_v3_ke_printer_online
    to: "off"
condition:
  - condition: state
    entity_id: binary_sensor.creality_v3_ke_printing
    state: "on"
action:
  - service: notify.persistent_notification
    data:
      title: "⚠️ Printer offline!"
      message: "Lost connection to the printer during a print."
```

---

## Technical Notes

- The printer's WebSocket (port 9999) is the same protocol used by:
  - Creality Print slicer software
  - The built-in web LAN dashboard
  - Node-RED integrations reported by the community
- Polling interval: **10 seconds** (each poll opens a WS connection, reads frames for ~12 s, closes).
- Field names are normalised to handle multiple firmware variants (different Creality firmware versions use slightly different JSON keys).
- For camera streaming: the printer exposes an MJPEG stream at `http://<printer-ip>:8080/?action=stream` — add this via Home Assistant's built-in **MJPEG IP Camera** integration.
