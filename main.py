import time
from datetime import datetime, timezone
import sys
import os
from collections import deque

# Suppress OpenCV warnings for cleaner output
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

# Ensure local imports work cleanly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sensors.screen import ScreenCaptureService
from sensors.webcam import WebcamGazeService
from sensors.input_monitor import InputMonitorService
from inference.context_classifier import ContextClassifier
from inference.signal_interpreter import SignalInterpreter
from core.attention_scorer import AttentionScorer
from core.insight_generator import InsightGenerator
from output.dispatcher import RealTimeDispatcher
from output.reporter import SessionReporter

def main_loop():
    print("Starting Attention Analysis Engine...", flush=True)
    
    # Init Sensors
    screen_sensor = ScreenCaptureService()
    gaze_sensor = WebcamGazeService()
    input_sensor = InputMonitorService()
    input_sensor.start()
    
    # Init Engines
    classifier = ContextClassifier()
    interpreter = SignalInterpreter()
    scorer = AttentionScorer()
    insight_gen = InsightGenerator()
    dispatcher = RealTimeDispatcher()
    reporter = SessionReporter()
    
    session_start = time.time()
    CYCLE_TIME = 5  # seconds - faster updates for real-time feel

    # Context switch tracking
    context_history = deque(maxlen=10)  # last 10 cycles = 5 minutes
    last_context = None
    
    try:
        while True:
            # --- 1. Gather Sensor Data ---
            win_meta = screen_sensor.get_active_window_metadata()
            screen_img = screen_sensor.capture_screen()
            
            raw_gaze = gaze_sensor.capture_frame_and_extract_features()
            raw_input = input_sensor.get_metrics_and_reset()
            
            # --- 2. Inference ---
            detected_objects = raw_gaze.get("detected_objects", [])
            face_present = raw_gaze.get("face_detected", False)

            context = classifier.classify(win_meta, screen_img, detected_objects)
            signals = interpreter.interpret(raw_gaze, raw_input)
            
            # --- 3. Track context switches ---
            if last_context is not None and context != last_context:
                context_history.append(time.time())
            last_context = context
            
            # Count switches in the last 5 minutes
            five_min_ago = time.time() - 300
            context_switches_5min = sum(1 for t in context_history if t > five_min_ago)
            
            # --- 4. Compute Attention ---
            score_data = scorer.compute_score(
                signals,
                context,
                face_detected=face_present,
                detected_objects=detected_objects
            )
            
            # --- 5. Insights ---
            session_duration_min = (time.time() - session_start) / 60.0
            insights = insight_gen.generate(score_data, session_duration_min, context)
            
            # --- 6. Build & Dispatch Payload ---
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_duration_min": round(session_duration_min, 1),
                "context": context,
                "attention_state": score_data["attention_state"],
                "attention_score": score_data["attention_score"],
                "signal_summary": {
                    "gaze_stability": round(signals["gaze_focus"], 2),
                    "posture_score": round(signals["posture_stability"], 2),
                    "interaction_focus": round(signals["interaction_engagement"], 2),
                    "context_switches_last_5min": context_switches_5min,
                    "dominant_signal": _dominant_signal(signals, score_data)
                },
                "trend": score_data.get("trend", "STABLE"),
                "session_insight": insights["session_insight"],
                "intervention": insights["intervention"]
            }
            
            dispatcher.dispatch(payload)
            reporter.record_cycle(payload)
            
            # Sleep for the heartbeat cycle
            time.sleep(CYCLE_TIME)
            
    except KeyboardInterrupt:
        print("\nStopping Engine via Keyboard Interrupt...", flush=True)
    finally:
        input_sensor.stop()
        screen_sensor.close()
        gaze_sensor.close()
        
        # Generate end-of-session report
        print("\nGenerating session report...", flush=True)
        report = reporter.save_report()
        _print_report_summary(report)
        
        print("Shutdown complete.", flush=True)


def _dominant_signal(signals: dict, score_data: dict | None = None) -> str:
    """Determines which signal contributes most to the current score."""
    mapping = {
        "gaze": signals.get("gaze_focus", 0.0) * 0.40,
        "interaction": signals.get("interaction_engagement", 0.0) * 0.20,
        "posture": signals.get("posture_stability", 0.0) * 0.10,
    }

    if score_data is not None:
        mapping["screen_relevance"] = score_data.get("raw_screen_relevance", 0.0) * 0.30
    else:
        mapping["screen_relevance"] = 0.0

    return max(mapping, key=mapping.get)


def _print_report_summary(report: dict):
    """Prints a human-readable summary of the session report."""
    if "error" in report:
        print(report["error"])
        return
    
    summary = report.get("session_summary", {})
    print("\n" + "=" * 50)
    print("         SESSION REPORT SUMMARY")
    print("=" * 50)
    print(f"  Duration:       {summary.get('total_duration_min', 0)} min")
    print(f"  Avg Score:      {summary.get('average_score', 0)}")
    print(f"  Peak Score:     {summary.get('peak_score', 0)}")
    print(f"  Lowest Score:   {summary.get('lowest_score', 0)}")
    print("-" * 50)
    
    states = report.get("state_distribution", {})
    print("  State Distribution:")
    for state, pct in states.items():
        print(f"    {state:<22} {pct}%")
    
    contexts = report.get("context_breakdown", {})
    print("-" * 50)
    print("  Context Breakdown:")
    for ctx, data in contexts.items():
        print(f"    {ctx:<18} {data['duration_min']} min  (avg: {data['avg_score']})")
    
    peaks = report.get("peak_focus_windows", [])
    if peaks:
        print("-" * 50)
        print(f"  Top Focus Windows: {len(peaks)} found")
        for i, p in enumerate(peaks, 1):
            print(f"    #{i}  avg={p['avg_score']}  cycles={p['duration_cycles']}  ctx={p['context']}")
    
    distractions = report.get("distraction_patterns", [])
    if distractions:
        print("-" * 50)
        print(f"  Distraction Spikes: {len(distractions)} detected")

    print("=" * 50 + "\n", flush=True)


if __name__ == "__main__":
    main_loop()
