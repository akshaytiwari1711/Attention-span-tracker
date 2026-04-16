import os
import sys
import time
import cv2
import threading
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

class WebcamGazeService:
    """
    Advanced Webcam Service using MediaPipe Tasks API for Gaze and Object Detection.
    Draws real-time overlays for eyes and distractions.
    """

    def __init__(self, camera_index=0):
        self.camera_available = False
        self.cap = None
        
        # 1. Face Landmarker Initialization
        try:
            face_model_path = os.path.join(os.getcwd(), 'inference', 'face_landmarker.task')
            face_options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=face_model_path),
                running_mode=vision.RunningMode.IMAGE,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                min_face_detection_confidence=0.3,
                min_face_presence_confidence=0.3,
                min_tracking_confidence=0.3,
            )
            self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)
            print("[WebcamGazeService] Face Landmarker loaded.", flush=True)
        except Exception as e:
            self.face_landmarker = None
            print(f"[WebcamGazeService] Warning: Face Landmarker failed: {e}", flush=True)

        # 2. Object Detector Initialization
        try:
            obj_model_path = os.path.join(os.getcwd(), 'inference', 'efficientdet.tflite')
            obj_options = vision.ObjectDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=obj_model_path),
                score_threshold=0.35,
                running_mode=vision.RunningMode.IMAGE
            )
            self.detector = vision.ObjectDetector.create_from_options(obj_options)
            print("[WebcamGazeService] Object Detector loaded.", flush=True)
        except Exception as e:
            self.detector = None
            print(f"[WebcamGazeService] Warning: Object Detector failed: {e}", flush=True)

        # Try to open camera
        self._init_camera_with_fallback(camera_index)

        # Tracking variables
        self.frame_lock = threading.Lock()
        self.streaming_lock = threading.Lock()
        self.last_frame = None
        self.streaming_frame = None
        self.last_face_result = None
        
        self.cached_features = self._neutral_features()
        self.detected_objects = []
        self.last_detection_time = 0
        self.detection_interval = 0.1
        
        self.frame_count = 0
        self._start_streaming_thread()

    def _init_camera_with_fallback(self, preferred_index: int = 0):
        # Try backends in order of preference (None = system default is most compatible)
        backends = [None, cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        
        for idx in [preferred_index, 0, 1, 2, 3]:
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(idx, backend) if backend else cv2.VideoCapture(idx)
                    if cap.isOpened():
                        # Set camera properties for better performance
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
                        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus if available
                        
                        # Give camera time to initialize
                        time.sleep(0.5)
                        
                        # Try to read a test frame with timeout
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            self.cap = cap
                            self.camera_available = True
                            print(f"[WebcamGazeService] Camera {idx} (backend {backend}) opened and tested successfully.", flush=True)
                            return
                        else:
                            # Camera opened but frame read failed - still might work after warmup
                            if cap.isOpened():
                                # Don't release yet, give it another chance
                                self.cap = cap
                                self.camera_available = True
                                print(f"[WebcamGazeService] Camera {idx} opened (first frame pending warmup).", flush=True)
                                return
                            cap.release()
                except Exception as e:
                    print(f"[WebcamGazeService] Failed to open camera {idx} with backend {backend}: {str(e)[:80]}", flush=True)
                    continue
        
        print("[WebcamGazeService] No working camera found after testing all indices and backends.", flush=True)

    def _start_streaming_thread(self):
        def _capture_loop():
            warmup_frames = 0
            max_warmup = 30  # 30 frames to warm up camera
            
            while self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                
                # During warmup phase, retry if frame is invalid
                if not ret or frame is None or frame.size == 0:
                    if warmup_frames < max_warmup:
                        warmup_frames += 1
                        time.sleep(0.05)
                        continue
                    
                    # Retry reading frame several times before giving up
                    retries = 0
                    while not ret and retries < 10:
                        time.sleep(0.1)
                        ret, frame = self.cap.read()
                        retries += 1
                    
                    if not ret or frame is None or frame.size == 0:
                        # Attempt to reopen camera before disabling
                        print("[WebcamGazeService] Frame read failed, attempting to reopen camera...")
                        if self.cap:
                            self.cap.release()
                        self.cap = None
                        self.camera_available = False
                        time.sleep(1)  # Wait before trying to reopen
                        self._init_camera_with_fallback(0)
                        if self.camera_available:
                            print("[WebcamGazeService] Camera reopened successfully, continuing capture.")
                            warmup_frames = 0
                            continue
                        else:
                            print("[WebcamGazeService] Failed to reopen camera, disabling webcam input.")
                            break

                warmup_frames = 0  # Reset warmup counter on successful read
                self.frame_count += 1
                processed_frame = frame.copy()
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                
                # 1. Face Tracking (Every Frame)
                face_result = None
                if self.face_landmarker:
                    try:
                        face_result = self.face_landmarker.detect(mp_image)
                    except Exception as e:
                        print(f"[WebcamGazeService] Face detection error: {str(e)[:80]}", flush=True)
                        face_result = None
                
                # 2. Object Detection (Every 5th frame)
                if self.detector and self.frame_count % 5 == 0:
                    try:
                        detection_result = self.detector.detect(mp_image)
                        current_objects = []
                        for detection in detection_result.detections:
                            category = detection.categories[0]
                            if category.category_name in ['cell phone', 'mobile phone', 'smartphone', 'book', 'laptop', 'bottle']:
                                current_objects.append({
                                    'name': category.category_name,
                                    'bbox': detection.bounding_box,
                                    'score': category.score
                                })
                        self.detected_objects = current_objects
                    except Exception as e:
                        print(f"[WebcamGazeService] Object detection error: {str(e)[:80]}", flush=True)

                # 3. Draw Overlays
                self._draw_overlays(processed_frame, face_result, self.detected_objects)

                with self.streaming_lock:
                    self.streaming_frame = processed_frame
                with self.frame_lock:
                    self.last_frame = frame
                    self.last_face_result = face_result

            print("[WebcamGazeService] Webcam capture thread exiting.", flush=True)

        self.streaming_thread = threading.Thread(target=_capture_loop, daemon=True)
        self.streaming_thread.start()

    def _draw_overlays(self, frame, face_result, objects):
        h, w = frame.shape[:2]
        
        # Draw Eyes
        if face_result and face_result.face_landmarks:
            for face_lms in face_result.face_landmarks:
                # Use Iris landmarks for refined eye boxes
                # Left Iris: 468, Right Iris: 473
                for center_idx in [468, 473]:
                    lm = face_lms[center_idx]
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.rectangle(frame, (cx-12, cy-12), (cx+12, cy+12), (0, 0, 255), 2)
                    cv2.putText(frame, "EYE", (cx-12, cy-18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Draw Objects
        for obj in objects:
            bbox = obj['bbox']
            x, y, bw, bh = int(bbox.origin_x), int(bbox.origin_y), int(bbox.width), int(bbox.height)
            if obj['name'] in ['cell phone', 'mobile phone', 'smartphone']:
                color = (0, 255, 255)  # Yellow
                label = 'PHONE'
            elif obj['name'] == 'book':
                color = (0, 255, 0)  # Green
                label = 'BOOK'
            elif obj['name'] == 'bottle':
                color = (255, 0, 0)  # Blue
                label = 'PEN'
            else:
                color = (0, 255, 255)  # Yellow default
                label = obj['name'].upper()
            
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)
            cv2.putText(frame, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    def capture_frame_and_extract_features(self) -> dict:
        """Extracts metrics for the engine.
        
        CRITICAL FIX: Check for ACTUAL face landmarks detection, not camera_available flag.
        camera_available is only for preventing frame read errors, not for gating face detection.
        """
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_interval:
            return self.cached_features

        # Get latest face detection result (can exist even if stream errors later)
        with self.frame_lock:
            result = getattr(self, 'last_face_result', None)
        
        # Check for face detection: face detected if face landmarks valid OR both eyes detected
        face_detected = False
        eyes_detected = 0
        face_landmarks_valid = result and result.face_landmarks and len(result.face_landmarks) > 0
        
        if face_landmarks_valid:
            lms = result.face_landmarks[0]
            
            # Check for left iris landmark (468)
            left_eye_detected = len(lms) > 468
            if left_eye_detected:
                eyes_detected += 1
            
            # Check for right iris landmark (473)
            right_eye_detected = len(lms) > 473
            if right_eye_detected:
                eyes_detected += 1
        
        # Required Logic: face detected if face landmarks valid OR both eyes detected
        if face_landmarks_valid or (eyes_detected >= 2):
            face_detected = True
        
        if face_detected:
            self.last_detection_time = current_time
            lms = result.face_landmarks[0]
            
            # Nose Tip (1) - use if available
            yaw = 0.0
            pitch = 0.0
            if len(lms) > 1:
                nose = lms[1]
                yaw = (nose.x - 0.5) * 2
                pitch = (nose.y - 0.5) * 2
            
            # Gaze calculation - use iris if available
            gaze_x = 0.0
            gaze_y = 0.0
            if eyes_detected >= 1 and len(lms) > 468:
                iris = lms[468]  # Use left iris
                if len(lms) > 1:
                    nose = lms[1]
                    gaze_x = (iris.x - nose.x) * 5
                    gaze_y = (iris.y - nose.y) * 5

            features = {
                "face_detected": True,
                "head_pose": {"pitch": round(pitch, 3), "yaw": round(yaw, 3), "roll": 0.0},
                "gaze_vector": {"x": round(gaze_x, 3), "y": round(gaze_y, 3)},
                "blink_detected": False,
                "posture_score": 1.0 if abs(pitch) < 0.3 else 0.5,
                "eyes_detected": eyes_detected,
                "detected_objects": [o['name'] for o in self.detected_objects],
                "status_message": "Face detected"
            }
            self.cached_features = features
            return features
        
        # No face landmarks detected
        f = self._neutral_features()
        if not self.camera_available:
            f["status_message"] = "No camera available"
        else:
            f["status_message"] = "Face is not detected"
        f["detected_objects"] = [o['name'] for o in self.detected_objects]
        return f

    def get_jpeg_frame(self) -> bytes | None:
        with self.streaming_lock:
            if self.streaming_frame is None: return None
            frame = self.streaming_frame.copy()
        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return buffer.tobytes() if ret else None

    def _neutral_features(self) -> dict:
        return {
            "face_detected": False,
            "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "gaze_vector": {"x": 0.0, "y": 0.0},
            "blink_detected": False,
            "posture_score": 0.0,
            "eyes_detected": 0,
            "detected_objects": [],
            "status_message": "Face is not detected"
        }

    def close(self):
        if self.cap: self.cap.release()
        if self.face_landmarker: self.face_landmarker.close()
        if self.detector: self.detector.close()

if __name__ == "__main__":
    service = WebcamGazeService()
    time.sleep(2)
    print(service.capture_frame_and_extract_features())
    service.close()
