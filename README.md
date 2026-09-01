# Departmental SIWES Assistant (DSA)

> A modular web-based SIWES management platform designed to support students, departmental SIWES coordinators, and tertiary institutions throughout the Student Industrial Work Experience Scheme (SIWES).

## 📌 Project Overview

The Departmental SIWES Assistant (DSA) is being developed to simplify the management of SIWES for students and academic departments.

For students, DSA provides tools for discovering relevant placement opportunities, accessing SIWES guidance, managing profiles, and tracking industrial training applications.

For departmental SIWES coordinators, the platform is designed to provide administrative tools for managing participating students, monitoring placement and SIWES progress, maintaining departmental information, and supporting students throughout their industrial training.

DSA is designed with future multi-institution support in mind, allowing different tertiary institutions and departments to use the platform while maintaining separate students, coordinators, and administrative access.

### Key Objectives

1. **Placement Discovery**: Help students discover relevant SIWES and industrial training organizations based on location, field of study, interests, and skills.

2. **SIWES Knowledge Base**: Provide practical guidance on SIWES requirements, logbooks, reports, supervision, documentation, and preparation.

3. **Application Tracking**: Allow students to monitor their placement applications from initial interest through acceptance or rejection.

4. **Coordinator Support**: Provide departmental SIWES coordinators with tools for managing and monitoring students within their departments.

5. **Data Integrity**: Clearly distinguish verified organizations, researched opportunities, and student-submitted information.

6. **Extensible Architecture**: Maintain a modular architecture that can support multiple institutions, departments, live placement research, role-based access, and future AI capabilities.
---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+
- **Web Framework**: Flask 3.0+ (Modular Blueprints architecture)
- **Database & ORM**: SQLite 3 with Flask-SQLAlchemy
- **Frontend**: Responsive HTML5 & Vanilla CSS (Custom Design System, Google Fonts, Mobile-Friendly)
- **Configuration**: `python-dotenv` with `.env` environment variables

---

## 📂 Project Structure

```
departmental_siwes_assistant/
│
├── app.py                     # Main application factory & development server
├── config.py                  # Environment-specific configuration classes
├── requirements.txt           # Python dependency specifications
├── seed.py                    # Database seeder with guides & verified tech firms
├── README.md                  # Complete project documentation & guide
├── .gitignore                 # Standard Python/Flask/SQLite ignore rules
├── .env.example               # Template for environment variables
├── .env                       # Active local environment settings
│
├── models/                    # SQLAlchemy Database Models
│   ├── __init__.py            # Model exports and database instance
│   ├── db.py                  # Shared SQLAlchemy db instance
│   ├── student.py             # StudentProfile model
│   ├── organization.py        # Organization model (with status & sources)
│   ├── application.py         # PlacementApplication & SavedOrganization models
│   └── guide.py               # GuideTopic model (editable SIWES knowledge base)
│
├── routes/                    # Modular Flask Blueprints
│   ├── __init__.py            # Blueprint registry
│   ├── main.py                # Home, SIWES Guide, and About routes
│   ├── student.py             # Student Profile and Command Dashboard routes
│   ├── placement.py           # Placement Search, Details, Save & Tracker routes
│   └── admin.py               # Secure Admin Console routes
│
├── services/                  # Business Logic & Search Services
│   ├── __init__.py
│   └── placement_search.py    # Database filter engine & Live Web API adapter
│
├── templates/                 # Jinja2 HTML Templates
│   ├── base.html              # Base layout with responsive navbar & footer
│   ├── index.html             # Homepage with stats, steps, and hero search
│   ├── siwes_guide.html       # SIWES Guide reader with sidebar navigation
│   ├── profile.html           # Student profile creation & edit form
│   ├── placement.html         # Interactive placement filter form
│   ├── results.html           # Placement result cards with verification tags
│   ├── organization.html      # Organization details & application tracker
│   ├── dashboard.html         # Student dashboard (Stats, Pipeline, Bookmarks)
│   ├── submit_org.html        # Student submission form for new companies
│   ├── about.html             # About DSA project and SIWES framework
│   └── admin/                 # Administration Views
│       ├── login.html         # Secure admin login
│       ├── dashboard.html     # Admin statistics & pending submissions
│       ├── organizations.html # Organization manager
│       ├── org_form.html      # Add/edit organization
│       ├── guides.html        # Guide topic manager
│       └── guide_form.html    # Add/edit guide topic
│
├── static/                    # Frontend Static Assets
│   ├── css/
│   │   └── style.css          # Modern custom CSS design system
│   └── js/
│       └── main.js            # Dynamic dropdowns, alerts, and modal logic
│
└── instance/
    └── database.db            # SQLite database file (generated on first run)
```

