import json
from datetime import datetime, timedelta
from pathlib import Path


class HistoricalTracker:
    """Tracks and analyzes attention patterns over time (daily, weekly, monthly)."""
    
    def __init__(self, history_file: str = "data/attention_history.jsonl"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(exist_ok=True)
    
    def record_cycle(self, timestamp: str, score: int, state: str, context: str):
        """Record a single attention cycle to history."""
        entry = {
            "timestamp": timestamp,
            "score": score,
            "state": state,
            "context": context
        }
        
        with open(self.history_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_daily_stats(self, days: int = 1) -> dict:
        """Get attention statistics for the last N days."""
        cutoff_time = datetime.now(datetime.timezone.utc) - timedelta(days=days)
        scores = []
        states = {}
        contexts = {}
        
        if not self.history_file.exists():
            return {}
        
        with open(self.history_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_time > cutoff_time:
                        scores.append(entry['score'])
                        state = entry['state']
                        states[state] = states.get(state, 0) + 1
                        context = entry['context']
                        contexts[context] = contexts.get(context, 0) + 1
                except:
                    pass
        
        return {
            "period_days": days,
            "samples": len(scores),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "peak_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "state_distribution": states,
            "context_breakdown": contexts
        }
    
    def get_weekly_stats(self) -> dict:
        """Get attention statistics for the last 7 days."""
        return self.get_daily_stats(days=7)
    
    def get_monthly_stats(self) -> dict:
        """Get attention statistics for the last 30 days."""
        return self.get_daily_stats(days=30)
    
    def get_trend(self, days: int = 7) -> str:
        """Determine trend over the specified period."""
        cutoff_time = datetime.now() - timedelta(days=days)
        scores = []
        
        if not self.history_file.exists():
            return "INSUFFICIENT_DATA"
        
        with open(self.history_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    
                    if entry_time > cutoff_time:
                        scores.append(entry['score'])
                except:
                    pass
        
        if len(scores) < 2:
            return "INSUFFICIENT_DATA"
        
        # Compare first half vs second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / len(scores[:mid])
        second_half_avg = sum(scores[mid:]) / len(scores[mid:])
        
        diff = second_half_avg - first_half_avg
        if diff > 5:
            return "IMPROVING"
        elif diff < -5:
            return "DECLINING"
        else:
            return "STABLE"
    
    def get_focus_patterns(self) -> dict:
        """Analyze focus patterns by time of day."""
        patterns = {
            "morning": [],    # 6-12
            "afternoon": [],  # 12-18
            "evening": [],    # 18-24
            "night": []       # 0-6
        }
        
        if not self.history_file.exists():
            return patterns
        
        with open(self.history_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    hour = entry_time.hour
                    score = entry['score']
                    
                    if 6 <= hour < 12:
                        patterns["morning"].append(score)
                    elif 12 <= hour < 18:
                        patterns["afternoon"].append(score)
                    elif 18 <= hour < 24:
                        patterns["evening"].append(score)
                    else:
                        patterns["night"].append(score)
                except:
                    pass
        
        # Compute averages
        result = {}
        for period, scores in patterns.items():
            if scores:
                result[period] = round(sum(scores) / len(scores), 1)
            else:
                result[period] = 0
        
        return result
