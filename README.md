# MediFlow AI — Intelligent Hospital Ecosystem 🏥

MediFlow AI is a next-generation hospital management and patient triage ecosystem powered by Artificial Intelligence. It streamlines the entire patient journey from initial symptom triage (via text, voice, and image) to queue management, doctor consultations, and pharmacy dispensing.

Built with **Streamlit**, **Supabase**, and **Groq (Qwen/Llama)**, MediFlow AI offers a completely role-based, reactive, and beautifully designed user experience.

---

## 🌟 Key Features

### 🤖 Multimodal AI Triage Nurse
- **Text, Audio, & Image Support:** Patients can describe their symptoms, upload images (e.g., rashes or injuries), or send voice notes.
- **Intelligent Follow-ups:** The AI asks targeted follow-up questions to understand the severity and details of the symptoms.
- **Smart Routing:** The AI automatically categorizes the urgency (Routine, Semi-Urgent, Urgent, Emergency) and assigns the patient to the most appropriate medical department.

### 👥 Role-Based Dashboards
MediFlow AI features 5 distinct, highly customized dashboards with persistent sessions:
1. **Patient Portal:** AI Triage, live queue tracking with estimated wait times, digital prescriptions, and visit history.
2. **Receptionist Dashboard:** Live hospital queue overview, AI triage confirmation, and manual patient registration.
3. **Doctor Dashboard:** Live patient queue, AI-generated triage reports (so doctors have full context before the patient walks in), and a digital prescription pad.
4. **Pharmacy Dashboard:** Real-time prescription queue and inventory management.
5. **Admin Dashboard:** High-level hospital analytics, staff management, and system configuration.

### 🎨 Premium UI/UX
- **Fully Responsive:** Custom-built navigation system that seamlessly adapts to Desktop, Tablet, and Mobile devices (including a mobile hamburger menu).
- **Dark Mode Support:** Beautiful dark mode interface with glowing active states and soft gradients.
- **Real-Time Workflow Tracker:** Patients can track exactly where they are in the hospital pipeline (Triaged ➔ In Queue ➔ With Doctor ➔ Prescribed ➔ At Pharmacy).

---

## 🛠️ Technology Stack

- **Frontend:** Streamlit (Python), Custom CSS/HTML
- **Backend/Database:** Supabase (PostgreSQL), Supabase Auth
- **AI/LLM:** Groq API (`qwen/qwen3.6-27b` for multimodal vision/audio, `llama-3.3-70b` for reasoning)
- **Agent Orchestration:** LangChain & LangGraph
- **Environment Management:** `python-dotenv`

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A [Supabase](https://supabase.com/) account and project.
- A [Groq](https://groq.com/) API key.

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/Coding-Philic/hospital-ecosystem.git
cd "hospital ecosystem"

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory (make sure it is ignored by git!). You will need your Supabase keys and Groq API key:

```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Primary AI Model (Groq)
PRIMARY_MODEL=qwen/qwen3.6-27b

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
```

### 4. Database Setup
A SQL setup script is provided. Execute the contents of `setup_database.sql` in your Supabase SQL Editor to initialize the database tables, policies, and initial test data.

### 5. Run the Application
Start the Streamlit server:

```bash
streamlit run app.py
```
The application will be available at `http://localhost:8501`.

---

## 🔐 Security Note
**Never commit your `.env` file to version control.** If you accidentally push your API keys or Supabase Service Role keys to GitHub, immediately revoke them and generate new ones to prevent unauthorized access to your database.

---
*Built for the future of healthcare.*
