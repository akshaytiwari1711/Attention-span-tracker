import os
import shutil
import cv2
import numpy as np
import time

# Try to import pytesseract; if Tesseract binary is missing, OCR will be disabled gracefully
try:
    import pytesseract
    # Auto-detect tesseract location
    _tess = shutil.which("tesseract")
    if _tess is None:
        _candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in _candidates:
            if os.path.isfile(p):
                _tess = p
                break
    if _tess:
        pytesseract.pytesseract.tesseract_cmd = _tess
        _OCR_AVAILABLE = True
    else:
        _OCR_AVAILABLE = False
        print("[ContextClassifier] Tesseract binary not found — OCR disabled, using metadata-only classification.")
except ImportError:
    _OCR_AVAILABLE = False
    print("[ContextClassifier] pytesseract not installed — OCR disabled.")

class ContextClassifier:
    def __init__(self):
        # Base categories
        self.CATEGORIES = [
            "DEEP WORK", "PASSIVE LEARN", "ENTERTAINMENT", "COMMUNICATION", "TRANSITION"
        ]
        
        # Expanded keyword sets for classification
        self.ED_KEYWORDS = {
            "tutorial", "lecture", "course", "learn", "how to", "explained",
            "lesson", "chapter", "study", "education", "training", "workshop",
            "documentation", "docs", "reference", "guide", "algorithm",
            "data structure", "machine learning", "deep learning",
            "unit", "chapter",
        }
        self.CODE_KEYWORDS = {
            "def", "class", "import", "function", "return", "int", "var",
            "const", "async", "await", "void", "public", "private", "static",
            "for", "while", "if", "elif", "else", "try", "except", "catch",
            "console.log", "print(", "self.", "this.", "=>", "lambda",
        }
        self.COMM_KEYWORDS = {
            "chat", "message", "inbox", "meeting", "call", "reply",
            "compose", "sent", "draft", "subject:", "to:", "from:",
            "typing...", "online", "last seen",
        }
        self.ENTERTAINMENT_KEYWORDS = {
            "watch", "episode", "season", "movie", "trailer", "gaming",
            "stream", "subscribe", "like", "comment", "share", "trending",
            "feed", "stories", "reel", "shorts", "playlist",
        }

        # Process name mappings for instant classification
        self.DEEP_WORK_PROCESSES = {
            "code", "code.exe", "idea64.exe", "pycharm64.exe", "pycharm",
            "devenv.exe", "sublime_text.exe", "notepad++.exe", "vim",
            "atom.exe", "webstorm64.exe", "clion64.exe", "rider64.exe",
            "cursor.exe", "windsurf.exe", "warp.exe", "terminal",
            "powershell.exe", "cmd.exe", "windowsterminal.exe",
            "word.exe", "winword.exe", "excel.exe", "libreoffice",
            "notion.exe", "obsidian.exe",
        }
        self.COMM_PROCESSES = {
            "slack.exe", "teams.exe", "zoom.exe", "discord.exe",
            "telegram.exe", "whatsapp.exe", "signal.exe", "outlook.exe",
            "thunderbird.exe", "skype.exe", "webex.exe",
        }
        self.ENTERTAINMENT_PROCESSES = {
            "spotify.exe", "vlc.exe", "wmplayer.exe", "netflix.exe",
            "steam.exe", "epicgameslauncher.exe",
        }

        # URL/domain patterns for browser title classification
        self.ED_DOMAINS = {
            "coursera", "udemy", "edx", "khanacademy", "mit.edu",
            "stackoverflow", "geeksforgeeks", "leetcode", "hackerrank",
            "w3schools", "mdn", "docs.python", "docs.google",
            "arxiv", "scholar.google", "wikipedia",
        }
        self.ENTERTAINMENT_DOMAINS = {
            "netflix", "primevideo", "hotstar", "hulu", "disneyplus",
            "twitch", "reddit", "twitter", "x.com", "instagram",
            "facebook", "tiktok", "9gag", "buzzfeed",
        }
        
        # Performance optimization: cache OCR results
        self.last_ocr_time = 0
        self.ocr_cache_duration = 10  # Cache OCR for 10 seconds
        self.cached_ocr_text = ""

    def _extract_text_from_screen(self, screen_img) -> str:
        """Runs OCR on the given screen image to extract text."""
        if screen_img is None or not _OCR_AVAILABLE:
            return ""
        
        current_time = time.time()
        if current_time - self.last_ocr_time < self.ocr_cache_duration:
            return self.cached_ocr_text
            
        self.last_ocr_time = current_time
        
        try:
            # mss captures in BGRA format — convert to grayscale properly
            if screen_img.shape[2] == 4:
                gray = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2GRAY)
            else:
                gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            
            # Resize to speed up OCR (half resolution)
            h, w = gray.shape
            gray = cv2.resize(gray, (w // 2, h // 2))
            
            text = pytesseract.image_to_string(gray)
            self.cached_ocr_text = text.lower()
            return self.cached_ocr_text
        except Exception as e:
            print("[ContextClassifier] OCR Error:", e)
            return ""

    def classify(self, window_metadata: dict, screen_img: np.ndarray = None, detected_objects: list = None) -> str:
        """
        Takes window metadata (title, process_name) and full screen image.
        Returns one of the context categories.
        """
        title = window_metadata.get("title", "").lower()
        process = window_metadata.get("process_name", "").lower()
        
        # --- Layer 1: Fast process name lookup ---
        if process in self.DEEP_WORK_PROCESSES:
            return "DEEP WORK"
        if process in self.COMM_PROCESSES:
            return "COMMUNICATION"
        if process in self.ENTERTAINMENT_PROCESSES:
            return "ENTERTAINMENT"

        # --- Layer 2: Browser title + domain analysis ---
        # Browsers carry the page title — this is the key to YouTube vs Netflix
        is_browser = any(b in process for b in ("chrome", "firefox", "msedge", "brave", "opera", "safari"))
        
        if is_browser:
            # Check for known entertainment domains in the title
            if any(d in title for d in self.ENTERTAINMENT_DOMAINS):
                # But is it educational entertainment (e.g., YouTube lecture)?
                if any(k in title for k in self.ED_KEYWORDS):
                    return "PASSIVE LEARN"
                return "ENTERTAINMENT"
            
            # Check for known educational domains
            if any(d in title for d in self.ED_DOMAINS):
                return "PASSIVE LEARN"

            # Check for communication platforms in browser
            if any(k in title for k in ("gmail", "outlook", "mail", "slack", "discord", "teams")):
                return "COMMUNICATION"

        # --- Layer 3: Title keyword analysis (non-browser or ambiguous) ---
        is_educational = any(k in title for k in self.ED_KEYWORDS)
        is_entertainment = any(k in title for k in self.ENTERTAINMENT_KEYWORDS)

        if "youtube" in title:
            return "PASSIVE LEARN" if is_educational else "ENTERTAINMENT"
        
        if is_educational and not is_entertainment:
            return "PASSIVE LEARN"

        # --- Layer 4: OCR text extraction for deeper context ---
        screen_text = self._extract_text_from_screen(screen_img)
        
        if not screen_text:
            return "TRANSITION"

        # Score each category by keyword hits
        code_hits = sum(1 for k in self.CODE_KEYWORDS if k in screen_text)
        ed_hits = sum(1 for k in self.ED_KEYWORDS if k in screen_text)
        comm_hits = sum(1 for k in self.COMM_KEYWORDS if k in screen_text)
        ent_hits = sum(1 for k in self.ENTERTAINMENT_KEYWORDS if k in screen_text)
        
        scores = {
            "DEEP WORK": code_hits,
            "PASSIVE LEARN": ed_hits,
            "COMMUNICATION": comm_hits,
            "ENTERTAINMENT": ent_hits,
        }
        
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        if best_score >= 2:
            return best_category

        # Default: transitioning or no dominant activity
        return "TRANSITION"

if __name__ == "__main__":
    clf = ContextClassifier()
    # Quick smoke tests
    print("VSCode:", clf.classify({"title": "main.py - VSCode", "process_name": "Code.exe"}, None))
    print("Netflix:", clf.classify({"title": "Stranger Things - Netflix", "process_name": "chrome.exe"}, None))
    print("YouTube Lecture:", clf.classify({"title": "MIT Lecture: Algorithm Design - YouTube", "process_name": "chrome.exe"}, None))
    print("YouTube Music:", clf.classify({"title": "Lofi Beats - YouTube", "process_name": "chrome.exe"}, None))
    print("Slack:", clf.classify({"title": "Slack | general", "process_name": "slack.exe"}, None))
