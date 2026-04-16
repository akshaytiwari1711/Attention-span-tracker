"""
Combined Attention Analysis Engine + Dashboard Server.
Runs the analysis loop in a background thread and serves a live dashboard at http://localhost:8080
"""

import time
import json
import os
import sys
import threading
import webbrowser

from datetime import datetime, timezone
from collections import deque
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Ensure imports work
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from sensors.screen import ScreenCaptureService
from sensors.webcam import WebcamGazeService
from sensors.input_monitor import InputMonitorService
from inference.context_classifier import ContextClassifier
from inference.signal_interpreter import SignalInterpreter
from core.attention_scorer import AttentionScorer
from core.insight_generator import InsightGenerator
from output.dispatcher import RealTimeDispatcher
from output.reporter import SessionReporter
from core.history_manager import HistoryManager
from core.system_monitor import SystemMonitor

# Global sensor references for the server to access
g_gaze_sensor = None
g_screen_sensor = None
g_reporter = None
history_manager = None
session_log = []

# --- Shared state for dashboard ---
latest_payload = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "session_duration_min": 0,
    "context": "TRANSITION",
    "attention_state": "WAITING",
    "attention_score": 0,
    "window_info": {"title": "Initializing...", "process_name": "—"},
    "input_metrics": {"keystrokes": 0, "backspaces": 0, "backspace_ratio": 0, "mouse_moves": 0, "mouse_clicks": 0, "scroll_events": 0},
    "signal_summary": {
        "gaze_stability": 0,
        "posture_score": 0,
        "interaction_focus": 0,
        "context_switches_last_5min": 0,
        "dominant_signal": "—",
    },
    "trend": "STABLE",
    "session_insight": "Dashboard initialized. Waiting for engine...",
    "intervention": None,
    "productivity_score": 0,
}
payload_lock = threading.Lock()

DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")
PORT = 8080

