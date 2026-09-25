"""
CivicAI - AI-Powered Citizen Services Assistant
Single-file version: backend, frontend, and data all in one file.

HOW TO RUN:
    pip install flask flask-cors google-genai gunicorn
    python app.py
Then open http://localhost:5000 in your browser.

(Optional) For live AI answers, set an environment variable GEMINI_API_KEY
before running. Without it, CivicAI still works using its built-in knowledge base.
"""

import os
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ----------------------------------------------------------------------------
# 1. KNOWLEDGE BASE
# ----------------------------------------------------------------------------
SERVICES = [
    {
        "name": "Scholarship Assistance",
        "category": "Education",
        "keywords": ["scholarship", "education", "student fee", "tuition"],
        "description": "Guidance on scholarship schemes available for school and college students from economically weaker or reserved categories.",
        "eligibility": "Indian citizen, enrolled in a recognized institution, family income below the scheme's prescribed limit (varies by scheme).",
        "documents": ["Aadhaar card", "Income certificate", "Caste certificate (if applicable)", "Previous year marksheet", "Bank passbook", "Admission/fee receipt"],
        "steps": ["Check eligibility on the National Scholarship Portal", "Register with Aadhaar-linked mobile number", "Fill application form", "Upload required documents", "Submit and track application status"],
    },
    {
        "name": "Income Certificate",
        "category": "Documents",
        "keywords": ["income certificate", "income proof"],
        "description": "An official document certifying a person's or family's annual income, required for scholarships, welfare schemes, and reservations.",
        "eligibility": "Any resident citizen can apply through their respective state's revenue department.",
        "documents": ["Aadhaar card", "Address proof", "Salary slip / self-declaration of income", "Passport size photo"],
        "steps": ["Visit state e-District portal or nearest Common Service Centre (CSC)", "Fill income certificate application", "Upload supporting documents", "Pay nominal fee if applicable", "Track and download the certificate once approved"],
    },
    {
        "name": "Employment Services",
        "category": "Employment",
        "keywords": ["job", "employment", "unemployment", "rojgar"],
        "description": "Information on government job portals, skill development programs, and unemployment support schemes.",
        "eligibility": "Job seekers registered with state employment exchange or national career service portal.",
        "documents": ["Aadhaar card", "Educational certificates", "Resume", "Bank account details"],
        "steps": ["Register on the National Career Service (NCS) portal", "Complete profile with skills and qualifications", "Browse job listings and skill training programs", "Apply directly through the portal"],
    },
    {
        "name": "Farmer / Agriculture Services",
        "category": "Agriculture",
        "keywords": ["farmer", "agriculture", "crop", "kisan"],
        "description": "Support schemes for farmers including income support, crop insurance, and subsidies on equipment and seeds.",
        "eligibility": "Landholding farmer families as per state land records.",
        "documents": ["Aadhaar card", "Land ownership documents", "Bank passbook", "Passport size photo"],
        "steps": ["Check eligibility on the PM-Kisan or relevant state portal", "Register with land and bank details", "Verify details at the local agriculture office", "Track benefit disbursement status online"],
    },
    {
        "name": "Healthcare Schemes",
        "category": "Healthcare",
        "keywords": ["health", "hospital", "ayushman", "insurance", "medical"],
        "description": "Government health insurance and assistance schemes providing free or subsidized treatment at empanelled hospitals.",
        "eligibility": "Families identified under socio-economic criteria defined by the scheme (varies by state/central scheme).",
        "documents": ["Aadhaar card", "Ration card / family ID", "Income certificate (if required)"],
        "steps": ["Check eligibility on the scheme's official portal", "Generate/verify health card at a Common Service Centre", "Visit an empanelled hospital for treatment", "Use the health card for cashless treatment"],
    },
    {
        "name": "Student Services",
        "category": "Education",
        "keywords": ["student id", "hostel", "student services", "college admission"],
        "description": "General guidance on student ID, hostel allotment, admission helpdesks, and education-related grievance redressal.",
        "eligibility": "Currently enrolled students in a recognized school, college, or university.",
        "documents": ["Aadhaar card", "Admission letter", "Institution ID proof"],
        "steps": ["Contact the institution's student services / admission cell", "Submit required documents for the specific service", "Follow up through the institution portal or helpdesk"],
    },
    {
        "name": "Identity / Document Services",
        "category": "Documents",
        "keywords": ["aadhaar", "pan card", "identity", "voter id", "passport"],
        "description": "Guidance on applying for or updating core identity documents such as Aadhaar, PAN, Voter ID, and passport.",
        "eligibility": "Indian residents/citizens as per the specific document's rules.",
        "documents": ["Proof of identity", "Proof of address", "Date of birth proof", "Passport size photo"],
        "steps": ["Identify the correct document portal (UIDAI, NSDL/UTIITSL, ECI, Passport Seva)", "Fill the online application form", "Book an appointment if biometric verification is required", "Submit documents and track application status"],
    },
    {
        "name": "Welfare Services",
        "category": "Welfare",
        "keywords": ["welfare", "pension", "disability", "widow", "old age"],
        "description": "Social welfare schemes covering old-age pension, disability support, and assistance for widows and vulnerable groups.",
        "eligibility": "Varies by scheme; generally based on age, income, or specific vulnerable-group criteria.",
        "documents": ["Aadhaar card", "Age proof", "Income certificate", "Disability/widow certificate (if applicable)", "Bank passbook"],
        "steps": ["Check the relevant scheme on the state social welfare department portal", "Fill the application with required details", "Submit supporting documents at the local welfare office or online", "Track application and benefit disbursement status"],
    },
]

