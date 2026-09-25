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
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>CivicAI — AI Assistant</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#050308; --shell:#0E0B16; --panel:#14101F; --panel-2:#1B1629;
    --border:rgba(255,255,255,0.07); --text:#EDEBF7; --dim:#9C96B3; --dim-2:#6E687F;
    --violet:#8B5CF6; --violet-2:#C084FC; --grad:linear-gradient(135deg,#7C5CFC 0%,#C084FC 100%);
    --radius-lg:22px; --radius-md:14px; --radius-sm:10px;
  }
  *{ box-sizing:border-box; }
  body{
    margin:0; background:var(--bg); color:var(--text);
    font-family:"Plus Jakarta Sans", Arial, sans-serif;
    min-height:100vh; display:flex; align-items:center; justify-content:center; padding:22px;
  }
  button, input{ font-family:inherit; }

  .shell{
    width:100%; max-width:1360px; min-height:88vh; background:var(--shell);
    border:1px solid rgba(139,92,246,0.22); border-radius:var(--radius-lg);
    box-shadow:0 0 90px rgba(139,92,246,0.14), 0 20px 60px rgba(0,0,0,0.5);
    display:flex; overflow:hidden;
  }

  /* ---------- sidebar ---------- */
  .sidebar{ width:236px; flex-shrink:0; border-right:1px solid var(--border); padding:22px 16px; display:flex; flex-direction:column; }
  .brand{ display:flex; align-items:center; gap:10px; padding:4px 8px 24px; }
  .brand-mark{ width:32px; height:32px; border-radius:9px; background:var(--grad); display:flex; align-items:center; justify-content:center; font-size:15px; }
  .brand-name{ font-weight:700; font-size:1.02rem; }

  .nav-section-label{ font-size:0.68rem; color:var(--dim-2); letter-spacing:0.06em; margin:18px 10px 8px; }
  .nav{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; }
  .nav button{
    width:100%; display:flex; align-items:center; gap:10px; padding:10px 12px; border-radius:var(--radius-sm);
    background:none; border:none; color:var(--dim); font-size:0.88rem; cursor:pointer; text-align:left;
  }
  .nav button:hover{ background:var(--panel); color:var(--text); }
  .nav button.active{ background:var(--grad); color:#fff; }
  .nav svg{ width:17px; height:17px; flex-shrink:0; }

  .sidebar-spacer{ flex:1; }
  .upsell{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-md); padding:14px; margin:10px 4px 12px; }
  .upsell-icon{ width:26px; height:26px; border-radius:8px; background:var(--grad); display:flex; align-items:center; justify-content:center; font-size:13px; margin-bottom:10px; }
  .upsell p{ margin:0 0 12px; font-size:0.78rem; color:var(--dim); line-height:1.4; }
  .upsell button{ width:100%; padding:9px; border:none; border-radius:var(--radius-sm); background:var(--grad); color:#fff; font-weight:600; font-size:0.8rem; cursor:pointer; }
  .logout{ display:flex; align-items:center; gap:10px; padding:10px 12px; color:var(--dim); font-size:0.85rem; background:none; border:none; cursor:pointer; }
  .logout:hover{ color:var(--text); }

  /* ---------- main ---------- */
  .main{ flex:1; display:flex; flex-direction:column; min-width:0; }
  .topbar{ display:flex; align-items:center; gap:16px; padding:18px 26px; border-bottom:1px solid var(--border); }
  .search{ flex:1; display:flex; align-items:center; gap:8px; background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-sm); padding:9px 14px; color:var(--dim-2); font-size:0.85rem; max-width:340px; }
  .search svg{ width:15px; height:15px; }
  .top-actions{ display:flex; align-items:center; gap:14px; margin-left:auto; color:var(--dim); }
  .user{ display:flex; align-items:center; gap:9px; }
  .user-avatar{ width:32px; height:32px; border-radius:50%; background:var(--grad); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.8rem; color:#fff; }
  .user-name{ font-size:0.85rem; font-weight:600; }
  .user-sub{ font-size:0.72rem; color:var(--dim-2); }

  .view{ flex:1; padding:26px; overflow-y:auto; }
  .view.hidden{ display:none; }

  .view-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:22px; }
  .view-head h1{ font-size:1.15rem; margin:0; }
  .view-actions{ display:flex; gap:10px; }
  .btn-ghost{ display:flex; align-items:center; gap:6px; padding:8px 14px; border-radius:var(--radius-sm); border:1px solid var(--border); background:var(--panel); color:var(--dim); font-size:0.82rem; cursor:pointer; }
  .btn-ghost:hover{ color:var(--text); border-color:rgba(139,92,246,0.4); }
  .btn-grad{ padding:8px 16px; border-radius:var(--radius-sm); border:none; background:var(--grad); color:#fff; font-size:0.82rem; font-weight:600; cursor:pointer; }

  /* ---------- dashboard ---------- */
  .stat-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px,1fr)); gap:14px; margin-bottom:26px; }
  .stat-card{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-md); padding:18px; }
  .stat-card .num{ font-size:1.6rem; font-weight:700; }
  .stat-card .label{ font-size:0.78rem; color:var(--dim); margin-top:4px; }
  .quick-section h2{ font-size:0.95rem; margin:0 0 12px; }
  .quick-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:12px; }
  .quick-card{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-md); padding:16px; cursor:pointer; }
  .quick-card:hover{ border-color:rgba(139,92,246,0.4); }
  .quick-card .title{ font-weight:600; font-size:0.88rem; margin-bottom:4px; }
  .quick-card .sub{ font-size:0.76rem; color:var(--dim); }

  /* ---------- services ---------- */
  .svc-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(280px,1fr)); gap:14px; }
  .svc-card{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-md); overflow:hidden; }
  .svc-card-head{ padding:16px; cursor:pointer; }
  .svc-code{ font-size:0.72rem; color:var(--violet-2); }
  .svc-name{ font-weight:700; font-size:0.98rem; margin:4px 0 6px; }
  .svc-cat{ font-size:0.76rem; color:var(--dim); }
  .svc-body{ max-height:0; overflow:hidden; transition:max-height 0.25s ease; border-top:1px solid transparent; }
  .svc-card.open .svc-body{ max-height:500px; border-top:1px solid var(--border); }
  .svc-body-inner{ padding:14px 16px 18px; font-size:0.83rem; color:var(--dim); }
  .svc-body-inner p{ color:var(--text); margin:0 0 10px; }
  .svc-field-label{ color:var(--violet-2); font-size:0.7rem; display:block; margin-bottom:3px; }
  .svc-field{ margin-bottom:10px; }
  .svc-body-inner ol{ margin:0; padding-left:16px; }
  .svc-ask{ margin-top:4px; font-size:0.78rem; background:none; border:1px solid var(--border); color:var(--violet-2); padding:7px 12px; border-radius:var(--radius-sm); cursor:pointer; }

  /* ---------- assistant ---------- */
  .assistant-body{ display:flex; flex-direction:column; height:100%; min-height:520px; }
  .empty-state{ flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:20px; }
  .empty-icon{ width:56px; height:56px; border-radius:16px; background:var(--grad); display:flex; align-items:center; justify-content:center; font-size:24px; margin-bottom:18px; }
  .empty-state h2{ font-size:1.3rem; margin:0 0 26px; }

  .ask-pill{ width:100%; max-width:640px; background:var(--panel); border:1px solid rgba(139,92,246,0.3); border-radius:18px; padding:14px 16px; }
  .ask-pill input{ width:100%; background:none; border:none; color:var(--text); font-size:0.92rem; outline:none; }
  .ask-pill input::placeholder{ color:var(--dim-2); }
  .ask-pill-row{ display:flex; align-items:center; justify-content:space-between; margin-top:10px; }
  .ask-pill-icons{ display:flex; gap:10px; color:var(--dim-2); }
  .ask-send{ width:34px; height:34px; border-radius:50%; background:var(--grad); border:none; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; }

  .chip-row{ display:flex; gap:12px; margin-top:22px; flex-wrap:wrap; justify-content:center; max-width:640px; }
  .chip{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-md); padding:12px 16px; text-align:left; cursor:pointer; min-width:150px; }
  .chip:hover{ border-color:rgba(139,92,246,0.4); }
  .chip .chip-title{ font-size:0.82rem; font-weight:600; margin-bottom:3px; }
  .chip .chip-sub{ font-size:0.74rem; color:var(--dim); }

  .chat-window{ flex:1; overflow-y:auto; padding:8px 4px 20px; display:flex; flex-direction:column; gap:14px; }
  .chat-window.hidden{ display:none; }
  .msg{ max-width:74%; padding:12px 15px; border-radius:16px; font-size:0.9rem; white-space:pre-wrap; line-height:1.5; }
  .msg.user{ align-self:flex-end; background:var(--grad); color:#fff; border-bottom-right-radius:4px; }
  .msg.bot{ align-self:flex-start; background:var(--panel); border:1px solid var(--border); color:var(--text); border-bottom-left-radius:4px; }
  .msg.loading{ align-self:flex-start; color:var(--dim); font-style:italic; background:none; border:none; }

  .chat-input-dock{ display:none; padding-top:14px; border-top:1px solid var(--border); margin-top:auto; }
  .chat-input-dock.show{ display:block; }

  footer.disclaimer{ padding:14px 26px; border-top:1px solid var(--border); font-size:0.72rem; color:var(--dim-2); text-align:center; }

  @media (max-width:900px){
    .shell{ flex-direction:column; min-height:unset; }
    .sidebar{ width:100%; flex-direction:row; flex-wrap:wrap; border-right:none; border-bottom:1px solid var(--border); }
    .sidebar-spacer, .upsell{ display:none; }
    .nav{ flex-direction:row; flex-wrap:wrap; }
  }
</style>
</head>
<body>
<div class="shell">

  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">⌘</div>
      <div class="brand-name">CivicAI</div>
    </div>

    <div class="nav-section-label">MENU</div>
    <ul class="nav" id="main-nav">
      <li><button data-view="dashboard"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>Dashboard</button></li>
      <li><button data-view="services"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>Services</button></li>
      <li><button data-view="assistant" class="active"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.9 4.4L18 9l-4.1 1.9L12 15l-1.9-4.1L6 9l4.1-1.6L12 3z"/><path d="M19 15l.9 2 2 .9-2 .9-.9 2-.9-2-2-.9 2-.9.9-2z"/></svg>AI Assistant</button></li>
      <li><button data-view="alerts"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>Alerts</button></li>
      <li><button data-view="settings"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>Settings</button></li>
    </ul>

    <div class="nav-section-label">CATEGORIES</div>
    <ul class="nav" id="cat-nav"></ul>

    <div class="sidebar-spacer"></div>

    <div class="upsell">
      <div class="upsell-icon">✓</div>
      <p>All guidance here is informational. Always confirm details on the official portal before applying.</p>
      <button type="button" id="upsell-btn">Got it</button>
    </div>
    <button class="logout" type="button"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg> Logout</button>
  </aside>

  <div class="main">
    <div class="topbar">
      <div class="search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        Search services...
      </div>
      <div class="top-actions">
        <div class="user">
          <div class="user-avatar">C</div>
          <div>
            <div class="user-name">Citizen</div>
            <div class="user-sub">Guest session</div>
          </div>
        </div>
      </div>
    </div>

    <!-- DASHBOARD -->
    <section class="view" id="view-dashboard">
      <div class="view-head"><h1>Dashboard</h1></div>
      <div class="stat-grid">
        <div class="stat-card"><div class="num">8</div><div class="label">Services available</div></div>
        <div class="stat-card"><div class="num">6</div><div class="label">Categories covered</div></div>
        <div class="stat-card"><div class="num">24/7</div><div class="label">Assistant availability</div></div>
      </div>
      <div class="quick-section">
        <h2>Popular questions</h2>
        <div class="quick-grid" id="quick-grid"></div>
      </div>
    </section>

    <!-- SERVICES -->
    <section class="view hidden" id="view-services">
      <div class="view-head"><h1>Service directory</h1></div>
      <div class="svc-grid" id="svc-grid"></div>
    </section>

    <!-- AI ASSISTANT -->
    <section class="view" id="view-assistant">
      <div class="view-head">
        <h1>AI Assistant</h1>
        <div class="view-actions">
          <button class="btn-ghost" id="new-chat">New Chat</button>
          <button class="btn-grad" id="share-btn">Share</button>
        </div>
      </div>

      <div class="assistant-body">
        <div class="empty-state" id="empty-state">
          <div class="empty-icon">⌘</div>
          <h2>What can I help with?</h2>
          <div class="ask-pill">
            <input type="text" id="ask-input" placeholder="Ask anything about public services..." autocomplete="off" />
            <div class="ask-pill-row">
              <div class="ask-pill-icons">
                <span>＋</span><span>🔗</span><span>🖼</span>
              </div>
              <button class="ask-send" id="ask-send">➤</button>
            </div>
          </div>
          <div class="chip-row" id="chip-row"></div>
        </div>

        <div class="chat-window hidden" id="chat-window"></div>

        <div class="chat-input-dock" id="chat-input-dock">
          <div class="ask-pill">
            <input type="text" id="chat-input" placeholder="Ask another question..." autocomplete="off" />
            <div class="ask-pill-row">
              <div class="ask-pill-icons"><span>＋</span><span>🔗</span></div>
              <button class="ask-send" id="chat-send">➤</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ALERTS -->
    <section class="view hidden" id="view-alerts">
      <div class="view-head"><h1>Alerts</h1></div>
      <div class="stat-card" style="max-width:520px;">
        <div class="label" style="margin-top:0;">CivicAI provides informational guidance and is not a government authority. Please verify current eligibility, documents and application requirements through the relevant official government portal, since rules can change.</div>
      </div>
    </section>

    <!-- SETTINGS -->
    <section class="view hidden" id="view-settings">
      <div class="view-head"><h1>Settings</h1></div>
      <div class="stat-card" style="max-width:520px;">
        <div class="label" style="margin-top:0;">Settings are not required to use CivicAI — this is a stateless assistant with no account or saved data.</div>
      </div>
    </section>

    <footer class="disclaimer">CivicAI provides informational guidance and is not a government authority. Verify details on the relevant official portal.</footer>
  </div>
</div>

<script>
  const SERVICES = __SERVICES_JSON__;

  /* ---------- view switching ---------- */
  const navButtons = document.querySelectorAll("#main-nav button");
  const views = { dashboard: "view-dashboard", services: "view-services", assistant: "view-assistant", alerts: "view-alerts", settings: "view-settings" };
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      navButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      Object.values(views).forEach(id => document.getElementById(id).classList.add("hidden"));
      document.getElementById(views[btn.dataset.view]).classList.remove("hidden");
    });
  });

  /* ---------- category nav (sidebar) ---------- */
  const catNav = document.getElementById("cat-nav");
  const categories = [...new Set(SERVICES.map(s => s.category))];
  categories.forEach(cat => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.textContent = cat;
    btn.addEventListener("click", () => {
      navButtons.forEach(b => b.classList.remove("active"));
      Object.values(views).forEach(id => document.getElementById(id).classList.add("hidden"));
      document.getElementById("view-services").classList.remove("hidden");
    });
    li.appendChild(btn);
    catNav.appendChild(li);
  });

  /* ---------- dashboard quick questions ---------- */
  const quickGrid = document.getElementById("quick-grid");
  const QUICK = [
    { title: "Scholarships", sub: "How do I apply for a scholarship?", q: "How do I apply for a scholarship?" },
    { title: "Income Certificate", sub: "What documents are needed?", q: "What documents do I need for an income certificate?" },
    { title: "Healthcare Schemes", sub: "Am I eligible?", q: "How do I check eligibility for healthcare schemes?" },
  ];
  QUICK.forEach(item => {
    const card = document.createElement("div");
    card.className = "quick-card";
    card.innerHTML = `<div class="title">${item.title}</div><div class="sub">${item.sub}</div>`;
    card.addEventListener("click", () => goToAssistantWith(item.q));
    quickGrid.appendChild(card);
  });

  /* ---------- services grid ---------- */
  const svcGrid = document.getElementById("svc-grid");
  SERVICES.forEach(s => {
    const card = document.createElement("div");
    card.className = "svc-card";
    const stepsHtml = s.steps.map(st => `<li>${st}</li>`).join("");
    card.innerHTML = `
      <div class="svc-card-head">
        <div class="svc-code">${s.code}</div>
        <div class="svc-name">${s.name}</div>
        <div class="svc-cat">${s.category}</div>
      </div>
      <div class="svc-body">
        <div class="svc-body-inner">
          <p>${s.description}</p>
          <div class="svc-field"><span class="svc-field-label">Eligibility</span>${s.eligibility}</div>
          <div class="svc-field"><span class="svc-field-label">Documents</span>${s.documents.join(", ")}</div>
          <div class="svc-field"><span class="svc-field-label">Steps</span><ol>${stepsHtml}</ol></div>
          <button class="svc-ask" type="button">Ask CivicAI about this</button>
        </div>
      </div>`;
    card.querySelector(".svc-card-head").addEventListener("click", () => card.classList.toggle("open"));
    card.querySelector(".svc-ask").addEventListener("click", (e) => {
      e.stopPropagation();
      goToAssistantWith(`Tell me more about ${s.name}`);
    });
    svcGrid.appendChild(card);
  });

  /* ---------- assistant chip suggestions ---------- */
  const chipRow = document.getElementById("chip-row");
  const CHIPS = [
    { title: "Scholarships", sub: "How do I apply?", q: "How do I apply for a scholarship?" },
    { title: "Income Certificate", sub: "Required documents", q: "What documents do I need for an income certificate?" },
    { title: "Healthcare Schemes", sub: "Check eligibility", q: "How do I check eligibility for healthcare schemes?" },
  ];
  CHIPS.forEach(c => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.innerHTML = `<div class="chip-title">${c.title}</div><div class="chip-sub">${c.sub}</div>`;
    chip.addEventListener("click", () => sendMessage(c.q));
    chipRow.appendChild(chip);
  });

  /* ---------- assistant chat logic ---------- */
  const emptyState = document.getElementById("empty-state");
  const chatWindow = document.getElementById("chat-window");
  const chatDock = document.getElementById("chat-input-dock");
  const askInput = document.getElementById("ask-input");
  const askSend = document.getElementById("ask-send");
  const chatInput = document.getElementById("chat-input");
  const chatSend = document.getElementById("chat-send");
  const newChatBtn = document.getElementById("new-chat");
  const shareBtn = document.getElementById("share-btn");

  function goToAssistantWith(question) {
    navButtons.forEach(b => b.classList.remove("active"));
    document.querySelector('[data-view="assistant"]').classList.add("active");
    Object.values(views).forEach(id => document.getElementById(id).classList.add("hidden"));
    document.getElementById("view-assistant").classList.remove("hidden");
    sendMessage(question);
  }

  function appendMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `msg ${sender}`;
    msg.textContent = text;
    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return msg;
  }

  function enterChatMode() {
    emptyState.style.display = "none";
    chatWindow.classList.remove("hidden");
    chatDock.classList.add("show");
  }

  async function sendMessage(message) {
    if (!message || !message.trim()) return;
    enterChatMode();
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

  askSend.addEventListener("click", () => { sendMessage(askInput.value.trim()); askInput.value = ""; });
  askInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { sendMessage(askInput.value.trim()); askInput.value = ""; } });
  chatSend.addEventListener("click", () => { sendMessage(chatInput.value.trim()); chatInput.value = ""; });
  chatInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { sendMessage(chatInput.value.trim()); chatInput.value = ""; } });

  newChatBtn.addEventListener("click", () => {
    chatWindow.innerHTML = "";
    chatWindow.classList.add("hidden");
    chatDock.classList.remove("show");
    emptyState.style.display = "flex";
  });

  shareBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      shareBtn.textContent = "Link copied";
      setTimeout(() => { shareBtn.textContent = "Share"; }, 1500);
    } catch (err) { /* clipboard not available, ignore */ }
  });

  document.getElementById("upsell-btn").addEventListener("click", () => {
    document.querySelector(".upsell").style.display = "none";
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
