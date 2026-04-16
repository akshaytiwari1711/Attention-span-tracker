from collections import deque
import math


class SignalInterpreter:
    """
    Translates raw sensor data into normalized attention signals (0.0–1.0).
    Maintains rolling history to compute stability and detect deterioration.
    """

    def __init__(self, history_size: int = 12):  # Reduced from 10 for 5s cycles (~1 min total)
        # Rolling windows for stability calculations (last ~1 min at 5s cycles)
        self.gaze_history = deque(maxlen=history_size)
        self.posture_history = deque(maxlen=history_size)
        self.interaction_history = deque(maxlen=history_size)

    def interpret(self, gaze_features: dict, input_metrics: dict) -> dict:
        """
        Translates raw sensor data from the 30-sec window into normalized signals 0.0–1.0.
        Uses rolling history to weight current readings with recent trends.
        """
        # --- 1. Gaze Focus (0.0 to 1.0) ---
        raw_gaze = self._interpret_gaze(gaze_features)
        self.gaze_history.append(raw_gaze)
        # Blend: 70% current reading + 30% rolling average for smoothing
        gaze_focus = self._smooth(raw_gaze, self.gaze_history)

        # --- 2. Posture Stability (0.0 to 1.0) ---
        raw_posture = self._interpret_posture(gaze_features)
        self.posture_history.append(raw_posture)
        posture_stability = self._smooth(raw_posture, self.posture_history)

        # --- 3. Interaction Engagement (0.0 to 1.0) ---
        raw_interaction = self._interpret_interaction(input_metrics)
        self.interaction_history.append(raw_interaction)
        interaction_engagement = self._smooth(raw_interaction, self.interaction_history)

        return {
            "gaze_focus": round(gaze_focus, 3),
            "posture_stability": round(posture_stability, 3),
            "interaction_engagement": round(interaction_engagement, 3),
        }

    # ------------------------------------------------------------------
    # Per-signal interpretation
    # ------------------------------------------------------------------

    def _interpret_gaze(self, gaze_features: dict) -> float:
        """Maps face/eye detection to a gaze focus score."""
        face_detected = gaze_features.get("face_detected", False)
        eyes_count = gaze_features.get("eyes_detected", 0)
        gaze_vector = gaze_features.get("gaze_vector", {"x": 0.0, "y": 0.0})

        if not face_detected:
            return 0.0

        # Base score from eye count
        if eyes_count >= 2:
            base = 1.0
        elif eyes_count == 1:
            base = 0.6
        else:
            return 0.2  # Face found, eyes not visible (looking away / closed)

        # Penalize off-center gaze: the further from center, the more likely distracted
        gaze_offset = math.sqrt(gaze_vector["x"] ** 2 + gaze_vector["y"] ** 2)
        # gaze_offset ~0 = centered, ~0.5 = edge of face ROI
        gaze_penalty = min(gaze_offset * 0.5, 0.3)  # cap penalty at 0.3

        return max(0.0, base - gaze_penalty)

    def _interpret_posture(self, gaze_features: dict) -> float:
        """Maps face position and head pose to a posture stability score."""
        if not gaze_features.get("face_detected", False):
            return 0.0

        base_posture = gaze_features.get("posture_score", 0.0)
        head_pose = gaze_features.get("head_pose", {})

        # Penalize extreme yaw (looking sideways) or pitch (looking down — phone check)
        yaw = abs(head_pose.get("yaw", 0.0))
        pitch = abs(head_pose.get("pitch", 0.0))

        # yaw/pitch are normalized to [-1, 1]; values > 0.3 suggest turning away
        pose_penalty = 0.0
        if yaw > 0.3:
            pose_penalty += (yaw - 0.3) * 0.5
        if pitch > 0.3:
            pose_penalty += (pitch - 0.3) * 0.5

        return max(0.0, min(1.0, base_posture - pose_penalty))

    def _interpret_interaction(self, input_metrics: dict) -> float:
        """Maps keystroke/mouse/scroll activity to an engagement score."""
        keystrokes = input_metrics.get("keystrokes", 0)
        mouse_moves = input_metrics.get("mouse_moves", 0)
        mouse_clicks = input_metrics.get("mouse_clicks", 0)
        scrolls = input_metrics.get("scroll_events", 0)
        backspace_ratio = input_metrics.get("backspace_ratio", 0.0)

        # Weighted combination normalized to a theoretical 5-sec max
        # ~25 keystrokes/5s for fast typing, ~100 mouse moves, ~6 scrolls
        intensity = (
            (keystrokes / 25.0) * 0.4
            + (mouse_clicks / 4.0) * 0.2
            + (mouse_moves / 100.0) * 0.2
            + (scrolls / 6.0) * 0.2
        )
        engagement = min(1.0, max(0.0, intensity))

        # Penalize high backspace ratio — signals interrupted concentration
        if backspace_ratio > 0.3:
            engagement *= 0.85

        return engagement

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _smooth(current: float, history: deque) -> float:
        """Exponential smoothing: 70% current + 30% rolling average."""
        if len(history) < 2:
            return current
        avg = sum(history) / len(history)
        return current * 0.7 + avg * 0.3