SYSTEM_PROMPT = """You are CivicAI, a friendly AI assistant that helps citizens understand \
public services, eligibility, required documents, and application steps.

Use the following service knowledge base whenever it is relevant to the user's question:
{context}

Guidelines:
- Answer clearly and concisely, using short structured points where helpful.
- If the question matches a known service above, base your answer on it.
- If it doesn't match anything in the knowledge base, answer helpfully using general \
knowledge about Indian public services, but say the details may vary.
- Always end by reminding the user to verify current requirements on the relevant \
official government portal, since rules can change.
"""


def build_context():
    lines = []
    for s in SERVICES:
        lines.append(
            f"- {s['name']} ({s['category']}): {s['description']} "
            f"Eligibility: {s['eligibility']} "
            f"Documents: {', '.join(s['documents'])}. "
            f"Steps: {' -> '.join(s['steps'])}."
        )
    return "\n".join(lines)


def fallback_answer(user_message):
    msg = user_message.lower()
    for s in SERVICES:
        if s["name"].lower() in msg or any(k in msg for k in s.get("keywords", [])):
            steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(s["steps"]))
            return (
                f"**{s['name']}**\n\n{s['description']}\n\n"
                f"**Eligibility:** {s['eligibility']}\n\n"
                f"**Documents needed:** {', '.join(s['documents'])}\n\n"
                f"**Steps:**\n{steps_text}\n\n"
                f"_Please verify current details on the relevant official government portal._"
            )
    categories = sorted(set(s["category"] for s in SERVICES))
    return (
        "I can help with information about: " + ", ".join(categories) +
        ". Could you tell me which service you're interested in, or ask a specific question "
        "like 'What documents do I need for a scholarship?'"
    )


def ask_gemini(user_message):
    if not GEMINI_API_KEY:
        return fallback_answer(user_message)
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = SYSTEM_PROMPT.format(context=build_context()) + f"\n\nUser question: {user_message}"
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = getattr(response, "text", None)
        return text.strip() if text else fallback_answer(user_message)
    except Exception:
        return fallback_answer(user_message)


