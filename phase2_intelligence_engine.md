# Phase 2 — Intelligence Engine

## Objective
Implement context detection, attention scoring, productivity logic.

## Iteration 2.1 Context Detection
### Risks
- Misclassification
- Missing browser title
### Fix
- Title fallback parser
- Keyword expansion table

## Iteration 2.2 Attention Scoring
### Problems
- False positives in dark rooms
- Face partially visible
### Fix
- Confidence threshold calibration

## Iteration 2.3 Productivity Logic
### Edge Cases
- User attentive but idle
- Educational content minimized
### Resolution
- Context priority overrides idle states
