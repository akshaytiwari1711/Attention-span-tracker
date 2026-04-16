import json
import os
from datetime import datetime, timezone
from collections import Counter

class SessionReporter:
    """Aggregates ephemeral session data and generates end-of-session structured reports."""

    def __init__(self, history_manager=None):
        self.timeline = []        # per-cycle records: (timestamp, score, state, context)
        self.context_scores = {}  # context -> list of scores
        self.state_counts = Counter()
        self.app_metrics = {}     # app -> {cycles, scores}
        self.cycle_count = 0
        self.history_manager = history_manager
        
        if self.history_manager:
            self.preload_history()

    def preload_history(self):
        """Loads today's cycles from the database to ensure session continuity."""
        try:
            # Fetch cycles from today
            from datetime import date
            today_str = date.today().isoformat()
            
            # Use HistoryManager to get today's data (we'll assume get_recent_history can be filtered or just take all)
            # For simplicity, we'll fetch last 500 cycles and filter by date
            recent = self.history_manager.get_recent_history(limit=500)
            for payload in reversed(recent):
                ts = payload.get("timestamp", "")
                if ts.startswith(today_str):
                    self.record_cycle(payload, is_preload=True)
            
            print(f"[SessionReporter] Preloaded {len(self.timeline)} cycles from today's history.", flush=True)
        except Exception as e:
            print(f"[SessionReporter] Warning: Could not preload history: {e}")

    def record_cycle(self, payload: dict, is_preload: bool = False):
        """Called every 5-sec cycle to accumulate session data."""
        if not is_preload:
            self.cycle_count += 1
        
        ts = payload.get("timestamp", "")
        score = payload.get("attention_score")
        # Handle None scores gracefully - treat as 0 for aggregation
        if score is None:
            score = 0
        state = payload.get("attention_state", "UNKNOWN")
        context = payload.get("context", "TRANSITION")
        process = payload.get("window_info", {}).get("process_name", "Unknown")

        self.timeline.append({
            "timestamp": ts,
            "score": score,
            "state": state,
            "context": context,
            "process": process
        })
        
        self.state_counts[state] += 1
        
        if context not in self.context_scores:
            self.context_scores[context] = []
        self.context_scores[context].append(score)
        
        # Track app metrics
        if not hasattr(self, 'app_metrics'):
            self.app_metrics = {}
        if process not in self.app_metrics:
            self.app_metrics[process] = {'cycles': 0, 'scores': []}
        self.app_metrics[process]['cycles'] += 1
        self.app_metrics[process]['scores'].append(score)

    def generate_report(self) -> dict:
        """Produces the full end-of-session structured report."""
        if not self.timeline:
            return {"error": "No data recorded for this session.", "session_summary": {"total_cycles": 0}, "score_timeline": [], "state_distribution": {}, "app_breakdown": {}, "context_breakdown": {}}

        total_cycles = len(self.timeline)
        scores = [entry["score"] for entry in self.timeline if entry["score"] is not None]
        if not scores: scores = [0]

        # 1. Session timeline — per-cycle score array with proper timestamp format
        score_timeline = []
        for i, e in enumerate(self.timeline):
            ts = e["timestamp"]
            # Format timestamp for chart display (use incremental index if timestamp parsing fails)
            display_ts = ts if ts else f"t_{i}"
            score_timeline.append({"t": display_ts, "s": e["score"]})

        # 2. State distribution — percentage of session in each state
        state_distribution = {
            state: round((count / total_cycles) * 100, 1)
            for state, count in self.state_counts.items()
        }

        # 3. Peak focus windows
        peak_windows = self._find_peak_windows(top_n=3)

        # 4. Context breakdown
        context_breakdown = {}
        for ctx, ctx_scores in self.context_scores.items():
            valid_scores = [s for s in ctx_scores if s is not None]
            context_breakdown[ctx] = {
                "cycles": len(ctx_scores),
                "duration_min": round(len(ctx_scores) * 0.5, 1),
                "avg_score": round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
            }

        # 5. App Usage Breakdown - aggregate application time and attention
        app_breakdown = {}
        if hasattr(self, 'app_metrics'):
            for proc, data in self.app_metrics.items():
                distraction_count = sum(
                    1 for entry in self.timeline
                    if entry["process"] == proc and entry["state"] == "PHONE DISTRACTION"
                )
                app_breakdown[proc] = {
                    "duration_min": round(data["cycles"] * 0.5, 1),
                    "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0,
                    "cycles": data["cycles"],
                    "distraction_count": distraction_count
                }
        else:
            # Fallback: compute from timeline if app_metrics not available
            app_metrics = {}
            for entry in self.timeline:
                proc = entry["process"]
                if proc not in app_metrics:
                    app_metrics[proc] = {"cycles": 0, "scores": [], "distraction_count": 0}
                app_metrics[proc]["cycles"] += 1
                if entry["score"] is not None:
                    app_metrics[proc]["scores"].append(entry["score"])
                if entry["state"] == "PHONE DISTRACTION":
                    app_metrics[proc]["distraction_count"] += 1
            
            for proc, data in app_metrics.items():
                app_breakdown[proc] = {
                    "duration_min": round(data["cycles"] * 0.5, 1),
                    "avg_score": round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0,
                    "cycles": data["cycles"],
                    "distraction_count": data.get("distraction_count", 0)
                }

        # 6. Overall summary stats
        avg_score = round(sum(scores) / len(scores), 1)
        peak_score = max(scores)
        low_score = min(scores)

        report = {
            "session_summary": {
                "total_duration_min": round(total_cycles * 0.5, 1),
                "total_cycles": total_cycles,
                "average_score": avg_score,
                "peak_score": peak_score,
                "lowest_score": low_score,
            },
            "score_timeline": score_timeline,
            "state_distribution": state_distribution,
            "app_breakdown": app_breakdown,
            "context_breakdown": context_breakdown,
            "peak_focus_windows": peak_windows,
        }

        # DEBUG: Log report generation
        print(f"[SessionReporter] total_cycles={total_cycles} timeline_points={len(score_timeline)} apps={list(app_breakdown.keys())} contexts={list(context_breakdown.keys())}", flush=True)
        print(f"[SessionReporter] state_dist={state_distribution}", flush=True)
        return report

    def save_report(self, filepath: str = "session_report.json"):
        """Saves the report as a JSON file."""
        report = self.generate_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSession report saved to: {filepath}", flush=True)
        return report

    def _find_peak_windows(self, top_n: int = 3) -> list:
        """Finds the top N sustained high-score windows (consecutive cycles >= 70)."""
        windows = []
        current_window = []

        for entry in self.timeline:
            if entry["score"] >= 70:
                current_window.append(entry)
            else:
                if len(current_window) >= 2:
                    avg = sum(e["score"] for e in current_window) / len(current_window)
                    windows.append({
                        "start": current_window[0]["timestamp"],
                        "end": current_window[-1]["timestamp"],
                        "duration_cycles": len(current_window),
                        "avg_score": round(avg, 1),
                        "context": current_window[0]["context"]
                    })
                current_window = []

        # Capture trailing window
        if len(current_window) >= 2:
            avg = sum(e["score"] for e in current_window) / len(current_window)
            windows.append({
                "start": current_window[0]["timestamp"],
                "end": current_window[-1]["timestamp"],
                "duration_cycles": len(current_window),
                "avg_score": round(avg, 1),
                "context": current_window[0]["context"]
            })

        # Sort by avg_score * duration for "best" windows
        windows.sort(key=lambda w: w["avg_score"] * w["duration_cycles"], reverse=True)
        return windows[:top_n]

    def _find_distraction_spikes(self) -> list:
        """Identifies points where score dropped by 20+ points between cycles."""
        spikes = []
        for i in range(1, len(self.timeline)):
            prev_score = self.timeline[i - 1]["score"]
            curr_score = self.timeline[i]["score"]
            drop = prev_score - curr_score

            if drop >= 20:
                spikes.append({
                    "timestamp": self.timeline[i]["timestamp"],
                    "score_before": prev_score,
                    "score_after": curr_score,
                    "drop": drop,
                    "context_before": self.timeline[i - 1]["context"],
                    "context_after": self.timeline[i]["context"],
                })
        return spikes
