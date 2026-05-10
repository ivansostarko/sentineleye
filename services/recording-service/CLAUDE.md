# CLAUDE.md — Recording Service

> Read the root [CLAUDE.md](../../CLAUDE.md) first.

## Responsibilities

- Spawn one ffmpeg process per enabled camera, segmenting output into N-second chunks
- Write segments to `LOCAL_STORAGE_PATH/{camera_id}/`
- Report each closed segment to the backend so it lands in the `recordings` table
- Survive transient camera disconnects via ffmpeg's auto-retry

The recording service does **not** read from the database directly. The backend
tells it which cameras to record (via the control-plane API).

## Why ffmpeg-segment vs HLS?

- HLS is great for browser playback but adds packaging overhead.
- `-f segment` produces self-contained MP4 chunks — easy to archive, easy to play
  back with a `<video>` element + signed URL, easy to delete.
- For live preview we use the AI engine's low-FPS WebSocket frames, not HLS.

## Storage Layout

```
$LOCAL_STORAGE_PATH/
└── {camera_id}/
    └── 20251225T143000Z.mp4    # segment start time, UTC, ISO8601 compact
```

Hybrid mode: a Celery task on the backend moves segments older than
`ARCHIVE_AFTER_DAYS` to S3 and updates `Recording.storage_backend` to `s3`.

## Dockerfile Notes

- Base image must include `ffmpeg`. We use `jrottenberg/ffmpeg:7-ubuntu` as the
  builder for the binary, then copy into a slim Python image.
- For NVENC/QSV hardware encoding, switch to a CUDA/QSV-enabled ffmpeg build.
