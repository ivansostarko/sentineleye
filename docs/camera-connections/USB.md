# Connecting a USB Camera

> SentinelEye treats USB webcams (and USB capture cards) as first-class
> camera sources via Linux's V4L2 layer. This guide is end-to-end: from
> "I just plugged it in" through to a recorded, AI-analysed pinned tile
> on your dashboard.

---

## 1. What is a "USB camera" here?

Anything that exposes itself to Linux as a **UVC** (USB Video Class) device,
which appears as one or more character devices under `/dev/video*`:

| Class                                          | Examples                                                                |
|------------------------------------------------|-------------------------------------------------------------------------|
| Built-in laptop webcam                         | Most modern laptops (Intel, Realtek, etc.)                              |
| External UVC webcam                            | Logitech C920/C922/Brio, Razer Kiyo, Lumina, Anker PowerConf C300       |
| HDMI → USB capture card (UVC mode)             | Elgato CamLink 4K, generic "HDMI to USB 3.0" sticks                     |
| Action cam in webcam mode                      | GoPro Hero 9+ (with media mod), Insta360 link                           |
| ONVIF/IP camera bridges with UVC firmware      | rare; usually just use [RTSP](./RTSP.md) instead                        |

If your device doesn't show up under `/dev/video*` after plugging it in, it's
not a UVC device and won't work without a vendor-specific kernel driver.
Don't waste time — use the manufacturer's RTSP stream over the LAN instead.

---

## 2. Verify the host can see the camera

Run these on the **host machine** (the one where the recording-service
container runs), not inside any container.

### Is the device present?

```bash
lsusb
# Look for your camera by vendor/model name, e.g.:
#   Bus 001 Device 005: ID 046d:085b Logitech, Inc. C925e
```

### What `/dev/videoN` numbers did the kernel assign?

```bash
ls -la /dev/video*
# crw-rw---- 1 root video 81, 0 May 10 19:42 /dev/video0
# crw-rw---- 1 root video 81, 1 May 10 19:42 /dev/video1
```

A single physical webcam usually exposes **two** entries (one for video,
one for metadata). The video device is always the lower-numbered one.

### What does the camera advertise?

```bash
sudo apt-get install v4l-utils      # one-time
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Sample `--list-formats-ext` output:

```
ioctl: VIDIOC_ENUM_FMT
  Type: Video Capture
  [0]: 'YUYV' (YUYV 4:2:2)
    Size: Discrete 1920x1080
      Interval: Discrete 0.200s (5.000 fps)
      Interval: Discrete 0.133s (7.500 fps)
      Interval: Discrete 0.100s (10.000 fps)
    Size: Discrete 1280x720
      Interval: Discrete 0.033s (30.000 fps)
      …
  [1]: 'MJPG' (Motion-JPEG, compressed)
    Size: Discrete 1920x1080
      Interval: Discrete 0.033s (30.000 fps)
      …
```

The two pixel formats matter for SentinelEye:

* **`YUYV`** is uncompressed — best image quality, but USB 2.0 caps you
  at ~5 fps for 1080p. Fine for low-FPS detection-only use.
* **`MJPG`** is JPEG-compressed at the camera — full 30 fps at 1080p
  even on USB 2.0. **Prefer this** for live recording.

We'll force the right format below in step 6.

---

## 3. Fix permissions so the recorder can open the device

By default, `/dev/videoN` is owned by `root:video` mode `crw-rw----`. The
recording-service container runs as a non-root user (UID 1000), so it
needs to be in the `video` group.

### One-shot for the host shell (testing only)

```bash
sudo usermod -aG video $USER
# Log out and back in (or run `newgrp video`) so the new group sticks.
ffplay /dev/video0      # smoke test — you should see a window open
```

### For the Docker container

The container's user must be in a group whose **GID matches** the host's
`video` group. On Debian/Ubuntu hosts the `video` GID is typically `44`,
on Fedora it varies. Check on the host:

```bash
getent group video
# video:x:44:john
```

The recording-service Dockerfile already creates a `video` group at GID
`44` and adds the runtime user to it. If your host's `video` GID is
different, override it with a build arg in `docker-compose.yml`:

```yaml
recording-service:
  build:
    context: .
    dockerfile: docker/recording-service/Dockerfile
    args:
      VIDEO_GID: 44       # ← match `getent group video` on your host
