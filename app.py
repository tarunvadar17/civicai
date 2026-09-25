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
        "code": "SVC-01",
        "name": "Scholarship Assistance",
        "category": "Education",
        "keywords": ["scholarship", "education", "student fee", "tuition"],
        "description": "Guidance on scholarship schemes available for school and college students from economically weaker or reserved categories.",
        "eligibility": "Indian citizen, enrolled in a recognized institution, family income below the scheme's prescribed limit (varies by scheme).",
        "documents": ["Aadhaar card", "Income certificate", "Caste certificate (if applicable)", "Previous year marksheet", "Bank passbook", "Admission/fee receipt"],
        "steps": ["Check eligibility on the National Scholarship Portal", "Register with Aadhaar-linked mobile number", "Fill application form", "Upload required documents", "Submit and track application status"],
    },
    {
        "code": "SVC-02",
        "name": "Income Certificate",
        "category": "Documents",
        "keywords": ["income certificate", "income proof"],
        "description": "An official document certifying a person's or family's annual income, required for scholarships, welfare schemes, and reservations.",
        "eligibility": "Any resident citizen can apply through their respective state's revenue department.",
        "documents": ["Aadhaar card", "Address proof", "Salary slip / self-declaration of income", "Passport size photo"],
        "steps": ["Visit state e-District portal or nearest Common Service Centre (CSC)", "Fill income certificate application", "Upload supporting documents", "Pay nominal fee if applicable", "Track and download the certificate once approved"],
    },
    {
        "code": "SVC-03",
        "name": "Employment Services",
        "category": "Employment",
        "keywords": ["job", "employment", "unemployment", "rojgar"],
        "description": "Information on government job portals, skill development programs, and unemployment support schemes.",
        "eligibility": "Job seekers registered with state employment exchange or national career service portal.",
        "documents": ["Aadhaar card", "Educational certificates", "Resume", "Bank account details"],
        "steps": ["Register on the National Career Service (NCS) portal", "Complete profile with skills and qualifications", "Browse job listings and skill training programs", "Apply directly through the portal"],
    },
    {
        "code": "SVC-04",
        "name": "Farmer / Agriculture Services",
        "category": "Agriculture",
        "keywords": ["farmer", "agriculture", "crop", "kisan"],
        "description": "Support schemes for farmers including income support, crop insurance, and subsidies on equipment and seeds.",
        "eligibility": "Landholding farmer families as per state land records.",
        "documents": ["Aadhaar card", "Land ownership documents", "Bank passbook", "Passport size photo"],
        "steps": ["Check eligibility on the PM-Kisan or relevant state portal", "Register with land and bank details", "Verify details at the local agriculture office", "Track benefit disbursement status online"],
    },
    {
        "code": "SVC-05",
        "name": "Healthcare Schemes",
        "category": "Healthcare",
        "keywords": ["health", "hospital", "ayushman", "insurance", "medical"],
        "description": "Government health insurance and assistance schemes providing free or subsidized treatment at empanelled hospitals.",
        "eligibility": "Families identified under socio-economic criteria defined by the scheme (varies by state/central scheme).",
        "documents": ["Aadhaar card", "Ration card / family ID", "Income certificate (if required)"],
        "steps": ["Check eligibility on the scheme's official portal", "Generate/verify health card at a Common Service Centre", "Visit an empanelled hospital for treatment", "Use the health card for cashless treatment"],
    },
    {
        "code": "SVC-06",
        "name": "Student Services",
        "category": "Education",
        "keywords": ["student id", "hostel", "student services", "college admission"],
        "description": "General guidance on student ID, hostel allotment, admission helpdesks, and education-related grievance redressal.",
        "eligibility": "Currently enrolled students in a recognized school, college, or university.",
        "documents": ["Aadhaar card", "Admission letter", "Institution ID proof"],
        "steps": ["Contact the institution's student services / admission cell", "Submit required documents for the specific service", "Follow up through the institution portal or helpdesk"],
    },
    {
        "code": "SVC-07",
        "name": "Identity / Document Services",
        "category": "Documents",
        "keywords": ["aadhaar", "pan card", "identity", "voter id", "passport"],
        "description": "Guidance on applying for or updating core identity documents such as Aadhaar, PAN, Voter ID, and passport.",
        "eligibility": "Indian residents/citizens as per the specific document's rules.",
        "documents": ["Proof of identity", "Proof of address", "Date of birth proof", "Passport size photo"],
        "steps": ["Identify the correct document portal (UIDAI, NSDL/UTIITSL, ECI, Passport Seva)", "Fill the online application form", "Book an appointment if biometric verification is required", "Submit documents and track application status"],
    },
    {
        "code": "SVC-08",
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
                f"{s['name']} ({s['code']})\n\n{s['description']}\n\n"
                f"Eligibility: {s['eligibility']}\n\n"
                f"Documents needed: {', '.join(s['documents'])}\n\n"
                f"Steps:\n{steps_text}\n\n"
                f"Please verify current details on the relevant official government portal."
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
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CivicAI — AI Assistant</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#05030a;
  --shell:#0b0813;
  --sidebar:#090711;
  --panel:#110d1b;
  --panel2:#171123;
  --panel3:#1d162b;
  --border:rgba(255,255,255,.075);
  --border-purple:rgba(139,92,246,.34);
  --text:#f7f5ff;
  --muted:#9b94ad;
  --muted2:#686174;
  --purple:#8b5cf6;
  --purple2:#b477ff;
  --pink:#d38cff;
  --gradient:linear-gradient(135deg,#7447ff 0%,#b66cff 100%);
  --shadow:0 30px 90px rgba(82,35,170,.20);
  --radius:18px;
}

*{box-sizing:border-box}
html,body{margin:0;min-height:100%;font-family:Inter,Arial,sans-serif;background:
radial-gradient(circle at 50% 45%,rgba(109,50,207,.14),transparent 38%),
radial-gradient(circle at 12% 90%,rgba(83,31,166,.12),transparent 30%),
var(--bg);color:var(--text)}
button,input{font:inherit}
button{cursor:pointer}

body{
  min-height:100vh;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:28px;
}

.app-shell{
  width:min(1450px,100%);
  height:min(900px,calc(100vh - 56px));
  min-height:680px;
  display:flex;
  overflow:hidden;
  border:1px solid rgba(145,91,255,.32);
  border-radius:24px;
  background:var(--shell);
  box-shadow:0 0 0 1px rgba(255,255,255,.025),0 0 110px rgba(117,55,225,.20),var(--shadow);
  position:relative;
}
.app-shell:before{
  content:"";
  position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(120deg,rgba(157,106,255,.035),transparent 28%,transparent 70%,rgba(157,106,255,.025));
}

/* Sidebar */
.sidebar{
  width:218px;flex:0 0 218px;
  background:rgba(7,5,12,.88);
  border-right:1px solid var(--border);
  padding:20px 13px 14px;
  display:flex;flex-direction:column;
  z-index:2;
}
.brand{
  display:flex;align-items:center;gap:9px;
  padding:2px 10px 24px;
}
.brand-icon{
  width:28px;height:28px;border-radius:8px;
  background:var(--gradient);
  display:grid;place-items:center;
  box-shadow:0 0 18px rgba(139,92,246,.45);
  color:#fff;font-size:14px;font-weight:800;
}
.brand-name{font-size:15px;font-weight:800;letter-spacing:-.2px}
.brand-name span{color:var(--purple2)}

.section-label{
  color:#625b6e;font-size:9px;font-weight:700;
  letter-spacing:1.1px;padding:0 10px 7px;
}
.nav{list-style:none;padding:0;margin:0 0 18px}
.nav li{margin:2px 0}
.nav button{
  width:100%;height:35px;border:0;background:transparent;color:#9b94a8;
  border-radius:9px;display:flex;align-items:center;gap:10px;
  padding:0 11px;font-size:11px;text-align:left;
  transition:.2s ease;
}
.nav button svg{width:14px;height:14px;opacity:.9;flex:none}
.nav button:hover{background:#15101f;color:#eeeaff}
.nav button.active{
  background:var(--gradient);color:white;
  box-shadow:0 7px 24px rgba(126,71,242,.28);
}
.nav button.active svg{color:#fff}

.sidebar-bottom{margin-top:auto}
.info-card{
  margin:8px 4px 12px;padding:12px;
  background:linear-gradient(145deg,#171126,#100d18);
  border:1px solid var(--border);border-radius:12px;
}
.info-icon{
  width:24px;height:24px;border-radius:7px;
  background:rgba(139,92,246,.18);color:#b98aff;
  display:grid;place-items:center;margin-bottom:8px;font-size:11px;
}
.info-card p{margin:0 0 10px;color:#81798f;font-size:9px;line-height:1.5}
.info-card button{
  width:100%;border:0;border-radius:7px;padding:7px;
  background:#1d1730;color:#c5a9ff;font-size:9px;font-weight:700;
}
.logout{
  width:100%;height:32px;border:0;background:transparent;color:#726a7d;
  display:flex;align-items:center;gap:9px;padding:0 11px;font-size:10px;
}
.logout:hover{color:#eeeaff}

/* Main */
.main{flex:1;min-width:0;display:flex;flex-direction:column;z-index:1}
.topbar{
  height:58px;flex:none;border-bottom:1px solid var(--border);
  display:flex;align-items:center;padding:0 20px;gap:15px;
  background:rgba(10,7,16,.55);
}
.search{
  width:280px;height:31px;display:flex;align-items:center;gap:8px;
  border:1px solid rgba(255,255,255,.045);border-radius:8px;
  background:#0d0a14;color:#686174;padding:0 10px;font-size:10px;
}
.search svg{width:13px}
.search input{
  width:100%;border:0;outline:0;background:transparent;color:#eee;
  font-size:10px;
}
.search input::placeholder{color:#5f586a}
.top-actions{margin-left:auto;display:flex;align-items:center;gap:13px}
.icon-btn{
  width:28px;height:28px;border:1px solid transparent;border-radius:8px;
  background:transparent;color:#777080;display:grid;place-items:center;
}
.icon-btn:hover{background:#171121;color:#eee}
.user{
  display:flex;align-items:center;gap:8px;padding-left:5px;
}
.avatar{
  width:27px;height:27px;border-radius:50%;background:var(--gradient);
  display:grid;place-items:center;font-size:9px;font-weight:800;
  box-shadow:0 0 12px rgba(139,92,246,.25);
}
.user-name{font-size:9px;font-weight:700}
.user-sub{font-size:8px;color:#625b6d;margin-top:2px}

.view{display:none;flex:1;min-height:0;overflow:auto;padding:22px}
.view.active{display:block}
.view::-webkit-scrollbar{width:6px}
.view::-webkit-scrollbar-thumb{background:#241b35;border-radius:10px}

.view-head{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:20px;
}
.view-head h1{font-size:14px;margin:0;font-weight:700}
.actions{display:flex;gap:8px}
.btn{
  height:30px;padding:0 12px;border-radius:8px;
  border:1px solid var(--border);background:#100c17;color:#9e97aa;
  font-size:9px;font-weight:600;
}
.btn:hover{border-color:var(--border-purple);color:#fff}
.btn.primary{background:var(--gradient);border:0;color:#fff}

/* Assistant */
.assistant{
  height:100%;min-height:0;display:flex;flex-direction:column;
}
.assistant-center{
  flex:1;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:10px 10px 30px;
}
.ai-orb{
  width:50px;height:50px;border-radius:50%;display:grid;place-items:center;
  background:radial-gradient(circle at 35% 30%,#d0a5ff,#8353f5 58%,#5a2fc3);
  box-shadow:0 0 35px rgba(142,86,255,.45),inset 0 0 15px rgba(255,255,255,.18);
  margin-bottom:15px;position:relative;
}
.ai-orb:after{
  content:"✦";font-size:20px;color:#fff;
  text-shadow:0 0 12px #fff;
}
.assistant-title{
  margin:0 0 20px;font-size:18px;letter-spacing:-.5px;font-weight:700;
}
.ask-box{
  width:min(620px,100%);
  border:1px solid rgba(151,98,255,.42);
  background:linear-gradient(145deg,rgba(24,17,37,.96),rgba(14,10,22,.96));
  border-radius:14px;padding:12px;
  box-shadow:0 15px 45px rgba(0,0,0,.25),0 0 28px rgba(121,61,229,.08);
}
.ask-box:focus-within{border-color:rgba(173,125,255,.75);box-shadow:0 0 30px rgba(139,92,246,.13)}
.ask-box input{
  width:100%;height:30px;border:0;outline:0;background:transparent;
  color:#eee;font-size:10px;padding:0 3px;
}
.ask-box input::placeholder{color:#615a6b}
.ask-row{display:flex;align-items:center;justify-content:space-between;margin-top:7px}
.ask-tools{display:flex;gap:5px}
.tool-btn{
  width:23px;height:23px;border:0;border-radius:6px;
  background:transparent;color:#70687c;display:grid;place-items:center;font-size:12px;
}
.tool-btn:hover{background:#1d152a;color:#b99cff}
.send-btn{
  width:27px;height:27px;border:0;border-radius:50%;
  background:var(--gradient);color:white;display:grid;place-items:center;
  box-shadow:0 4px 15px rgba(126,71,242,.35);font-size:11px;
}
.send-btn:hover{transform:translateY(-1px)}

.suggestions{
  width:min(620px,100%);display:grid;
  grid-template-columns:repeat(3,1fr);gap:8px;margin-top:9px;
}
.suggestion{
  min-height:57px;text-align:left;padding:9px 10px;
  background:rgba(13,10,20,.75);border:1px solid var(--border);
  border-radius:9px;color:#8d8598;transition:.2s;
}
.suggestion:hover{border-color:rgba(139,92,246,.35);background:#151020}
.suggestion-title{font-size:9px;font-weight:700;color:#c3bdca;margin-bottom:4px}
.suggestion-sub{font-size:8px;color:#686071;line-height:1.35}

/* Chat */
.chat-layout{height:100%;display:flex;flex-direction:column}
.chat-window{
  flex:1;overflow:auto;display:flex;flex-direction:column;
  gap:12px;padding:8px max(5px,8%);
}
.chat-window::-webkit-scrollbar{width:5px}
.chat-window::-webkit-scrollbar-thumb{background:#261b39;border-radius:10px}
.msg{
  max-width:min(72%,650px);padding:10px 13px;border-radius:12px;
  font-size:10px;line-height:1.55;white-space:pre-wrap;
}
.msg.user{align-self:flex-end;background:var(--gradient);color:white;border-bottom-right-radius:4px}
.msg.bot{align-self:flex-start;background:#14101e;border:1px solid var(--border);color:#ddd7e5;border-bottom-left-radius:4px}
.msg.loading{background:transparent;border:0;color:#766d80;font-style:italic}
.chat-dock{padding:10px 8% 4px}
.chat-dock .ask-box{width:100%;max-width:none}

.hidden{display:none!important}

/* Dashboard */
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}
.card{
  background:linear-gradient(145deg,#151020,#100c17);
  border:1px solid var(--border);border-radius:13px;padding:15px;
}
.metric{font-size:21px;font-weight:800}
.metric-label{font-size:9px;color:#777080;margin-top:4px}
.card-icon{
  width:27px;height:27px;border-radius:8px;background:#211633;
  color:#b68aff;display:grid;place-items:center;margin-bottom:10px;font-size:11px
}
.section-title{font-size:11px;font-weight:700;margin:0 0 10px}
.quick-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.quick-card{
  border:1px solid var(--border);border-radius:12px;padding:14px;
  background:#100d17;transition:.2s;cursor:pointer;
}
.quick-card:hover{transform:translateY(-2px);border-color:rgba(139,92,246,.4)}
.quick-card strong{font-size:10px;display:block;margin-bottom:5px}
.quick-card span{font-size:8px;color:#70687a;line-height:1.4}

/* Services */
.service-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.service-card{
  border:1px solid var(--border);background:#100d17;border-radius:12px;
  overflow:hidden;
}
.service-head{padding:13px;cursor:pointer}
.service-code{font-size:8px;color:#ad7bff;font-weight:700}
.service-name{font-size:11px;font-weight:700;margin:4px 0}
.service-cat{font-size:8px;color:#6f6877}
.service-body{display:none;border-top:1px solid var(--border);padding:12px;color:#8a8292;font-size:9px;line-height:1.5}
.service-card.open .service-body{display:block}
.service-body b{color:#b98eff}
.service-body ol{padding-left:16px}
.ask-service{border:1px solid var(--border);background:#171124;color:#b890ff;border-radius:7px;padding:7px 9px;font-size:8px}

/* Alerts/settings */
.info-panel{max-width:620px}
.info-panel p{font-size:10px;color:#847c8e;line-height:1.6;margin:0}

/* Footer */
.footer{
  border-top:1px solid var(--border);padding:8px 20px;
  text-align:center;color:#514a5d;font-size:8px;flex:none;
}

/* Responsive */
@media(max-width:900px){
  body{padding:12px}
  .app-shell{height:calc(100vh - 24px);min-height:600px}
  .sidebar{width:170px;flex-basis:170px}
  .search{width:210px}
}
@media(max-width:700px){
  .app-shell{flex-direction:column;height:auto;min-height:calc(100vh - 24px)}
  .sidebar{width:100%;flex-basis:auto;height:auto;border-right:0;border-bottom:1px solid var(--border);padding:10px}
  .brand{padding-bottom:10px}
  .section-label,.sidebar-bottom,.sidebar .nav:nth-of-type(2){display:none}
  .sidebar .nav{display:flex;gap:4px;margin:0;overflow:auto}
  .sidebar .nav button{white-space:nowrap;width:auto;padding:0 10px}
  .topbar{height:50px}
  .search{flex:1;width:auto}
  .user-sub{display:none}
  .view{padding:14px}
  .suggestions,.quick-grid{grid-template-columns:1fr}
  .cards{grid-template-columns:1fr}
  .service-grid{grid-template-columns:1fr}
  .assistant-title{font-size:16px}
}
</style>
</head>
<body>
<div class="app-shell">

  <aside class="sidebar">
    <div class="brand">
      <div class="brand-icon">✦</div>
      <div class="brand-name">Civic<span>AI</span></div>
    </div>

    <div class="section-label">MENU</div>
    <ul class="nav" id="main-nav">
      <li><button data-view="dashboard">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>Dashboard
      </button></li>
      <li><button data-view="services">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>Services
      </button></li>
      <li><button data-view="assistant" class="active">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.9 4.4L18 9l-4.1 1.9L12 15l-1.9-4.1L6 9l4.1-1.6L12 3z"/><path d="M19 15l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9.9-2z"/></svg>AI Assistant
      </button></li>
      <li><button data-view="alerts">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>Alerts
      </button></li>
      <li><button data-view="settings">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>Settings
      </button></li>
    </ul>

    <div class="section-label">CATEGORIES</div>
    <ul class="nav" id="cat-nav"></ul>

    <div class="sidebar-bottom">
      <div class="info-card">
        <div class="info-icon">✓</div>
        <p>Guidance is informational. Confirm current details on the official government portal.</p>
        <button id="dismiss-info">Got it</button>
      </div>
      <button class="logout" type="button">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        Logout
      </button>
    </div>
  </aside>

  <main class="main">
    <header class="topbar">
      <div class="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input id="service-search" placeholder="Search services..." autocomplete="off">
      </div>

      <div class="top-actions">
        <button class="icon-btn" title="Notifications">◌</button>
        <button class="icon-btn" title="Help">?</button>
        <div class="user">
          <div class="avatar">C</div>
          <div>
            <div class="user-name">Citizen</div>
            <div class="user-sub">Guest session</div>
          </div>
        </div>
      </div>
    </header>

    <!-- Dashboard -->
    <section class="view" id="view-dashboard">
      <div class="view-head">
        <h1>Dashboard</h1>
        <div class="actions"><button class="btn primary" id="dashboard-ai">Ask CivicAI</button></div>
      </div>

      <div class="cards">
        <div class="card"><div class="card-icon">▦</div><div class="metric" id="service-count">8</div><div class="metric-label">Services available</div></div>
        <div class="card"><div class="card-icon">◈</div><div class="metric" id="category-count">6</div><div class="metric-label">Categories covered</div></div>
        <div class="card"><div class="card-icon">✦</div><div class="metric">24/7</div><div class="metric-label">Assistant availability</div></div>
      </div>

      <h2 class="section-title">Popular questions</h2>
      <div class="quick-grid" id="quick-grid"></div>
    </section>

    <!-- Services -->
    <section class="view" id="view-services">
      <div class="view-head">
        <h1>Service Directory</h1>
      </div>
      <div class="service-grid" id="service-grid"></div>
    </section>

    <!-- Assistant -->
    <section class="view active" id="view-assistant">
      <div class="assistant">
        <div class="view-head">
          <h1>AI Assistant</h1>
          <div class="actions">
            <button class="btn" id="new-chat">New Chat</button>
            <button class="btn primary" id="share-btn">Share</button>
          </div>
        </div>

        <div class="assistant-center" id="empty-state">
          <div class="ai-orb"></div>
          <h2 class="assistant-title">What can I help with?</h2>

          <div class="ask-box">
            <input id="ask-input" type="text" placeholder="Ask anything about public services..." autocomplete="off">
            <div class="ask-row">
              <div class="ask-tools">
                <button class="tool-btn" type="button">＋</button>
                <button class="tool-btn" type="button">⌁</button>
                <button class="tool-btn" type="button">◉</button>
              </div>
              <button class="send-btn" id="ask-send" type="button">➤</button>
            </div>
          </div>

          <div class="suggestions" id="suggestions"></div>
        </div>

        <div class="chat-layout hidden" id="chat-layout">
          <div class="chat-window" id="chat-window"></div>
          <div class="chat-dock">
            <div class="ask-box">
              <input id="chat-input" type="text" placeholder="Ask another question..." autocomplete="off">
              <div class="ask-row">
                <div class="ask-tools">
                  <button class="tool-btn" type="button">＋</button>
                  <button class="tool-btn" type="button">⌁</button>
                </div>
                <button class="send-btn" id="chat-send" type="button">➤</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Alerts -->
    <section class="view" id="view-alerts">
      <div class="view-head"><h1>Alerts</h1></div>
      <div class="card info-panel">
        <div class="card-icon">!</div>
        <p>CivicAI provides informational guidance and is not a government authority. Verify current eligibility, documents and application requirements through the relevant official government portal.</p>
      </div>
    </section>

    <!-- Settings -->
    <section class="view" id="view-settings">
      <div class="view-head"><h1>Settings</h1></div>
      <div class="card info-panel">
        <div class="card-icon">⚙</div>
        <p>Settings are not required to use CivicAI. This version is a stateless assistant with no account or saved data.</p>
      </div>
    </section>

    <footer class="footer">CivicAI provides informational guidance. Verify important details on the relevant official government portal.</footer>
  </main>
</div>

<script>
const SERVICES = __SERVICES_JSON__;

const views = {
  dashboard: document.getElementById("view-dashboard"),
  services: document.getElementById("view-services"),
  assistant: document.getElementById("view-assistant"),
  alerts: document.getElementById("view-alerts"),
  settings: document.getElementById("view-settings")
};

const navButtons = document.querySelectorAll("#main-nav button");

function showView(name){
  Object.values(views).forEach(v => v.classList.remove("active"));
  views[name].classList.add("active");
  navButtons.forEach(b => b.classList.toggle("active", b.dataset.view === name));
}

navButtons.forEach(btn => btn.addEventListener("click", () => showView(btn.dataset.view)));

const categories = [...new Set(SERVICES.map(s => s.category))];
const catNav = document.getElementById("cat-nav");
categories.forEach(cat => {
  const li = document.createElement("li");
  const btn = document.createElement("button");
  btn.innerHTML = `<span style="width:14px;text-align:center">•</span>${cat}`;
  btn.addEventListener("click", () => showView("services"));
  li.appendChild(btn);
  catNav.appendChild(li);
});

document.getElementById("service-count").textContent = SERVICES.length;
document.getElementById("category-count").textContent = categories.length;

const QUICK = [
  {title:"Scholarships", sub:"How do I apply for a scholarship?", q:"How do I apply for a scholarship?"},
  {title:"Income Certificate", sub:"What documents are needed?", q:"What documents do I need for an income certificate?"},
  {title:"Healthcare Schemes", sub:"How can I check eligibility?", q:"How do I check eligibility for healthcare schemes?"}
];

const quickGrid = document.getElementById("quick-grid");
const suggestions = document.getElementById("suggestions");

QUICK.forEach(item => {
  const card = document.createElement("div");
  card.className = "quick-card";
  card.innerHTML = `<strong>${item.title}</strong><span>${item.sub}</span>`;
  card.onclick = () => goToAssistantWith(item.q);
  quickGrid.appendChild(card);

  const chip = document.createElement("button");
  chip.className = "suggestion";
  chip.innerHTML = `<div class="suggestion-title">${item.title}</div><div class="suggestion-sub">${item.sub}</div>`;
  chip.onclick = () => sendMessage(item.q);
  suggestions.appendChild(chip);
});

const serviceGrid = document.getElementById("service-grid");

function renderServices(list){
  serviceGrid.innerHTML = "";
  list.forEach(s => {
    const card = document.createElement("div");
    card.className = "service-card";
    card.innerHTML = `
      <div class="service-head">
        <div class="service-code">${s.code}</div>
        <div class="service-name">${s.name}</div>
        <div class="service-cat">${s.category}</div>
      </div>
      <div class="service-body">
        <div><b>Description</b><br>${s.description}</div><br>
        <div><b>Eligibility</b><br>${s.eligibility}</div><br>
        <div><b>Documents</b><br>${s.documents.join(", ")}</div><br>
        <div><b>Steps</b><ol>${s.steps.map(x => `<li>${x}</li>`).join("")}</ol></div>
        <button class="ask-service">Ask CivicAI about this</button>
      </div>
    `;

    card.querySelector(".service-head").onclick = () => card.classList.toggle("open");
    card.querySelector(".ask-service").onclick = (e) => {
      e.stopPropagation();
      goToAssistantWith(`Tell me more about ${s.name}`);
    };
    serviceGrid.appendChild(card);
  });
}
renderServices(SERVICES);

const emptyState = document.getElementById("empty-state");
const chatLayout = document.getElementById("chat-layout");
const chatWindow = document.getElementById("chat-window");
const askInput = document.getElementById("ask-input");
const askSend = document.getElementById("ask-send");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

function enterChat(){
  emptyState.classList.add("hidden");
  chatLayout.classList.remove("hidden");
}

function appendMessage(text, sender){
  const msg = document.createElement("div");
  msg.className = `msg ${sender}`;
  msg.textContent = text;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

async function sendMessage(message){
  if(!message || !message.trim()) return;
  showView("assistant");
  enterChat();

  appendMessage(message, "user");
  const loading = appendMessage("CivicAI is thinking...", "loading");

  try{
    const res = await fetch("/api/chat", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({message})
    });
    const data = await res.json();
    loading.remove();
    appendMessage(data.response || "Sorry, something went wrong. Please try again.", "bot");
  }catch(err){
    loading.remove();
    appendMessage("Network error — please check your connection and try again.", "bot");
  }
}

function goToAssistantWith(question){
  showView("assistant");
  sendMessage(question);
}

askSend.onclick = () => {
  const value = askInput.value.trim();
  askInput.value = "";
  sendMessage(value);
};
askInput.addEventListener("keydown", e => {
  if(e.key === "Enter"){
    const value = askInput.value.trim();
    askInput.value = "";
    sendMessage(value);
  }
});

chatSend.onclick = () => {
  const value = chatInput.value.trim();
  chatInput.value = "";
  sendMessage(value);
};
chatInput.addEventListener("keydown", e => {
  if(e.key === "Enter"){
    const value = chatInput.value.trim();
    chatInput.value = "";
    sendMessage(value);
  }
});

document.getElementById("new-chat").onclick = () => {
  chatWindow.innerHTML = "";
  chatLayout.classList.add("hidden");
  emptyState.classList.remove("hidden");
  askInput.focus();
};

document.getElementById("dashboard-ai").onclick = () => showView("assistant");

document.getElementById("share-btn").onclick = async () => {
  try{
    await navigator.clipboard.writeText(window.location.href);
    const btn = document.getElementById("share-btn");
    btn.textContent = "Copied";
    setTimeout(() => btn.textContent = "Share", 1300);
  }catch(e){}
};

document.getElementById("dismiss-info").onclick = () => {
  document.querySelector(".info-card").style.display = "none";
};

document.getElementById("service-search").addEventListener("input", e => {
  const q = e.target.value.toLowerCase().trim();
  if(!q){
    renderServices(SERVICES);
    return;
  }
  showView("services");
  renderServices(SERVICES.filter(s =>
    `${s.name} ${s.category} ${s.description} ${s.keywords.join(" ")}`
      .toLowerCase().includes(q)
  ));
});
</script>
</body>
</html>
"""



# ----------------------------------------------------------------------------
# 3. ROUTES
# ----------------------------------------------------------------------------
@app.route("/")
def home():
    import json as _json
    html = PAGE_HTML.replace("__SERVICES_JSON__", _json.dumps(SERVICES))
    return Response(html, mimetype="text/html")


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
