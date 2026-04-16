import json
from datetime import datetime, timezone

class RealTimeDispatcher:
    def __init__(self, log_path="session_log.jsonl"):
        self.log_path = log_path

    def dispatch(self, payload: dict):
        """
        Takes the fully constructed schema dict, prints it, and optionally saves it sequentially.
        """
        # Formulate timestamp if missing
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Print clean, readable attention metrics
        timestamp = payload.get("timestamp", "")
        score = payload.get("attention_score", 0)
        state = payload.get("attention_state", "UNKNOWN")
        context = payload.get("context", "UNKNOWN")
        trend = payload.get("trend", "STABLE")
        productivity = payload.get("productivity_score", 0)
        duration = payload.get("session_duration_min", 0)
        
        print("\n" + "=" * 70)
        print("ATTENTION ANALYSIS UPDATE")
        print("=" * 70)
        print(f"Time: {timestamp}")
        print(f"Session Duration: {duration} min")
        print("-" * 70)
        print(f"ATTENTION SCORE:        {score}/100")
        print(f"ATTENTION STATE:        {state}")
        print(f"CONTEXT:                {context}")
        print(f"TREND:                  {trend}")
        print(f"PRODUCTIVITY SCORE:     {productivity}/100")
        print("-" * 70)
        
        signals = payload.get("signal_summary", {})
        print("SIGNAL ANALYSIS:")
        print(f"  Gaze Stability:       {signals.get('gaze_stability', 0)}")
        print(f"  Posture Score:        {signals.get('posture_score', 0)}")
        print(f"  Interaction Focus:    {signals.get('interaction_focus', 0)}")
        print(f"  Dominant Signal:      {signals.get('dominant_signal', '—')}")
        print("-" * 70)
        
        insight = payload.get("session_insight", "")
        intervention = payload.get("intervention")
        if insight:
            print(f"INSIGHT: {insight}")
        if intervention:
            print(f"SUGGESTION: {intervention}")
        print("=" * 70 + "\n", flush=True)
        
        # Append full payload to log for data analysis
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as e:
            print("Dispatch write error:", e)