```

---

## 4. Give the container access to the device

This is the step people miss. By default Docker containers see *no*
host devices. You have to pass each `/dev/videoN` through explicitly.

Edit `docker-compose.yml` and add a `devices:` list to `recording-service`
**and** `ai-engine` (because the AI engine reads frames too):

```yaml
recording-service:
  build:
    context: .
    dockerfile: docker/recording-service/Dockerfile
  restart: unless-stopped
  env_file: .env
  environment:
    <<: *common-env
    BACKEND_URL: http://backend:8000
  depends_on:
    backend:
      condition: service_started
  ports:
    - "8200:8200"
  volumes:
    - recordings-data:/data/recordings
  # ─── USB cameras ────────────────────────────────────────────
  devices:
    - "/dev/video0:/dev/video0"        # one line per camera
    - "/dev/video2:/dev/video2"
    # Or pass everything through (lazier; works if you trust the host):
    # - "/dev:/dev"
  group_add:
    - "44"                              # host video group GID
```

If you mount the entire `/dev` (the lazy form), Docker will hand the
container access to every device the host adds *after* the container
started — useful when you hot-plug cameras. The downside is a wider
attack surface; only do it on a trusted host.

After the edit:

```bash
docker compose up -d recording-service ai-engine
docker compose exec recording-service ls -la /dev/video*
# → should show the same character devices as the host
```

---

## 5. Add the camera in the UI

1. Go to **Cameras → Add camera**.
2. Connection tab:
   * **Protocol**: `USB`
   * **URL**: the device path or index. Both work:
     * `/dev/video0` — explicit, recommended
     * `0` — OpenCV-style index; the "0" maps to the first `/dev/video*`
       Docker exposes inside the container
   * **Username / Password**: leave blank (V4L2 has no auth).
3. Configuration tab:
   * **Category**: pick whatever you'd use this camera for (Indoor /
     Doorbell / etc.). Doesn't affect connection — just a UI hint.
   * **Target FPS**: see "Performance" below.
4. Positioning tab:
   * For a stationary USB camera you can drop a pin and set a
     [Field of view](#) cone like any IP camera. Heading + horizontal
     angle behave identically.
5. Save.

The recording-service health-checks the camera within 60 s; the tile on
the cameras grid should flip to **Online** with a recent snapshot.

---

## 6. Pick the right format (avoid YUYV at 5 fps)

By default ffmpeg / OpenCV ask V4L2 for the first format the device
advertises, which is often `YUYV`. On USB 2.0 buses that ceilings you
to **5 fps at 1080p** — useless for surveillance.

Force MJPEG by setting `config.v4l2_input_format` on the camera. The
recording-service reads it and prepends the right `-input_format mjpeg`
flag to ffmpeg.

Two ways to set it:

### Via the API (or a shell while the form-dialog UI lacks the field)

```bash
curl -X PATCH https://localhost:8000/api/v1/cameras/<CAM_UUID> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "v4l2_input_format": "mjpeg",
      "v4l2_video_size": "1920x1080",
      "v4l2_framerate": 30
    }
  }'
```

### Via direct `psql` (when shelling in)

```bash
docker compose exec postgres psql -U sentinel -d sentineleye -c \
  "UPDATE cameras
     SET config = config || '{\"v4l2_input_format\":\"mjpeg\",\
                              \"v4l2_video_size\":\"1920x1080\",\
                              \"v4l2_framerate\":30}'::jsonb
     WHERE name = 'Front Door';"
```

Recommended starting point per use case:

| Use case               | input_format | video_size | framerate |
|------------------------|--------------|------------|-----------|
| Live recording 24/7    | `mjpeg`      | `1920x1080`| 30        |
| Detection-only, low BW | `mjpeg`      | `1280x720` | 15        |
| Best image quality     | `yuyv422`    | `640x480`  | 30        |
| Capture card (HDMI-in) | `mjpeg`      | `1920x1080`| 60        |

---

## 7. Stable device names across reboots (multi-camera setups)

`/dev/video0` is whichever camera the kernel enumerated first — that
order **is not stable** across reboots or hot-plugs. With more than one
USB camera you'll randomly swap which feed is which.

Fix it once with udev. Find your cameras' serial numbers:

```bash
udevadm info -q all -n /dev/video0 | grep -E "ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL_SHORT"
# E: ID_VENDOR_ID=046d
# E: ID_MODEL_ID=085b
# E: ID_SERIAL_SHORT=AB12CD34
```

Create `/etc/udev/rules.d/99-sentineleye-cameras.rules`:

```
SUBSYSTEM=="video4linux", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="085b", \
  ATTRS{serial}=="AB12CD34", SYMLINK+="sentineleye/front-door"
SUBSYSTEM=="video4linux", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="085b", \
  ATTRS{serial}=="EF56GH78", SYMLINK+="sentineleye/back-yard"
