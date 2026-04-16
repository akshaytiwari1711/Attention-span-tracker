import time
import mss
import numpy as np
import win32gui
import win32process
import psutil
import cv2
import threading

class ScreenCaptureService:
    def __init__(self):
        self.sct = mss.mss()
        self.last_capture = None
        self.capture_lock = threading.Lock()
        
        # Caching to reduce capture frequency
        self.last_capture_time = 0
        self.capture_interval = 0.2  # Update screen every 200ms for ultra-lag-free feel

    def get_active_window_metadata(self):
        """Returns the title and process name of the currently active window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            if pid > 0:
                process = psutil.Process(pid)
                process_name = process.name()
            else:
                process_name = "Unknown"
                
            return {
                "title": title,
                "process_name": process_name
            }
        except Exception as e:
            return {"title": "Unknown", "process_name": "error"}

    def capture_screen(self):
        """Captures the primary monitor and returns an RGB numpy array. Uses cache for performance."""
        current_time = time.time()
        
        # Use cached capture if recent enough
        if self.last_capture is not None and (current_time - self.last_capture_time) < self.capture_interval:
            return self.last_capture.copy()
            
        try:
            # Monitor 1 is usually the primary monitor
            monitor = self.sct.monitors[1]
            sct_img = self.sct.grab(monitor)
            # Convert to numpy array
            img = np.array(sct_img)
            
            # Store the capture for the dashboard (with lock)
            with self.capture_lock:
                self.last_capture = img.copy()
                self.last_capture_time = current_time

            # mss returns BGRA, convert or just return for OpenCV/Tesseract processing
            return img
        except Exception as e:
            return self.last_capture if self.last_capture is not None else None

    def get_jpeg_thumbnail(self) -> bytes | None:
        """Encodes a responsive thumbnail of the screen for smooth dashboard."""
        with self.capture_lock:
            if self.last_capture is None:
                return None
            img = self.last_capture.copy()

        # MSS returns BGRA. Tesseract/OpenCV usually want RGB/BGR.
        # Resize to responsive size - balance speed and visibility
        h, w = img.shape[:2]
        thumb_w = 400  # Responsive resolution for readability
        thumb_h = int((thumb_w / w) * h)
        thumb = cv2.resize(img, (thumb_w, thumb_h), interpolation=cv2.INTER_NEAREST)

        # Convert BGRA to BGR for encoding
        if thumb.shape[2] == 4:
            thumb = cv2.cvtColor(thumb, cv2.COLOR_BGRA2BGR)

        ret, buffer = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 35, cv2.IMWRITE_JPEG_OPTIMIZE, 1])
        if ret:
            return buffer.tobytes()
        return None

    def close(self):
        self.sct.close()

if __name__ == "__main__":
    service = ScreenCaptureService()
    print("Metadata:", service.get_active_window_metadata())
    screen = service.capture_screen()
    if screen is not None:
        print("Captured Screen Shape:", screen.shape)
    service.close()
