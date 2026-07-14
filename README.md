# MediFlow AI — Intelligent Hospital Ecosystem

MediFlow AI is a next-generation hospital management and patient triage ecosystem powered by Artificial Intelligence. It streamlines the entire patient journey from initial symptom triage (via text, voice, and image) to queue management, doctor consultations, and pharmacy dispensing.

Built with **Streamlit**, **Supabase**, and **Groq**, MediFlow AI offers a completely role-based, reactive, and professionally designed minimalist user experience.

---

## Key Features

### Multimodal AI Triage Nurse
- **Text, Audio, and Image Support:** Patients can describe their symptoms, upload images (e.g., rashes or injuries), or send voice notes.
- **Intelligent Follow-ups:** The conversational AI asks targeted follow-up questions to understand the severity and details of the symptoms.
- **Smart Routing:** The AI automatically categorizes the urgency (Routine, Semi-Urgent, Urgent, Emergency) and assigns the patient to the most appropriate medical department.

### Role-Based Dashboards
MediFlow AI features 5 distinct, highly customized dashboards with persistent sessions:
1. **Patient Portal:** Conversational AI Triage, live queue tracking with estimated wait times, digital prescriptions, and visit history.
2. **Receptionist Dashboard:** Live hospital queue overview, AI triage confirmation, and manual patient registration.
3. **Doctor Dashboard:** Live patient queue, AI-generated triage reports (so doctors have full context before the patient walks in), and a digital prescription pad.
4. **Pharmacy Dashboard:** Real-time prescription queue and inventory management.
5. **Admin Dashboard:** High-level hospital analytics, staff management, and system configuration.

### Premium Professional UI/UX
- **Minimalist Solid-Color Design:** The application features a clean, highly professional UI that utilizes a custom solid color palette, removing distracting elements for a streamlined workflow.
- **Top Navigation Bar:** Replaced traditional sidebars with a dynamic, responsive horizontal top navbar.
- **Trust-Building Landing Page:** A professionally designed landing page featuring hospital performance metrics, compelling taglines, and integrated login/registration workflows.
- **Fully Responsive:** The custom-built navigation system seamlessly adapts to Desktop, Tablet, and Mobile devices (including a mobile hamburger menu).
- **Real-Time Workflow Tracker:** Patients can track exactly where they are in the hospital pipeline (Triaged -> In Queue -> With Doctor -> Prescribed -> At Pharmacy).

---

## Technology Stack

- **Frontend:** Streamlit (Python), Custom CSS/HTML
- **Backend/Database:** Supabase (PostgreSQL), Supabase Auth
- **AI/LLM:** Groq API (qwen/qwen3.6-27b for multimodal vision/audio, llama-3.3-70b for reasoning)
- **Agent Orchestration:** LangChain and LangGraph
- **Environment Management:** python-dotenv

---

## Getting Started

### 1. Prerequisites
- Python 3.9+
- A Supabase account and project.
- A Groq API key.

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

## Security Note
**Never commit your `.env` file to version control.** If you accidentally push your API keys or Supabase Service Role keys to GitHub, immediately revoke them and generate new ones to prevent unauthorized access to your database.

---
*Built for the future of healthcare.*
