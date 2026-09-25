# CivicAI

**AI-Powered Citizen Services Assistant**
Track 1 — AI for Digital Public Infrastructure & Governance

## 1. Problem
Citizens often struggle to understand public-service eligibility, required documents, and
application procedures because information is complex or scattered across sources.

## 2. Solution
CivicAI is a conversational AI assistant that helps citizens understand public services,
eligibility, required documents, and application steps through a simple chat interface.

## 3. Features
- 🤖 AI citizen assistant (chat interface)
- 🔎 Service discovery by category
- 📄 Document & eligibility guidance
- 🪜 Step-by-step application instructions
- 📱 Mobile-friendly, responsive design
- 🧠 Built-in knowledge base with a smart fallback if no AI key is configured

## 4. Technology Stack
- **Backend:** Python + Flask (single-file app, frontend HTML/CSS/JS embedded)
- **AI:** Google Gemini (`google-genai`)
- **Deployment:** Render / any Python host, via Gunicorn

## 5. System Architecture
```
          USER
            |
      Browser (HTML/CSS/JS)
            |
        Flask Backend  --->  built-in service knowledge base
            |
       Gemini AI API
            |
     Structured Response
            |
          USER
```

## 6. How to Run Locally

1. Clone this repository:
   ```
   git clone https://github.com/YOUR_USERNAME/civicai.git
   cd civicai
   ```
2. (Optional) Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. (Optional) Set your Gemini API key for live AI answers. Without it, CivicAI still
   works using its built-in knowledge base.
   - Windows PowerShell: `$env:GEMINI_API_KEY="your_key_here"`
   - macOS/Linux: `export GEMINI_API_KEY="your_key_here"`
5. Run the app:
   ```
   python app.py
   ```
6. Open your browser at: `http://localhost:5000`

## 7. Deploying to Render
- **Root Directory:** `.`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- Add an environment variable `GEMINI_API_KEY` in Render's dashboard (optional but
  recommended for live AI answers).

## 8. Project Structure
```
civicai/
├── app.py            # Full Flask backend + embedded frontend (HTML/CSS/JS)
├── requirements.txt  # Python dependencies
├── README.md
└── .gitignore
```

## 9. Future Scope
- Support for Indian languages (Kannada, Hindi, etc.)
- Voice-based interaction
- More verified government services
- Integration with official government APIs
- Accessibility improvements

## 10. Disclaimer
CivicAI provides informational guidance and is not a government authority. Please verify
current eligibility, documents and application requirements through the relevant official
government portal.

## Team
Team Quantum Trio
