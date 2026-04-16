import json
import csv
from datetime import datetime
from pathlib import Path


class DataExporter:
    """Exports session data to multiple formats (JSON, CSV)."""
    
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export_json(self, timeline_data: list, activity_history: list, filename: str = None) -> str:
        """Export session data to JSON format."""
        if filename is None:
            filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.output_dir / filename
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "timeline": timeline_data,
            "activity_history": activity_history,
            "statistics": self._compute_statistics(timeline_data)
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return str(filepath)
    
    def export_csv(self, timeline_data: list, filename: str = None) -> str:
        """Export timeline data to CSV format."""
        if filename is None:
            filename = f"timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.output_dir / filename
        
        if not timeline_data:
            return None
        
        fieldnames = ['timestamp', 'score', 'state', 'context', 'productivity_score']
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(timeline_data)
        
        return str(filepath)
    
    def export_summary_report(self, report_data: dict, filename: str = None) -> str:
        """Export a comprehensive summary report."""
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("ATTENTION ANALYSIS SESSION REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            summary = report_data.get("session_summary", {})
            f.write("SESSION SUMMARY\n")
            f.write("-" * 60 + "\n")
            f.write(f"Duration: {summary.get('total_duration_min', 0)} minutes\n")
            f.write(f"Average Score: {summary.get('average_score', 0)}\n")
            f.write(f"Peak Score: {summary.get('peak_score', 0)}\n")
            f.write(f"Lowest Score: {summary.get('lowest_score', 0)}\n\n")
            
            states = report_data.get("state_distribution", {})
            f.write("ATTENTION STATE DISTRIBUTION\n")
            f.write("-" * 60 + "\n")
            for state, pct in states.items():
                f.write(f"{state:<25} {pct}%\n")
            f.write("\n")
            
            contexts = report_data.get("context_breakdown", {})
            f.write("CONTEXT BREAKDOWN\n")
            f.write("-" * 60 + "\n")
            for ctx, data in contexts.items():
                f.write(f"{ctx:<20} {data['duration_min']} min  (avg score: {data['avg_score']})\n")
            f.write("\n")
            
            peaks = report_data.get("peak_focus_windows", [])
            if peaks:
                f.write("PEAK FOCUS WINDOWS\n")
                f.write("-" * 60 + "\n")
                for i, p in enumerate(peaks, 1):
                    f.write(f"#{i}  Score: {p['avg_score']}  Duration: {p['duration_cycles']} cycles  Context: {p['context']}\n")
                f.write("\n")
        
        return str(filepath)
    
    @staticmethod
    def _compute_statistics(timeline_data: list) -> dict:
        """Compute basic statistics from timeline data."""
        if not timeline_data:
            return {}
        
        scores = [entry.get('score', 0) for entry in timeline_data]
        
        return {
            "count_samples": len(scores),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "peak_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "median_score": sorted(scores)[len(scores) // 2] if scores else 0
        }
