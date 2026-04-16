# Phase 3 — API Server Engineering

## Objective
Build multi-threaded backend delivery APIs.

### Problems Faced
1. Single-thread blocking
2. MJPEG stream freezes
3. Concurrent browser tab crashes

### Solution
- ThreadingHTTPServer
- Independent stream threads
- Socket timeout control

### Deliverables
- /api/latest
- /api/video_feed
- /api/screen_preview
