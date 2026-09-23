# Morning Alarm

A Home Assistant custom integration that runs a configurable morning alarm: a gradual wake-up light fade combined with a Yoto (or any other) media player, on a per-day-of-week schedule.

Everything is configured through the Home Assistant UI — no YAML required.

---

## Features

- **Per-day schedule** — enable/disable and set a different alarm time for every day of the week
- **Wake-up light fade** — dimmable lights rise gradually from a low starting brightness to a final brightness over a configurable duration
- **Threshold trigger** — a separate set of on/off lights switch on once brightness passes a configurable threshold
- **Yoto / media player** — any HA media player entity; you supply the content ID for the station you want
- **Concurrent audio + lighting** — both start at the same time
- **Test button** — run the full alarm immediately without waiting for the scheduled time
- **Stop button** — cancel a running alarm and pause the media player
- **Dashboard entities** — alarm times, day switches, fade duration, and running status are all exposed as entities you can place on a dashboard
- **Graceful degradation** — Yoto offline, individual lights unavailable, non-dimmable lights all handled without stopping the rest of the sequence
- **DST-safe scheduling** — uses Home Assistant's local timezone via `dt_util`

---

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations → Custom repositories**.
2. Add `https://github.com/chrisdowling/ha-alarm` as an **Integration**.
3. Search for **Morning Alarm** and install it.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/morning_alarm/` from this repo into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Initial configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Morning Alarm** and click it.
3. Follow the five setup steps:

| Step | What you configure |
|---|---|
| **Name** | Display name for this alarm instance |
| **Audio** | Yoto media player entity + media content ID |
| **Lights** | Dimmable lights and on/off lights |
| **Brightness & fade** | Fade duration, start %, threshold %, final % |
| **Schedule** | Enable/disable + time for each day of the week |

You can re-run all five steps at any time via the **Configure** button on the integration card.

---

## Finding your Yoto content ID

The content ID is whatever you pass to `media_player.play_media`. The easiest way to find it:

1. Open **Developer Tools → Services** in HA.
2. Call `media_player.play_media` on your Yoto player with your desired station.
3. Check the HA log or inspect the service call data to see the `media_content_id` that was used.

Alternatively, use the Yoto HA integration's own controls to start a station and then check **Settings → Entities → [your Yoto player]** for the current `media_content_id` attribute.

---

## Configuring daily alarm times

After the integration is set up, each day has two entities:

- **Morning Alarm [Day] enabled** — switch to enable/disable that day
- **Morning Alarm [Day] alarm time** — time entity to set the alarm time

Changes to these entities take effect immediately (the scheduler re-arms for the next occurrence). No restart needed.

---

## Configuring lights

**Dimmable lights** — any `light` entity that supports the `brightness` attribute. Their brightness is set to `start_brightness`, then faded up to `final_brightness` over the `fade_duration`.

**On/off lights** — any `light` entity. They are turned on with a plain `light.turn_on` call when the dimmable lights reach `threshold_brightness`.

If you add a non-dimmable light to the dimmable list it will simply be turned on at each step without a brightness argument — it won't cause an error.

---

## Testing the alarm

Press the **Test alarm** button (entity: `button.<name>_test_alarm`) to run the complete alarm sequence immediately. This is identical to a scheduled trigger.

---

## Stopping an alarm

Press the **Stop alarm** button (entity: `button.<name>_stop_alarm`) while an alarm is running. This:

- Cancels the lighting fade (lights stay at whatever brightness they reached)
- Pauses the media player

It does **not** affect the configured schedule.

---

## Dashboard example

Add these entities to a card:

```yaml
type: entities
entities:
  - binary_sensor.morning_alarm_alarm_active
  - button.morning_alarm_test_alarm
  - button.morning_alarm_stop_alarm
  - number.morning_alarm_fade_duration
  - switch.morning_alarm_monday_enabled
  - time.morning_alarm_monday_alarm_time
  - switch.morning_alarm_tuesday_enabled
  - time.morning_alarm_tuesday_alarm_time
  # ... etc
```

---

## Troubleshooting

**Alarm didn't fire**
- Check the integration's entities in **Developer Tools → States** to confirm the schedule is set correctly.
- Check HA logs (`Settings → System → Logs`) for `morning_alarm` entries.
- Confirm the day is enabled (switch is on).
- Verify your HA timezone is set correctly under **Settings → System → General**.

**Lights didn't change**
- Confirm the light entities are available (not `unavailable` in States).
- Check whether the lights are in the dimmable or on/off list (not both).
- Use **Test alarm** and watch the HA log for debug messages.

**Yoto didn't play**
- Press **Test alarm** and check the log for `Failed to start media`.
- Verify the media player entity ID and content ID in the integration options.
- Confirm the Yoto player is online and available.

**Alarm fires but entities show wrong time after restart**
- Entity times are read from integration options. If you changed a time entity but didn't save via the Options flow, use the time entity UI to set it again.

---

## Known limitations

- Only one alarm sequence can run at a time. A second trigger while an alarm is already running is ignored (logged as a warning).
- The lighting fade uses 10-second steps. Very short fade durations (under 1 minute) will have few steps.
- Stopping an alarm leaves the lights at whatever brightness they reached — it does not turn them off.
