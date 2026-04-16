import time
import random

class InsightGenerator:
    def __init__(self):
        self.last_intervention_time = 0
        self.INTERVENTION_COOLDOWN_SEC = 20 * 60  # 20 minutes
        self.last_intervention_text = ""
        self.last_break_reminder_time = 0
        self.BREAK_REMINDER_INTERVAL = 25 * 60  # Pomodoro: 25 minutes
        
        # Customizable thresholds
        self.FOCUS_THRESHOLD = 80        # Score for "Deep Focus"
        self.ENGAGEMENT_THRESHOLD = 60   # Score for "Active Engagement"
        self.DISTRACTION_THRESHOLD = 40  # Score for "Distracted"

        # Varied intervention pool to avoid repetition
        self._interventions = [
            "A 90-second stretch or eye-rest away from the screen may help restore baseline focus.",
            "Shifting your gaze to a distant object for 20 seconds could help reduce eye strain.",
            "A brief walk or change of posture might help re-engage focus.",
            "Consider a short breathing exercise — 4 seconds in, 4 seconds hold, 4 seconds out.",
            "Stepping away for a glass of water may help reset your attention cycle.",
        ]
        
        # Break reminders
        self._break_reminders = [
            "Time for a 5-minute break — stand up and move around.",
            "You've been focused for a while. Take a short break to recharge.",
            "Quick break time: Step away, hydrate, and come back refreshed.",
            "Consider a 5-minute break to maintain your focus quality.",
            "Break reminder: Your attention benefits from regular pauses.",
        ]

    def generate(self, score_data: dict, session_duration_min: float, context: str) -> dict:
        """
        Generates contextual insights and interventions.
        """
        score = score_data.get("attention_score")
        state = score_data.get("attention_state", "UNKNOWN")
        trend = score_data.get("trend", "STABLE")
        
        # GATING HANDLER: If no score was generated (e.g. no face), return placeholder
        if score is None:
            return {
                "session_insight": "Seeking visual focus signals — position face within frame.",
                "intervention": None
            }
        
        # 1. Non-judgmental, observational insights
        insight = self._build_insight(state, context, session_duration_min, score, trend)

        # 2. Interventions
        intervention = self._build_intervention(score, state, session_duration_min)

        return {
            "session_insight": insight,
            "intervention": intervention
        }

    def _build_insight(self, state: str, context: str, duration: float, score: int, trend: str) -> str:
        """Builds a neutral, observational insight string."""
        mins = int(duration)

        if state == "DEEP FOCUS" and duration > 5:
            return f"Sustained deep focus for {mins} minutes in {context} context."
        
        if state == "DEEP FOCUS":
            return f"{context} session entering flow state."

        if state == "ACTIVE ENGAGEMENT":
            return f"Actively engaged in {context} — attention signals are positive."

        if state == "FATIGUED":
            return f"Attention signals have been declining over the last few cycles after {mins} minutes."

        if state == "PASSIVE WATCHING" and context in ("PASSIVE LEARN", "ENTERTAINMENT"):
            return f"Passive viewing pattern detected — consistent with {context} activity."

        if state == "SURFACE SKIMMING":
            return "Interaction pattern suggests scanning rather than deep reading."

        if state == "DISTRACTED":
            if trend == "DECLINING":
                return f"Focus has been trending downward over the session ({mins} min elapsed)."
            return f"Fragmented attention detected in {context} context."

        if state == "DISENGAGED":
            return "Minimal engagement signals detected from gaze and input."

        # Generic fallback
        return "Session is progressing with variable attention."

    def _build_intervention(self, score: int, state: str, session_duration_min: float) -> str | None:
        """Generates an intervention based on score, state, and break timing."""
        current_time = time.time()
        
        # Priority 1: Distraction/Fatigue interventions
        time_since_last_intervention = current_time - self.last_intervention_time
        if (score < self.DISTRACTION_THRESHOLD or state == "FATIGUED") and \
           (time_since_last_intervention > self.INTERVENTION_COOLDOWN_SEC):
            candidates = [i for i in self._interventions if i != self.last_intervention_text]
            intervention = random.choice(candidates) if candidates else self._interventions[0]
            self.last_intervention_time = current_time
            self.last_intervention_text = intervention
            return intervention
        
        # Priority 2: Proactive break reminders for sustained focus
        time_since_last_break = current_time - self.last_break_reminder_time
        if session_duration_min > 0 and \
           int(session_duration_min) % int(self.BREAK_REMINDER_INTERVAL / 60) == 0 and \
           time_since_last_break > (self.BREAK_REMINDER_INTERVAL - 30):
            if score >= self.ENGAGEMENT_THRESHOLD:  # Only remind during focused work
                break_reminder = random.choice(self._break_reminders)
                self.last_break_reminder_time = current_time
                return break_reminder
        
        return None
