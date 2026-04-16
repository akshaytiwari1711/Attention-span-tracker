import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sensors.screen import ScreenCaptureService
from sensors.webcam import WebcamGazeService
from sensors.input_monitor import InputMonitorService
from inference.context_classifier import ContextClassifier
from inference.signal_interpreter import SignalInterpreter
from core.attention_scorer import AttentionScorer
from core.insight_generator import InsightGenerator
from output.dispatcher import RealTimeDispatcher

print("Initializing...")
screen_sensor = ScreenCaptureService()
gaze_sensor = WebcamGazeService()
input_sensor = InputMonitorService()
input_sensor.start()

classifier = ContextClassifier()
interpreter = SignalInterpreter()
scorer = AttentionScorer()
insight_gen = InsightGenerator()
dispatcher = RealTimeDispatcher()

print("Capturing...")
win_meta = screen_sensor.get_active_window_metadata()
screen_img = screen_sensor.capture_screen()
raw_gaze = gaze_sensor.capture_frame_and_extract_features()
raw_input = input_sensor.get_metrics_and_reset()

print("Inference...")
context = classifier.classify(win_meta, screen_img)
signals = interpreter.interpret(raw_gaze, raw_input)
score_data = scorer.compute_score(signals, context)
insights = insight_gen.generate(score_data, 0.1, context)

print("Test complete. Score:", score_data)
input_sensor.stop()
screen_sensor.close()
gaze_sensor.close()
