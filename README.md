# 🎯 Attention Analysis System

A real-time Computer Vision and Behavioral AI system that analyzes user attention and productivity using webcam-based behavioral signals, screen activity, interaction patterns, and contextual task classification.

---

# 📌 Problem Statement

Traditional productivity trackers measure application usage and screen time but fail to determine whether a user is genuinely focused or simply present in front of a screen.

The Attention Analysis System addresses this problem by combining computer vision, behavioral analysis, and context-aware scoring to estimate real-time attention and productivity levels.

The system evaluates user engagement through gaze stability, posture analysis, interaction patterns, and task context, then presents the results through a live analytics dashboard.

---

# 🚀 Features

## Real-Time Monitoring

* Live webcam feed
* Live screen preview
* Continuous attention tracking
* Real-time dashboard updates

## Attention Intelligence

* Face detection
* Gaze stability analysis
* Posture scoring
* Interaction focus tracking
* Attention score calculation

## Productivity Intelligence

* Context classification
* Active application analysis
* Educational content detection
* Entertainment detection
* Productivity scoring

## Dashboard Analytics

* Attention score visualization
* Productivity score visualization
* Activity context display
* Trend analysis
* Live monitoring interface

---

# 🏗️ System Architecture

```text
User
 │
 ├── Webcam Sensor
 │      │
 │      ├── Face Detection
 │      ├── Gaze Analysis
 │      └── Posture Analysis
 │
 ├── Screen Capture
 │      │
 │      └── Active Task Preview
 │
 ├── Interaction Tracking
 │      │
 │      ├── Keyboard Activity
 │      └── Mouse Activity
 │
 └── Context Classification
        │
        ├── Deep Work
        ├── Passive Learning
        └── Entertainment

                ↓

         Attention Scorer

                ↓

       Productivity Engine

                ↓

            API Layer

                ↓

         Live Dashboard
```

---

# 🧠 Attention Scoring Logic

The system calculates attention using a weighted behavioral model:

```python
attention = (gaze * 0.5) + (posture * 0.3) + (interaction * 0.2)
attention_score = attention * 100
```

### Weight Distribution

| Signal            | Weight |
| ----------------- | ------ |
| Gaze Stability    | 50%    |
| Posture Score     | 30%    |
| Interaction Focus | 20%    |

---

# 📊 Attention States

| Score Range | State                |
| ----------- | -------------------- |
| 80 – 100    | Deep Focus           |
| 60 – 79     | Active Study         |
| 40 – 59     | Active Engagement    |
| 20 – 39     | Fragmented Attention |
| 0 – 19      | Disengaged           |

---

# 🎓 Context Classification

The system categorizes user activities into:

### Deep Work

* VS Code
* PyCharm
* Development tools
* Writing environments
* Technical applications

### Passive Learning

* Educational videos
* Online lectures
* Tutorials
* Learning platforms

### Entertainment

* Streaming platforms
* Social media
* Movies and videos
* Gaming content

---

# 📁 Project Structure

```text
attention-analysis/
│
├── run_dashboard.py
│
├── sensors/
│   ├── webcam.py
│   └── screen.py
│
├── core/
│   └── attention_scorer.py
│
├── inference/
│   └── context_classifier.py
│
├── dashboard/
│   └── index.html
│
├── tests/
│
└── requirements.txt
```

---

# 🔄 System Workflow

1. Application starts.
2. Webcam captures user frames.
3. Screen capture module generates task previews.
4. Context classifier identifies current activity.
5. Face detection validates user presence.
6. Gaze stability is calculated.
7. Posture score is estimated.
8. Interaction activity is measured.
9. Attention score is generated.
10. Productivity score is calculated.
11. Results are sent through APIs.
12. Dashboard updates in real time.

---

# 🔌 API Endpoints

## GET /api/latest

Returns the latest analytics data.

### Sample Response

```json
{
  "attention_score": 82,
  "productivity_score": 78,
  "context": "DEEP_WORK",
  "trend": "IMPROVING"
}
```

---

## GET /api/video_feed

Returns the live webcam stream.

---

## GET /api/screen_preview

Returns the latest screen preview image.

---

# ⚙️ Technology Stack

## Programming Language

* Python

## Computer Vision

* OpenCV

## Backend

* ThreadingHTTPServer
* REST-style APIs
* JSON Data Exchange

## Frontend

* HTML
* CSS
* JavaScript

## Processing

* Real-Time Analytics
* Behavioral Modeling
* Context Classification

---

# 🧩 Core Modules

## run_dashboard.py

Handles server initialization, API routing, dashboard communication, and stream delivery.

## webcam.py

Captures live webcam frames and provides visual input for analysis.

## screen.py

Captures screen previews and supplies task visualization data.

## context_classifier.py

Analyzes active applications and classifies task context.

## attention_scorer.py

Calculates attention and productivity scores using behavioral signals.

---

# 📊 Performance Characteristics

| Metric            | Value                 |
| ----------------- | --------------------- |
| Processing Type   | Real-Time             |
| Dashboard Updates | Live                  |
| Webcam Stream     | Continuous            |
| Screen Capture    | Periodic              |
| Architecture      | Multi-Threaded        |
| Deployment Model  | Local Web Application |

---

# 🧪 Testing Strategy

## Unit Testing

* Webcam capture
* Screen capture
* Context classification
* Attention scoring
* Productivity scoring

## Integration Testing

* End-to-end data flow
* Dashboard synchronization
* API communication
* Multi-threaded execution

## System Testing

* Long-duration execution
* Resource stability
* Memory consistency
* Dashboard responsiveness

---

# 🏆 Key Achievements

* Designed a complete attention analysis workflow
* Implemented real-time computer vision pipeline
* Developed behavior-based productivity scoring
* Built a browser-based analytics dashboard
* Created a modular and extensible architecture
* Applied computer vision to productivity monitoring

---

# 🔒 Privacy & Security

This project is designed for local execution.

### Data Handling

* No cloud storage
* No external data transmission
* No user account requirements
* No personal information collection
* All processing occurs locally

### Processed Data

* Webcam frames
* Screen thumbnails
* Active application information

No data is transmitted outside the user's machine.

---

# ⚠️ Known Limitations

* Performance may decrease in poor lighting conditions.
* Multiple faces can reduce detection accuracy.
* Some operating systems require screen recording permissions.
* A functional webcam is required for attention analysis.

---

# 🚀 Future Improvements

* Deep learning gaze estimation
* Eye fatigue detection
* Blink rate analysis
* Head pose estimation
* Emotion recognition
* Stress detection
* Historical productivity analytics
* Cloud-based reporting dashboard

---

# 📚 Academic Relevance

This project combines concepts from:

* Artificial Intelligence
* Computer Vision
* Behavioral Analytics
* Human-Computer Interaction
* Software Engineering
* Real-Time Systems
* Data Analytics

---

# 🛠️ Installation

```bash
git clone <repository-url>
cd attention-analysis
pip install -r requirements.txt
```

---

# ▶️ Running the Project

```bash
python run_dashboard.py
```

Open in browser:

```text
http://localhost:8080
```

---

# 📄 License

This project is intended for educational, research, and learning purposes.

---

# 👨‍💻 Author

Developed as an Artificial Intelligence & Data Science engineering project focused on real-time attention intelligence and productivity analytics.
