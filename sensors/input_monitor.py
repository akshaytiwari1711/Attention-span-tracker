from pynput import mouse, keyboard
import time
import threading

class InputMonitorService:
    def __init__(self):
        self.keystrokes = 0
        self.backspaces = 0
        self.mouse_moves = 0
        self.mouse_clicks = 0
        self.scroll_events = 0
        
        self.last_activity_time = time.time()
        self.lock = threading.Lock()
        
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll)
        
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press)
            
    def start(self):
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
    def stop(self):
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

    def on_move(self, x, y):
        with self.lock:
            # We just count moving events - in reality, evaluate distance
            self.mouse_moves += 1
            self.last_activity_time = time.time()

    def on_click(self, x, y, button, pressed):
        if pressed:
            with self.lock:
                self.mouse_clicks += 1
                self.last_activity_time = time.time()

    def on_scroll(self, x, y, dx, dy):
        with self.lock:
            self.scroll_events += abs(dy)
            self.last_activity_time = time.time()

    def on_press(self, key):
        with self.lock:
            self.keystrokes += 1
            self.last_activity_time = time.time()
            if key == keyboard.Key.backspace or key == keyboard.Key.delete:
                self.backspaces += 1

    def get_metrics_and_reset(self):
        """Returns the accumulated metrics over the interval and resets counters."""
        with self.lock:
            metrics = {
                "keystrokes": self.keystrokes,
                "backspaces": self.backspaces,
                "backspace_ratio": (self.backspaces / self.keystrokes) if self.keystrokes > 0 else 0,
                "mouse_moves": self.mouse_moves,
                "mouse_clicks": self.mouse_clicks,
                "scroll_events": self.scroll_events,
                "total_input_events": self.keystrokes + self.mouse_moves + self.mouse_clicks + self.scroll_events,
                "idle_seconds": time.time() - self.last_activity_time
            }
            # Reset counters
            self.keystrokes = 0
            self.backspaces = 0
            self.mouse_moves = 0
            self.mouse_clicks = 0
            self.scroll_events = 0
            
        return metrics

if __name__ == "__main__":
    monitor = InputMonitorService()
    monitor.start()
    print("Capturing input for 5 seconds...")
    time.sleep(5)
    print("Metrics:", monitor.get_metrics_and_reset())
    monitor.stop()
