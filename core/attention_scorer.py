class AttentionScorer:
    def __init__(self):
        # Weights defined by requirements
        self.W_GAZE = 0.40
        self.W_SCREEN_REL = 0.30
        self.W_TYPING = 0.20
        self.W_POSTURE = 0.10

        self.alpha = 0.20  # Smoothing factor
        self.max_change = 8  # Rate limiting
        
        # Smoothed values
        self.s_attention = 0
        self.s_gaze = 0
        self.s_posture = 0
        self.s_interaction = 0
        
        # Rolling history for trend and fatigue detection
        self.score_history = []  # list of recent scores
        self.MAX_HISTORY = 24    # ~2 minutes of 5-sec cycles
        
        # Calibration
        self.start_time = None
        self.warmup_period = 60 # seconds

    def compute_score(self, interpreted_signals: dict, context: str, face_detected: bool = True, detected_objects: list = None) -> dict:
        """
        Calculates the Attention Score (0-100) with strict gating.
        CRITICAL: When no face is detected, ALL scores are zeroed immediately.
        No smoothing, interpolation, or value carry-over when user is absent.
        """
        if detected_objects is None:
            detected_objects = []

        if self.start_time is None:
            import time
            self.start_time = time.time()
            self.is_warming_up = True
        else:
            import time
            self.is_warming_up = (time.time() - self.start_time) < self.warmup_period

        # === STRICT FACE PRESENCE GATE ===
        # When no face is detected: ZERO everything, no exceptions
        if not face_detected:
            # CRITICAL: Reset all smoothing buffers to prevent value carry-over
            self.s_gaze = 0.0
            self.s_posture = 0.0
            self.s_interaction = 0.0
            self.s_attention = 0
            
            return {
                "attention_score": 0,  # STRICT ZERO, not None
                "attention_state": "NO USER DETECTED",
                "raw_screen_relevance": 0,
                "trend": "STABLE",
                "productivity_score": 0,  # STRICT ZERO
                "no_face": True,
                "user_present": False,
                "status_message": "Waiting for face detection..."
            }

        # User IS detected — reset user_present flag
        user_was_absent = not hasattr(self, 'last_face_detected') or not self.last_face_detected
        self.last_face_detected = True
        
        # Raw values from signals
        raw_gaze = interpreted_signals.get("gaze_focus", 0.0)
        raw_typing = interpreted_signals.get("interaction_engagement", 0.0)
        raw_posture = interpreted_signals.get("posture_stability", 0.0)
        
        # APPLY SMOOTHING ONLY WHEN USER PRESENT
        self.s_gaze = (self.alpha * raw_gaze) + ((1 - self.alpha) * self.s_gaze)
        self.s_posture = (self.alpha * raw_posture) + ((1 - self.alpha) * self.s_posture)
        self.s_interaction = (self.alpha * raw_typing) + ((1 - self.alpha) * self.s_interaction)

        # OBJECT-BASED CONTEXT OVERRIDES
        phone_detected = any(phone in detected_objects for phone in ['cell phone', 'mobile phone', 'smartphone'])
        study_objects = 'book' in detected_objects or 'bottle' in detected_objects # bottle is pen proxy
        
        # State Priority Logic
        override_state = None
        if phone_detected and self.s_gaze < 0.4:
            override_state = "PHONE DISTRACTION"
        elif study_objects and self.s_gaze > 0.4:
            override_state = "ACTIVE STUDY"

        screen_relevance = self._compute_screen_relevance(context, self.s_gaze, self.s_interaction)
        if override_state == "ACTIVE STUDY":
            screen_relevance = 1.0 # High relevance for study objects

        # Base Score Formula
        score_float = (
            (self.s_gaze * self.W_GAZE) +
            (screen_relevance * self.W_SCREEN_REL) +
            (self.s_interaction * self.W_TYPING) +
            (self.s_posture * self.W_POSTURE)
        )
        
        if override_state == "PHONE DISTRACTION":
            score_float *= 0.3 # Heavy penalty for phone usage
        
        new_score = int(score_float * 100)
        new_score = max(0, min(100, new_score))
        
        # RATE LIMITING (Fix 05)
        diff = new_score - self.s_attention
        if abs(diff) > self.max_change:
            new_score = self.s_attention + (self.max_change if diff > 0 else -self.max_change)
        
        self.s_attention = new_score
        
        # Track history
        self.score_history.append(self.s_attention)
        if len(self.score_history) > self.MAX_HISTORY:
            self.score_history.pop(0)
        
        state = override_state if override_state else self._classify_state(self.s_attention, context)
        if self._detect_fatigue() and not override_state:
            state = "FATIGUED"
        
        trend = self._compute_trend()
        productivity = self._compute_productivity_score(self.s_attention, context, override_state)
        
        return {
            "attention_score": self.s_attention,
            "attention_state": state,
            "raw_screen_relevance": screen_relevance,
            "trend": trend,
            "productivity_score": productivity,
            "no_face": False,
            "user_present": True,
            "warming_up": self.is_warming_up
        }

    def _compute_productivity_score(self, score: int, context: str, override_state: str = None) -> int:
        """Weight the attention score by its context productivity."""
        if override_state == "ACTIVE STUDY":
            return score # 100% credit for studying
        if override_state == "PHONE DISTRACTION":
            return int(score * 0.1) # Minimum credit for phone distraction

        multipliers = {
            "DEEP WORK": 1.0,
            "PASSIVE LEARN": 1.0,
            "COMMUNICATION": 0.7,
            "TRANSITION": 0.4,
            "ENTERTAINMENT": 0.1
        }
        mult = multipliers.get(context, 0.4)
        return int(score * mult)

    def _compute_screen_relevance(self, context: str, gaze: float, typing: float) -> float:
        """Derives screen relevance from context and active signals."""
        if context == "DEEP WORK":
            if typing > 0.3 or gaze > 0.5:
                return 1.0
            elif typing > 0.1:
                return 0.7
            else:
                return 0.4
        elif context in ("ENTERTAINMENT", "PASSIVE LEARN"):
            # Passive contexts: high relevance simply requires looking at the screen
            return 1.0 if gaze > 0.5 else 0.5
        elif context == "COMMUNICATION":
            return 0.9 if gaze > 0.3 else 0.6
        else:  # TRANSITION
            return 0.5

    def _classify_state(self, score: int, context: str) -> str:
        """Maps a numeric score + context to a discrete attention state."""
        if score >= 80:
            return "DEEP FOCUS"
        elif score >= 60:
            return "ACTIVE ENGAGEMENT"
        elif score >= 40:
            return "PASSIVE WATCHING" if context in ("PASSIVE LEARN", "ENTERTAINMENT") else "SURFACE SKIMMING"
        elif score >= 20:
            return "FRAGMENTED"
        else:
            return "DISENGAGED"

    def _detect_fatigue(self) -> bool:
        """
        Detects fatigue when scores show a consistent downward trend 
        over the last 5 cycles (2.5 minutes).
        """
        if len(self.score_history) < 5:
            return False
        
        recent = self.score_history[-5:]
        peak = max(self.score_history[:-5]) if len(self.score_history) > 5 else recent[0]
        
        # Fatigue = all recent scores declining AND current is 15+ points below earlier peak
        is_declining = all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1))
        dropped_significantly = (peak - recent[-1]) >= 15
        
        return is_declining and dropped_significantly

    def _compute_trend(self) -> str:
        """Computes the trend direction from the rolling score history."""
        if len(self.score_history) < 4:
            return "STABLE"
        
        first_half = self.score_history[:len(self.score_history) // 2]
        second_half = self.score_history[len(self.score_history) // 2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        diff = avg_second - avg_first
        if diff > 5:
            return "IMPROVING"
        elif diff < -5:
            return "DECLINING"
        else:
            return "STABLE"
