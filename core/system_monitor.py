import psutil
import os
from collections import deque

class SystemMonitor:
    """Monitors OS-level CPU, RAM, and Battery status with rolling averaging."""
    
    cpu_history = deque(maxlen=3)
    _initialized = False
    
    @classmethod
    def get_metrics(cls):
        try:
            if not cls._initialized:
                psutil.cpu_percent(interval=None) # Set baseline
                psutil.virtual_memory() # Warm up
                cls._initialized = True

            # CPU: (Fix 04)
            cpu_now = psutil.cpu_percent(interval=0.1 if len(cls.cpu_history) == 0 else None)
            cls.cpu_history.append(cpu_now)
            avg_cpu = sum(cls.cpu_history) / len(cls.cpu_history)
            
            # RAM: (Fix 04)
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            # available_gb might be missing on some systems, use available
            available_gb = getattr(mem, 'available', mem.free) / (1024**3)
            used_gb = total_gb - available_gb
            ram_percent = mem.percent
            
            # Fallback if total_gb is 0 for some weird reason
            if total_gb <= 0:
                 ram_label = f"{ram_percent:.0f}%"
            else:
                 ram_label = f"{used_gb:.1f} / {total_gb:.1f} GB ({ram_percent:.0f}%)"
            
            # Battery
            battery = psutil.sensors_battery()
            battery_data = None
            if battery:
                battery_data = {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "label": f"{battery.percent}% ({'AC' if battery.power_plugged else 'Batt'})"
                }
            
            return {
                "cpu_percent": int(avg_cpu),
                "ram_percent": int(ram_percent),
                "ram_label": ram_label,
                "battery": battery_data
            }
        except Exception as e:
            print(f"[SystemMonitor] Sync Error: {e}")
            return {
                "cpu_percent": 0,
                "ram_percent": 0,
                "ram_label": "Error",
                "battery": None
            }

    @staticmethod
    def get_optimization_factor():
        """Returns a multiplier for sleep time based on battery status."""
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 30:
                return 2.0  # Slow down loop to save power
            return 1.0
        except:
            return 1.0