class DashboardHandler(SimpleHTTPRequestHandler):
    """Serves the dashboard HTML and provides JSON endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/latest"):
            with payload_lock:
                data = json.dumps(latest_payload)
            self._send_json(data)

        elif self.path.startswith("/api/report"):
            global g_reporter
            if g_reporter:
                report = g_reporter.generate_report()
                self._send_json(json.dumps(report))
            else: self.send_error(503)

        elif self.path.startswith("/api/history"):
            if history_manager:
                data = history_manager.get_daily_trend(days=7)
                self._send_json(json.dumps(data))
            else: self.send_error(503)

        elif self.path.startswith("/api/tasks"):
            if history_manager:
                data = history_manager.get_task_history(limit=50)
                self._send_json(json.dumps(data))
            else: self.send_error(503)

        elif self.path.startswith("/api/video_feed"):
            if g_gaze_sensor:
                self.send_response(200)
                self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
                self.end_headers()
                last_jpeg = None
                try:
                    while True:
                        jpeg = g_gaze_sensor.get_jpeg_frame()
                        if jpeg: last_jpeg = jpeg
                        if last_jpeg:
                            self.wfile.write(b'--frame\r\n')
                            self.send_header('Content-type', 'image/jpeg')
                            self.send_header('Content-length', len(last_jpeg))
                            self.end_headers()
                            self.wfile.write(last_jpeg)
                            self.wfile.write(b'\r\n')
                        time.sleep(0.05)
                except: pass
            else: self.send_error(503)

        elif self.path.startswith("/api/screen_preview"):
            if g_screen_sensor:
                jpeg = g_screen_sensor.get_jpeg_thumbnail()
                if jpeg:
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.end_headers()
                    self.wfile.write(jpeg)
                else: self.send_error(404)
            else: self.send_error(503)
        else:
            super().do_GET()

    def _send_json(self, data_str):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data_str.encode())

    def log_message(self, format, *args):
        pass

def start_dashboard_server():
    """Starts the HTTP server in a daemon thread."""
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print("Open this in browser: http://localhost:8080")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    webbrowser.open(f"http://localhost:{PORT}")
    return server

def engine_loop():
    """Main attention analysis loop."""
    global latest_payload, g_gaze_sensor, g_screen_sensor, g_reporter, history_manager

    print("Starting Attention Analysis Engine...", flush=True)

    # Init Managers
    history_manager = HistoryManager()
    
    # Init Sensors
    screen_sensor = ScreenCaptureService()
    gaze_sensor = WebcamGazeService()
    
    g_screen_sensor = screen_sensor
    g_gaze_sensor = gaze_sensor
    
    input_sensor = InputMonitorService()
    input_sensor.start()

    # Init Engines
    classifier = ContextClassifier()
    interpreter = SignalInterpreter()
    scorer = AttentionScorer()
    insight_gen = InsightGenerator()
    dispatcher = RealTimeDispatcher()
    g_reporter = SessionReporter(history_manager=history_manager)

    session_start = time.time()
    CYCLE_TIME = 5

    context_history = deque(maxlen=10)
    last_context = None

    try:
        while True:
            # --- 1. Gather Sensor Data ---
            win_meta = screen_sensor.get_active_window_metadata()
            screen_img = screen_sensor.capture_screen()

            raw_gaze = gaze_sensor.capture_frame_and_extract_features()
            raw_input = input_sensor.get_metrics_and_reset()

            # --- 2. Inference ---
            detected_objects = raw_gaze.get('detected_objects', [])
            context = classifier.classify(win_meta, screen_img, detected_objects)
            signals = interpreter.interpret(raw_gaze, raw_input)

            # --- 3. Track context switches ---
            if last_context is not None and context != last_context:
                context_history.append(time.time())
            last_context = context

            five_min_ago = time.time() - 300
            context_switches_5min = sum(1 for t in context_history if t > five_min_ago)

            # --- 4. Compute Attention ---
            score_data = scorer.compute_score(
                signals,
                context,
                face_detected=raw_gaze.get('face_detected', False),
                detected_objects=detected_objects
            )

            # --- 5. Insights ---
            session_duration_min = (time.time() - session_start) / 60.0
            insights = insight_gen.generate(score_data, session_duration_min, context)

            # --- 6. Build Payload ---
            sys_metrics = SystemMonitor.get_metrics()
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_duration_min": round(session_duration_min, 1),
                "context": context,
                "attention_state": score_data["attention_state"],
                "attention_score": score_data["attention_score"],
                "face_detected": raw_gaze.get("face_detected", False),
                "face_status": raw_gaze.get("status_message", "Unknown"),
                "user_present": score_data.get("user_present", False),
                "window_info": win_meta,
                "input_metrics": raw_input,
                "system_metrics": sys_metrics,
                "signal_summary": {
                    "gaze_stability": round(signals["gaze_focus"], 2),
                    "posture_score": round(signals["posture_stability"], 2),
                    "interaction_focus": round(signals["interaction_engagement"], 2),
                    "context_switches_last_5min": context_switches_5min,
                    "dominant_signal": _dominant_signal(signals, score_data),
                    "face_detected": raw_gaze.get("face_detected", False),
                },
                "trend": score_data["trend"],
                "session_insight": insights["session_insight"],
                "intervention": insights["intervention"],
                "productivity_score": score_data["productivity_score"],
            }

            session_record = {
                "timestamp": payload["timestamp"],
                "attention_score": payload["attention_score"] if payload["attention_score"] is not None else 0,
                "context": payload["context"],
                "application": win_meta.get("process_name") or win_meta.get("title", "Unknown"),
                "window_title": win_meta.get("title", "Unknown"),
                "duration_min": round(session_duration_min, 1),
                "gaze_stability": round(signals["gaze_focus"], 2),
                "attention_state": payload["attention_state"],
                "detected_objects": detected_objects,
                "face_detected": raw_gaze.get("face_detected", False),
            }
            session_log.append(session_record)
            print(f"[SessionLog] size={len(session_log)} app={session_record['application']} score={session_record['attention_score']} face={session_record['face_detected']}", flush=True)

            with payload_lock:
                latest_payload = payload

            # --- 7. Persistence and Dispatch ---
            dispatcher.dispatch(payload)
            g_reporter.record_cycle(payload)
            history_manager.save_cycle(payload)
            
            # DEBUG: Validate pipeline
            if len(session_log) % 10 == 0:
                print(f"[Debug] Session log has {len(session_log)} records, reporter has {len(g_reporter.timeline)} timeline points", flush=True)

            # Optimization based on battery
            opt_factor = SystemMonitor.get_optimization_factor()
            time.sleep(CYCLE_TIME * opt_factor)

    except KeyboardInterrupt:
        print("\nStopping Engine...", flush=True)
    finally:
        input_sensor.stop()
        screen_sensor.close()
        gaze_sensor.close()
        print("Shutdown complete.", flush=True)


def _dominant_signal(signals: dict, score_data: dict | None = None) -> str:
    screen_relevance = score_data.get("raw_screen_relevance", 0.3) if score_data else 0.3
    mapping = {
        "gaze": signals["gaze_focus"] * 0.40,
        "screen_relevance": screen_relevance * 0.30,
        "interaction": signals["interaction_engagement"] * 0.20,
        "posture": signals["posture_stability"] * 0.10,
    }
    return max(mapping, key=mapping.get)


def _print_report_summary(report: dict):
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
    print("=" * 50 + "\n", flush=True)


if __name__ == "__main__":
    # Start dashboard server first
    server = start_dashboard_server()

    # Run engine in main thread (so Ctrl+C works)
    engine_loop()
