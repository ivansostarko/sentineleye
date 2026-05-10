# Camera Support

SentinelEye treats each camera as a URL + protocol + optional credentials.
The recording service hands the URL to ffmpeg; the AI engine hands it to
OpenCV's `VideoCapture` (which itself uses ffmpeg).

## Supported protocols

| Protocol | URL example                                              | Notes                                |
|----------|----------------------------------------------------------|--------------------------------------|
| RTSP     | `rtsp://user:pass@192.168.1.10:554/Streaming/Channels/1` | Most common. Use TCP transport.      |
| RTMP     | `rtmp://server/live/streamkey`                           | Push-style streams.                  |
| ONVIF    | `http://192.168.1.10:8000/onvif/device_service`          | Discovery + profile selection.       |
| USB      | `0`, `1`, `/dev/video0`                                  | Local UVC webcams.                   |
| HTTP     | `http://192.168.1.10/video.mjpg`                         | Generic HTTP video.                  |
| MJPEG    | `http://192.168.1.10:8080/video`                         | Many phone-as-camera apps.           |

## Vendor-specific URL hints

| Vendor   | RTSP main stream                                                            |
|----------|-----------------------------------------------------------------------------|
| Hikvision| `rtsp://user:pass@host:554/Streaming/Channels/101`                          |
| Dahua    | `rtsp://user:pass@host:554/cam/realmonitor?channel=1&subtype=0`             |
| Axis     | `rtsp://user:pass@host/axis-media/media.amp`                                |
| Reolink  | `rtsp://user:pass@host:554/h264Preview_01_main`                             |
| Amcrest  | `rtsp://user:pass@host:554/cam/realmonitor?channel=1&subtype=0`             |
| Foscam   | `rtsp://user:pass@host:88/videoMain`                                        |
| TP-Link  | `rtsp://user:pass@host:554/stream1`                                         |

## ONVIF discovery

A future `POST /api/v1/cameras/discover` endpoint will WS-Discovery the LAN and
return candidate cameras. Until that lands, configure cameras manually.

## Health monitoring

- A backend Celery task (`camera_health_check`) probes each enabled camera every
  60 seconds and updates `cameras.status` to one of:
  `online | offline | degraded | unknown`.
- "degraded" is set when the probe succeeds but reports lower-than-target FPS or
  intermittent packet loss.
- `events.camera_state` is published on every status change so UI tiles update
  in real time.

## Reconnect logic

- ffmpeg in the recording-service uses `-rtsp_transport tcp` for reliability.
- When ffmpeg exits (camera dropped), the recorder re-spawns it with
  exponential backoff (max 30s).
- The AI engine's `VideoCapture` is wrapped in the same retry loop in
  `pipelines/__init__.py`.

## Bandwidth & FPS

- `target_fps` on a `Camera` controls the AI engine sample rate, not what's
  recorded. Recording always pulls the camera's native stream at native FPS.
- For cameras with a sub-stream (lower resolution), point detection at the
  sub-stream and recording at the main stream by configuring two `Camera` rows
  with the same name and different roles. (Future work: explicit sub-stream
  field on the schema.)

## Troubleshooting

| Symptom                                  | Try                                                 |
|------------------------------------------|-----------------------------------------------------|
| `401 Unauthorized` from RTSP             | URL-encode special chars in user/pass               |
| Black frames                             | Wrong substream / codec — try `subtype=1`           |
| `Server returned 5XX` on ONVIF           | Disable ONVIF auth or set Digest in client          |
| High CPU + dropped frames                | Lower `target_fps`; switch to GPU                   |
| Recording segment is 0 bytes             | ffmpeg failed silently — check service logs         |