---

## 🚀 Setup and Installation Instructions

### Step 1: Clone the Repository

Clone the project from GitHub:

```powershell
git clone https://github.com/shinkomania/departmental-siwes-assistant.git
```

Navigate into the project directory:

```powershell
cd departmental-siwes-assistant
```

### Step 2: Create and Activate a Virtual Environment

Create a Python virtual environment:

```powershell
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file based on `.env.example` and configure the required local environment variables.

Do not commit the `.env` file or any passwords, API keys, secret keys, or other private credentials to GitHub.

### Step 5: Initialize the Database

```powershell
python seed.py
```

This initializes the local development database with the data required by the application.

### Step 6: Start the Flask Development Server

```powershell
python app.py
```

### Step 7: Open the Application

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

This address is used for local development. A public deployment URL will be provided separately when the application is deployed.

## 🔑 Administrative Access

Administrative credentials are configured using environment variables and are not stored in the repository.

Copy `.env.example` to `.env` for local development and configure your private administrative credentials there.

Never commit `.env`, passwords, API keys, secret keys, or other production credentials to the repository.

---

## 💡 Core Features Implemented

1. **Home Page**  
   Provides a central entry point to DSA with quick access to SIWES guidance, placement search, student tools, key information, and featured resources.

2. **SIWES Guide**  
   Provides structured guidance covering important areas of the Student Industrial Work Experience Scheme, including:
   - SIWES and ITF background
   - Objectives and purpose of industrial training
   - Preparation and required documentation
   - Introductory letters and ITF forms
   - Choosing a suitable SIWES placement
   - Daily logbook documentation and weekly summaries
   - Technical report preparation
   - Institutional and ITF supervision
   - Common SIWES challenges and practical guidance

3. **Student Profile**  
   Allows students to create and manage profiles containing relevant academic, location, skills, and industrial training preferences.

4. **Placement Finder**  
   Enables students to search available organizations and placement information using criteria such as location, field of interest, and keywords.

5. **Organization Source and Status Labels**  
   Provides transparency about how organization information entered the platform. Records can be identified according to their source or review status, including:
   - Admin-reviewed organization records
   - Online research results where supported by configured search services
   - Student-submitted organizations awaiting review

6. **Organization Details**  
   Provides available information about an organization, such as location, industry or field, website, contact information, source information, and relevance to industrial training.

7. **Application Pipeline Tracker**  
   Allows students to monitor the progress of their placement applications through stages such as:
   `Interested → Contacted → Application Submitted → Interview → Accepted / Rejected`

   Students can also maintain follow-up notes associated with their applications.

8. **Student Dashboard**  
   Provides students with an overview of their profile, saved organizations, placement applications, and application progress.

9. **Organization Submission**  
   Allows students to suggest organizations that may provide SIWES opportunities. Submitted information can be reviewed before being treated as an approved platform record.

10. **Administrative Console**  
    Provides administrative tools for managing organization records, reviewing student-submitted organizations, and maintaining SIWES guide content.

11. **Modular Placement Search Service**  
    The `services/placement_search.py` service separates placement-search logic from the main application and provides a foundation for integrating external search providers and live opportunity research in future versions.

12. **Modular Flask Architecture**  
    DSA uses separate models, routes, services, templates, and configuration components, making the application easier to maintain and extend as new SIWES management features are introduced.
---

## 🔮 Future Roadmap & AI Extensions


- **Multi-Institution Support**: Allow multiple universities and tertiary institutions to use DSA independently.

- **Department Management**: Organize students and SIWES activities according to institution and academic department.

- **Departmental Coordinator Accounts**: Provide authorized SIWES coordinators with role-based administrative accounts.

- **Student Monitoring**: Enable coordinators to monitor student placement status, SIWES progress, and relevant submissions within their departments.

- **Role-Based Access Control**: Separate permissions for students, departmental coordinators, institutional administrators, and platform administrators.

- **Placement Verification Workflow**: Allow authorized coordinators or administrators to review and verify placement organizations and student-submitted opportunities.

- **AI SIWES Assistant**: Provide natural-language assistance for SIWES questions, documentation, workplace guidance, and institutional requirements.

- **AI Logbook Assistant**: Help students transform rough daily activity notes into properly structured technical logbook entries while preserving the student's actual work.

- **Automated Report Reviewer**: Assist students in reviewing SIWES technical reports for structure, completeness, and technical presentation.

- **Live Placement Research**: Integrate external search services to discover current industrial training opportunities and relevant organizations.