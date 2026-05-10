# API Reference

Base URL: `http://localhost:8000` (dev) — versioned under `/api/v1`.
OpenAPI explorer: `/docs`. Machine-readable spec: `/openapi.json`.

All non-auth endpoints require a `Authorization: Bearer <access_token>` header.

## Auth

### `POST /api/v1/auth/register`
```json
{ "email": "you@example.com", "password": "ChangeMe!1234", "full_name": "You", "role": "viewer" }
```
→ `201 UserPublic`

### `POST /api/v1/auth/login`
```json
{ "email": "you@example.com", "password": "ChangeMe!1234" }
```
→ `200 { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`

### `POST /api/v1/auth/refresh`
```json
{ "refresh_token": "..." }
```
→ `200 TokenPair`

### `GET /api/v1/auth/me`
→ `200 UserPublic`

## Cameras

### `GET /api/v1/cameras?page=1&size=50`
→ `200 Page<CameraPublic>`

### `POST /api/v1/cameras` *(operator/admin)*
```json
{
  "name": "Front Door",
  "location": "Outside",
  "protocol": "rtsp",
  "url": "rtsp://192.168.1.10:554/stream1",
  "username": "admin",
  "password": "secret",
  "enabled": true,
  "record_continuous": true,
  "detection_enabled": true,
  "target_fps": 15
}
```
→ `201 CameraPublic`

### `GET /api/v1/cameras/{id}` → `200 CameraPublic`
### `PATCH /api/v1/cameras/{id}` *(operator/admin)* → `200 CameraPublic`
### `DELETE /api/v1/cameras/{id}` *(admin)* → `204 No Content`

## Detection Events

### `GET /api/v1/detection-events`
Query: `camera_id`, `object_class`, `start`, `end`, `page`, `size`.
→ `200 Page<DetectionEventPublic>`

### `POST /api/v1/detection-events`
Used by the AI engine (service-token auth).
```json
{
  "camera_id": "uuid",
  "occurred_at": "2025-01-01T12:34:56Z",
  "object_class": "person",
  "confidence": 0.91,
  "track_id": 17,
  "bbox": { "x": 0.12, "y": 0.30, "w": 0.20, "h": 0.45 },
  "snapshot_key": null,
  "recording_id": null
}
```
→ `201 DetectionEventPublic`

## Recordings

### `GET /api/v1/recordings?camera_id=...&start=...&end=...&limit=100`
→ `200 [RecordingPublic]` — each item includes `playback_url` (signed for S3, backend-served for local).

### `GET /api/v1/recordings/{id}` → `200 RecordingPublic`

## Alert Rules

### `GET /api/v1/alert-rules` → `200 [AlertRulePublic]`

### `POST /api/v1/alert-rules` *(operator/admin)*
```json
{
  "name": "Person at Front Door at night",
  "enabled": true,
  "camera_id": "uuid-or-null",
  "trigger": "object_detected",
  "parameters": { "classes": ["person"], "min_confidence": 0.6, "hours": [22,23,0,1,2,3,4,5] },
  "channels": ["telegram", "realtime"],
  "cooldown_seconds": 60
}
```
→ `201 AlertRulePublic`

### `PATCH /api/v1/alert-rules/{id}` *(operator/admin)* → `200 AlertRulePublic`
### `DELETE /api/v1/alert-rules/{id}` *(admin)* → `204`

## System

### `GET /api/v1/system/info` → `200 { name, version, environment, storage_mode }`
### `GET /healthz` → `200 { "status": "ok" }`
### `GET /readyz` → `200 { "status": "ready" }` (DB + Redis reachable)

## WebSockets

All require `?token=<access_token>` query param.

### `WS /api/v1/ws/events/stream`

Receives JSON envelopes:
```json
{ "channel": "events.detections", "data": { /* DetectionEventPublic */ } }
{ "channel": "events.camera_state", "data": { "camera_id": "...", "status": "online" } }
{ "channel": "events.alerts", "data": { "rule_id": "...", "title": "...", "body": "..." } }
```

### `WS /api/v1/ws/cameras/{camera_id}/live`

Receives low-FPS JPEG previews:
```json
{ "jpeg_b64": "...", "ts": "2025-01-01T12:34:56Z" }
```
For production live view, prefer WebRTC or HLS — this WS path is suitable for
preview tiles (≤ 5 fps).

## Errors

All errors follow [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807):

```json
{
  "type": "about:blank#not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Camera 1234 not found."
}
```