```

Reload + replug:

```bash
sudo udevadm control --reload
sudo udevadm trigger
ls -la /dev/sentineleye/
# lrwxrwxrwx … front-door -> ../video0
# lrwxrwxrwx … back-yard  -> ../video2
```

Then in `docker-compose.yml` pass through the **stable** symlinks:

```yaml
devices:
  - "/dev/sentineleye/front-door:/dev/video0"
  - "/dev/sentineleye/back-yard:/dev/video1"
```

Now it doesn't matter which physical USB port you plug into — the
right camera always lands at the right path inside the container.

---

## 8. Performance & expectations

| Aspect             | Reality                                                                         |
|--------------------|---------------------------------------------------------------------------------|
| Bandwidth (USB 2.0)| ~480 Mb/s shared across ports → cap ~3 cameras at 1080p30 MJPEG                 |
| Bandwidth (USB 3.0)| ~5 Gb/s → 8+ cameras comfortably; MJPEG at 4K30 from a single capture card OK   |
| CPU on the host    | ffmpeg copy-only mode is cheap. AI inference is the cost — see ai-engine docs.  |
| Latency            | <100 ms glass-to-recorder typical; <500 ms to dashboard tile                    |
| Storage            | 1080p30 MJPEG ≈ 2.5 GB/h. Plan retention accordingly.                           |

---

## 9. Troubleshooting

| Symptom                                                | Fix                                                                                      |
|--------------------------------------------------------|------------------------------------------------------------------------------------------|
| `Cannot open device /dev/video0: Permission denied`    | Container user not in `video` group. Add `group_add: ["44"]` (or your host's video GID). |
| `Cannot open device … No such file or directory`       | Forgot the `devices:` passthrough in compose. Or device is on a different `/dev/videoN`. |
| `Device or resource busy`                              | Another process has it (e.g. `cheese`, a browser WebRTC tab, or **another camera row**). |
| Tile shows `unknown`/`offline` after 60 s              | Recording-service can't probe. `docker compose logs recording-service` shows the cause.  |
| Stream works but only 5 fps at 1080p                   | YUYV uncompressed — set `v4l2_input_format=mjpeg` (step 6).                              |
| Detection works but recordings are empty `.mp4` files  | Permission writing to `recordings-data` volume. Check ownership: `chown -R 1000:1000 …`. |
| Camera randomly stops working after host reboot        | `/dev/videoN` reshuffled. Move to udev symlinks (step 7).                                |
| `select timeout` from ffmpeg every few seconds         | USB hub oversubscribed. Try a powered hub or split cameras across host's USB controllers.|
| Snapshots are dark / oversaturated                     | Use `v4l2-ctl -d /dev/video0 --set-ctrl exposure_auto=3,brightness=128` then re-test.    |

For deeper diagnosis run ffmpeg directly inside the container:

```bash
docker compose exec recording-service \
  ffmpeg -f v4l2 -input_format mjpeg -video_size 1920x1080 -framerate 30 \
    -i /dev/video0 -t 5 -c copy /tmp/test.mp4
docker compose exec recording-service ls -la /tmp/test.mp4
```

A non-zero-byte file proves the device + permissions + format are all OK
end-to-end — any UI issue from here is a backend/UI bug, not USB.

---

## 10. Limitations to know about up front

* **Local only.** USB cameras must be physically attached to whichever
  machine runs `recording-service`. There's no remote USB-over-IP
  passthrough in the supported configuration. If your camera lives
  elsewhere, run a tiny relay there with `ffmpeg -i /dev/video0 -f rtsp
  rtsp://...` or use a network camera.
* **No PTZ.** SentinelEye doesn't expose UVC PTZ controls (pan/tilt/zoom)
  even on cameras that support them — those go through V4L2 ioctls
  rather than RTSP/ONVIF. Use the camera's own software for PTZ.
* **No audio.** Recording is video-only by design. The audio track on a
  UVC mic-equipped webcam is dropped at the recorder.
* **One camera per row.** A single physical camera that exposes two
  streams (e.g. 1080p main + 480p sub) needs two `Camera` rows pointing
  to the same `/dev/videoN` with different `config.v4l2_video_size`.
  Keep them in sync via the camera name (e.g. `Front Door (main)` /
  `Front Door (sub)`).

---

## 11. See also

* [CAMERA_SUPPORT.md](../CAMERA_SUPPORT.md) — protocol matrix + URL
  patterns for every supported source type.
* [ARCHITECTURE.md](../ARCHITECTURE.md) — how the recording-service and
  AI engine consume the URL.
* [DEPLOYMENT.md](../DEPLOYMENT.md) — host-level GPU + capture-card
  passthrough notes for production deployments.