# ----------------------------------------------------------------------------
# 2. FRONTEND (HTML + CSS + JS all embedded in one string)
# ----------------------------------------------------------------------------
PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>CivicAI — Your Digital Public Assistant</title>
<style>
  :root {
    --primary: #1e5f8c; --primary-dark: #123a56; --bg: #f5f8fa;
    --card-bg: #ffffff; --text: #1c2b36; --muted: #5a6b76; --radius: 12px;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Segoe UI", Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); }
  .navbar { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); color: white; padding: 18px 24px; text-align: center; }
  .brand { display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 1.6rem; font-weight: 700; }
  .tagline { margin: 4px 0 0; opacity: 0.9; font-size: 0.95rem; }
  main { max-width: 900px; margin: 0 auto; padding: 32px 20px 60px; }
  .hero { text-align: center; padding: 30px 10px 10px; }
  .hero h1 { font-size: 1.9rem; margin-bottom: 8px; }
  .hero p { color: var(--muted); margin-bottom: 24px; }
  .ask-box { display: flex; gap: 10px; max-width: 600px; margin: 0 auto; }
  .ask-box input, .chat-input-row input { flex: 1; padding: 14px 16px; border-radius: var(--radius); border: 1px solid #d5dee3; font-size: 1rem; }
  .ask-box button, .chat-input-row button { padding: 14px 20px; border: none; border-radius: var(--radius); background: var(--primary); color: white; font-weight: 600; cursor: pointer; }
  .ask-box button:hover, .chat-input-row button:hover { background: var(--primary-dark); }
  .categories { margin-top: 48px; }
  .categories h2 { text-align: center; margin-bottom: 20px; }
  .category-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 14px; }
  .category-card { background: var(--card-bg); border: 1px solid #e3e9ec; border-radius: var(--radius); padding: 18px 12px; text-align: center; cursor: pointer; transition: transform 0.15s ease; }
  .category-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(30,95,140,0.12); }
  .category-card .icon { font-size: 1.6rem; display: block; margin-bottom: 6px; }
  .chat-section { margin-top: 48px; background: var(--card-bg); border-radius: var(--radius); border: 1px solid #e3e9ec; padding: 20px; }
  .chat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .link-button { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.9rem; text-decoration: underline; }
  .chat-window { min-height: 200px; max-height: 420px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 8px 4px; }
  .msg { max-width: 85%; padding: 12px 14px; border-radius: var(--radius); line-height: 1.45; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: var(--primary); color: white; border-bottom-right-radius: 4px; }
  .msg.bot { align-self: flex-start; background: #eef3f5; color: var(--text); border-bottom-left-radius: 4px; }
  .msg.loading { align-self: flex-start; color: var(--muted); font-style: italic; }
  .chat-input-row { display: flex; gap: 10px; margin-top: 14px; }
  footer { text-align: center; padding: 20px; font-size: 0.8rem; color: var(--muted); max-width: 700px; margin: 0 auto; }
  @media (max-width: 480px) { .ask-box, .chat-input-row { flex-direction: column; } }
</style>
</head>
<body>
  <header class="navbar">
    <div class="brand"><span>🏛️</span><span>CivicAI</span></div>
    <p class="tagline">Making Public Services Easier to Understand</p>
  </header>

  <main>
    <section class="hero">
      <h1>Your Digital Public Assistant</h1>
      <p>Ask anything about public services — scholarships, documents, healthcare, and more.</p>
      <form id="ask-form" class="ask-box">
        <input type="text" id="ask-input" placeholder="What do you want to know?" autocomplete="off" required />
        <button type="submit">Ask CivicAI</button>
      </form>
    </section>

    <section class="categories">
      <h2>Popular Services</h2>
      <div class="category-grid" id="category-grid"></div>
    </section>

    <section class="chat-section" id="chat-section" hidden>
      <div class="chat-header">
        <h2>Chat with CivicAI</h2>
        <button id="clear-chat" class="link-button">Clear conversation</button>
      </div>
      <div id="chat-window" class="chat-window"></div>
      <form id="chat-form" class="chat-input-row">
        <input type="text" id="chat-input" placeholder="Ask another question..." autocomplete="off" required />
        <button type="submit">Send</button>
      </form>
    </section>
  </main>

  <footer>
    CivicAI provides informational guidance and is not a government authority.
    Please verify current eligibility, documents and application requirements
    through the relevant official government portal.
  </footer>

<script>
  const CATEGORIES = [
    { name: "Education", icon: "🎓" }, { name: "Healthcare", icon: "🏥" },
    { name: "Documents", icon: "📄" }, { name: "Employment", icon: "💼" },
    { name: "Agriculture", icon: "🌾" }, { name: "Welfare", icon: "🤝" },
  ];
  const categoryGrid = document.getElementById("category-grid");
  const askForm = document.getElementById("ask-form");
  const askInput = document.getElementById("ask-input");
  const chatSection = document.getElementById("chat-section");
  const chatWindow = document.getElementById("chat-window");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const clearChatBtn = document.getElementById("clear-chat");

  function renderCategories() {
    categoryGrid.innerHTML = "";
    CATEGORIES.forEach((cat) => {
      const card = document.createElement("div");
      card.className = "category-card";
      card.innerHTML = `<span class="icon">${cat.icon}</span><span>${cat.name}</span>`;
      card.addEventListener("click", () => {
        openChat();
        sendMessage(`What services are available related to ${cat.name}?`);
      });
      categoryGrid.appendChild(card);
    });
  }
  function openChat() {
    chatSection.hidden = false;
    chatSection.scrollIntoView({ behavior: "smooth" });
  }
  function appendMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `msg ${sender}`;
    msg.textContent = text;
    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return msg;
  }
  async function sendMessage(message) {
    appendMessage(message, "user");
    const loadingMsg = appendMessage("CivicAI is thinking...", "loading");
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      loadingMsg.remove();
      appendMessage(data.response || "Sorry, something went wrong. Please try again.", "bot");
    } catch (err) {
      loadingMsg.remove();
      appendMessage("Network error — please check your connection and try again.", "bot");
    }
  }
  askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = askInput.value.trim();
    if (!value) return;
    openChat();
    sendMessage(value);
    askInput.value = "";
  });
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = chatInput.value.trim();
    if (!value) return;
    sendMessage(value);
    chatInput.value = "";
  });
  clearChatBtn.addEventListener("click", () => { chatWindow.innerHTML = ""; });
  renderCategories();
</script>
</body>
</html>
"""


# ----------------------------------------------------------------------------
# 3. ROUTES
# ----------------------------------------------------------------------------
@app.route("/")
def home():
    return Response(PAGE_HTML, mimetype="text/html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/services")
def get_services():
    return jsonify(SERVICES)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "message is required"}), 400
    return jsonify({"response": ask_gemini(user_message)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
