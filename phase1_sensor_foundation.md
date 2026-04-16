# Phase 1 — Sensor Foundation

## Objective
Build robust webcam and screen capture infrastructure.

## Iteration 1.1 Webcam Acquisition
### Tasks
- Camera initialization
- Frame capture loop
- JPEG encoder

### Problems Faced
1. Webcam unavailable
2. Frame drops
3. Memory leaks

### Mitigation
- Retry logic
- Buffer overwrite policy
- Auto release resources

### Unit Tests
- Camera starts
- Captures 100 continuous frames
- Releases on shutdown

## Iteration 1.2 Screen Capture Engine
### Problems
- Lag spikes on 4K displays
- Black screen captures

### Solution
- Reduced-resolution preview mode
- Fallback capture retries
