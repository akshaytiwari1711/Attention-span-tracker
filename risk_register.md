# Risk Register

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Camera lock conflict | High | Medium | Retry camera init |
| MJPEG freeze | High | Medium | Stream watchdog |
| Memory leak | High | Low | Resource cleanup hooks |
| Wrong classification | Medium | High | Keyword retraining |
| CPU overload | High | Medium | Frame throttling |
