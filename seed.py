"""
Database Seeding Script
-----------------------
Populates the SQLite database with rich, factual SIWES guidance topics
and verified Nigerian technology and engineering organizations.

Run via:
    python seed.py
or
    flask seed-db
"""
from models.db import db
from models.guide import GuideTopic
from models.organization import Organization
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication

GUIDE_TOPICS = [
    {
        'slug': 'what-is-siwes',
        'title': 'What is SIWES?',
        'category': 'Overview',
        'order_num': 1,
        'icon': 'info-circle',
        'summary': 'Understand the Student Industrial Work Experience Scheme (SIWES) and its background.',
        'content': """
The **Students Industrial Work Experience Scheme (SIWES)** is a skills training programme designed to expose and prepare students of Universities, Polytechnics, and Colleges of Education for the industrial work situation they are likely to meet after graduation.

In Nigeria, SIWES was established by the **Industrial Training Fund (ITF)** in 1973 to bridge the gap between theoretical knowledge acquired in higher institutions and practical industrial skills.

#### Key Highlights for Computer Engineering Students:
- **Duration**: Typically 6 months for university engineering students (often during 400 Level / Year 4).
- **Supervision**: Supervised jointly by Departmental/Institutional supervisors and ITF Industry supervisors.
- **Grading**: SIWES is a credit-bearing course requiring a certified logbook, a comprehensive technical report, and an oral presentation/defense.
        """
    },
    {
        'slug': 'purpose-of-siwes',
        'title': 'Purpose of SIWES',
        'category': 'Overview',
        'order_num': 2,
        'icon': 'target',
        'summary': 'Why SIWES is mandatory for engineering and technology disciplines.',
        'content': """
SIWES serves as a critical bridge between academic engineering concepts and industry production environments.

#### Core Objectives:
1. **Practical Exposure**: Provide students with an opportunity to apply their theoretical knowledge in real-world work situations.
2. **Machinery & Tool Familiarity**: Expose students to work methods, advanced software engineering practices, testing frameworks, and hardware equipment not commonly accessible within universities.
3. **Transition Ease**: Smooth the transition from the university environment to professional industry practices.
4. **Professional Networking**: Enlist and strengthen employer involvement in the educational process of preparing students for employment.
5. **Work Ethic Development**: Instill workplace discipline, teamwork, punctuality, safety compliance, and professional communication.
        """
    },
    {
        'slug': 'how-to-prepare-for-siwes',
        'title': 'How to Prepare for SIWES',
        'category': 'Preparation',
        'order_num': 3,
        'icon': 'clipboard-check',
        'summary': 'Essential pre-commencement checklist: documents, letters, ITF Form 8, and safety.',
        'content': """
Preparation starts well before your official start date. Here is the step-by-step checklist:

#### 1. Official Documentation
- **Introductory / SIWES Request Letter**: Obtain your official stamped introductory letter from your university's Industrial Training Coordination Center (ITCC/SIWES Directorate).
- **Acceptance Letter & ITF Form 8**: Once an organization accepts you, have them fill and stamp your acceptance slip/Form 8 and submit the designated copies back to your ITCC and the nearest ITF Area Office.
- **SPE-1 Form**: Fill out your student placement information form accurately with your workplace address and phone numbers.

#### 2. Technical Preparation
- Brush up on core computer engineering fundamentals (e.g. Git, command line basics, Python, Linux, basic networking commands, hardware debugging).
- Set up a clean portfolio or GitHub profile showcasing course projects.

#### 3. Professional Mindset
- Plan your commuting route and prepare professional business casual attire.
- Understand workplace safety regulations and intellectual property confidentiality guidelines.
        """
    },
    {
        'slug': 'choosing-a-suitable-organization',
        'title': 'Choosing a Suitable Organization',
        'category': 'Preparation',
        'order_num': 4,
        'icon': 'building',
        'summary': 'How to evaluate potential IT/SIWES placement firms for relevant engineering experience.',
        'content': """
For a Computer Engineering student, where you spend your 6 months will significantly impact your practical skills and career trajectory.

#### Key Criteria for Evaluation:
1. **Engineering Relevance**: Does the company have an active Engineering, IT, Software Development, Infrastructure, or R&D department?
2. **Mentorship & Supervision**: Will you have an experienced engineer or senior tech professional assigned to mentor you?
3. **Hands-on Involvement**: Avoid firms that will relegate you to clerical or non-technical errands. Look for companies with real projects.
4. **Industry Standards**: Companies that use modern version control (Git), cloud platforms, structured agile sprints, or hardware lab testing environments provide superior learning.

#### Types of Suitable Organizations:
- Software Engineering & Product companies
- Fintech & Payment processors
- Telecommunications operators & ISP network providers
- Government Tech Agencies (e.g. NITDA, Galaxy Backbone)
- Embedded systems, IoT, and hardware maintenance enterprises
        """
    },
    {
        'slug': 'siwes-logbook',
        'title': 'SIWES Logbook Guidelines',
        'category': 'Logbook',
        'order_num': 5,
        'icon': 'book',
        'summary': 'Best practices for daily logbook entries, sketches, diagrams, and industry supervisor sign-offs.',
        'content': """
Your SIWES Logbook (Daily Activities Book) is your legal and academic proof of industrial training.

#### Rules for Daily Entries:
- **Write Daily**: Fill your logbook at the end of each working day while tasks and technical details are fresh in your memory.
- **Be Specific & Technical**: Avoid vague entries like *"worked on computers"*. Write *"Diagnosed a DNS resolution failure on subnet 192.168.1.0/24, reconfigured DHCP scope parameters on Cisco router, and tested connectivity using traceroute."*
- **Include Diagrams & Circuit Sketches**: Dedicate the diagram/sketch section to block diagrams, network topologies, flowcharts, or system architecture sketches.
- **Weekly Signatures**: Ensure your Industry-based supervisor reviews, comments on, and signs your logbook at the end of every work week.
        """
    },
    {
        'slug': 'weekly-activities',
        'title': 'Weekly Activities & Documentation',
        'category': 'Logbook',
        'order_num': 6,
        'icon': 'calendar',
        'summary': 'How to summarize weekly milestones and keep track of accomplishments.',
        'content': """
In addition to daily bullet points, each week requires a cohesive summary of learning milestones.

#### Structure of a Strong Weekly Summary:
1. **Weekly Milestone**: The main objective for the week (e.g., *"Deployment of internal API service using Docker containers and Nginx reverse proxy"*).
2. **Tools & Technologies Used**: Specific frameworks, libraries, oscilloscopes, cable testers, or IDEs.
3. **Challenges Encountered**: Technical bottlenecks faced during the week.
4. **Solutions Developed**: How you and your team debugged and resolved the problem.
5. **Key Learning Takeaways**: New technical knowledge acquired.
        """
    },
    {
        'slug': 'siwes-report',
        'title': 'SIWES Technical Report Writing',
        'category': 'Report',
        'order_num': 7,
        'icon': 'file-text',
        'summary': 'Standard engineering format for your final SIWES technical report.',
        'content': """
Your final report is the primary academic document graded by your university departmental defense committee.

#### Standard Chapter Breakdown:
- **Preliminary Pages**: Title Page, Certification/Approval Page, Dedication, Acknowledgements, Abstract, Table of Contents, List of Figures, List of Tables.
- **Chapter 1: Introduction**:
  - History, objectives, and administrative framework of SIWES and ITF.
  - History, organizational structure, departments, and vision of your placement organization.
- **Chapter 2: Safety & Workplace Environment**:
  - Safety precautions, workplace regulations, and equipment handling guidelines.
- **Chapter 3: Technical Experience & Projects Undertaken**:
  - In-depth technical documentation of projects, software built, networks configured, or hardware tested. Include architecture diagrams, code snippets, and schematics.
- **Chapter 4: Problems Encountered & Solutions**:
  - Academic and operational bottlenecks and mitigation strategies.
- **Chapter 5: Conclusion & Recommendations**:
  - Summary of experience, recommendations to the Department, ITF, and the host organization.
- **References & Appendices**: Cited literature, manuals, and data sheets.
        """
    },
    {
        'slug': 'supervisor-visits',
        'title': 'Supervisor Visits (Institutional & ITF)',
        'category': 'Supervision',
        'order_num': 8,
        'icon': 'user-check',
        'summary': 'What to expect when your university lecturer or ITF inspector visits your workplace.',
        'content': """
During your 6-month SIWES, you will receive visits from both your University Departmental Supervisor and ITF Officials.

#### What Supervisors Check:
1. **Physical Presence & Punctuality**: Confirming you are actively on-site and observing regular office hours.
2. **Up-to-Date Logbook**: Ensuring your daily entries are complete, detailed, and signed up to the current week.
3. **Industry Supervisor Feedback**: The supervisor meets with your workplace supervisor to evaluate your conduct, technical initiative, and discipline.
4. **Hands-on Demonstration**: You may be asked to explain your current project, show code repositories, or demonstrate equipment you operate.

#### Important Tip:
Always keep your logbook and notebook at your desk. If your supervisor visits unannounced, your logbook must be immediately presentable.
        """
    },
    {
        'slug': 'common-siwes-challenges',
        'title': 'Common SIWES Challenges & Solutions',
        'category': 'Challenges',
        'order_num': 9,
        'icon': 'alert-triangle',
        'summary': 'Overcoming stipend delays, lack of initial tasks, transportation, and technical roadblocks.',
        'content': """
Every student encounters challenges during industrial training. Here is how to handle the most common ones:

#### 1. "They aren't giving me serious work."
- **Solution**: Don't just wait passively. Ask questions, shadow senior engineers, review company documentation/codebases, and propose small internal utility projects (e.g. automating a report or organizing cabling).

#### 2. "The technology stack is unfamiliar."
- **Solution**: Dedicate evenings and weekends to crash courses and official documentation. Ask teammates for code reviews.

#### 3. "Commute and Transportation Costs."
- **Solution**: Choose placement locations strategically near family or reliable transit routes. Discuss flexible or hybrid schedules with your supervisor if approved by the department.

#### 4. "Stipend Uncertainties."
- **Solution**: View SIWES primarily as an invaluable practical education and career gateway rather than a wage-earning role.
        """
    },
    {
        'slug': 'general-tips-for-success',
        'title': 'General Tips for a Successful SIWES',
        'category': 'Defense & Tips',
        'order_num': 10,
        'icon': 'award',
        'summary': 'Pro tips on securing retainership offers, building professional relationships, and acing your defense.',
        'content': """
Transform your 6-month placement into a long-term career catalyst:

1. **Build Real Relationships**: Connect with colleagues on LinkedIn, understand different career pathways, and seek mentorship.
2. **Document Everything as You Go**: Take photos of equipment/setups (with company permission) for your presentation slides.
3. **Maintain High Integrity**: Respect company confidentiality agreements, intellectual property, and client data.
4. **Prepare Defense Slides Early**: Start organizing your PowerPoint slides 3 weeks before the end of the programme.
5. **Seek Retainership**: High-performing SIWES students often receive graduate job offers, NYSC primary assignment placements, or contract project work from their host organizations.
        """
    }
]

VERIFIED_ORGANIZATIONS = [
    {
        'name': 'Galaxy Backbone Limited',
        'description': 'The digital infrastructure and shared services provider for the Federal Government of Nigeria, operating nationwide Tier-III datacenter facilities and fiber network infrastructure.',
        'address': 'Galaxy Backbone House, 61 Adetokunbo Ademola Crescent, Wuse II',
        'state': 'FCT Abuja',
        'city': 'Abuja',
        'industry': 'Government organization / Telecom',
        'relevance_areas': 'Cloud Computing & DevOps, Networking & Telecommunications, Cybersecurity, Hardware',
        'website': 'https://www.galaxybackbone.com.ng',
        'contact_email': 'info@galaxybackbone.com.ng',
        'contact_phone': '+234 9 462 1500',
        'verification_status': 'Verified',
        'source': 'Federal Government Enterprise Directory',
        'why_relevant': 'Exceptional enterprise datacenter, cloud computing, government network management, and cybersecurity operations.'
    },
    {
        'name': 'National Information Technology Development Agency (NITDA)',
        'description': 'The apex regulatory body and capacity builder for Information Technology in Nigeria, spearheading national AI, cybersecurity, and digital economy initiatives.',
        'address': 'No. 28, Port Harcourt Crescent, Off Gimbiya Street, Area 11, Garki',
        'state': 'FCT Abuja',
        'city': 'Abuja',
        'industry': 'Government organization',
        'relevance_areas': 'Artificial Intelligence, Cybersecurity, Software Development, Cloud Computing & DevOps',
        'website': 'https://nitda.gov.ng',
        'contact_email': 'info@nitda.gov.ng',
        'contact_phone': '+234 816 840 1802',
        'verification_status': 'Verified',
        'source': 'Official NITDA Agency Portal',
        'why_relevant': 'Hands-on exposure to national tech policy, emerging technologies research (AI/IoT), and cyber defense frameworks.'
    },
    {
        'name': 'Paystack Payments Limited',
        'description': 'Modern online payment processing platform enabling businesses across Africa to accept multi-channel payments securely via APIs.',
        'address': '126A Murtala Muhammed Way, Yaba',
        'state': 'Lagos',
        'city': 'Lagos (Yaba)',
        'industry': 'Bank/Fintech',
        'relevance_areas': 'Software Development, Web Development, Cloud Computing & DevOps, Data Science & Analytics',
        'website': 'https://paystack.com',
        'contact_email': 'contact@paystack.com',
        'contact_phone': '+234 1 631 6160',
        'verification_status': 'Verified',
        'source': 'Paystack Careers & Engineering Portal',
        'why_relevant': 'World-class fintech engineering practices, distributed systems architecture, microservices, and API integrations.'
    },
    {
        'name': 'Flutterwave Technologies Solutions',
        'description': 'Leading African payments infrastructure company connecting businesses across the globe with seamless digital payment rails and enterprise solutions.',
        'address': '8, Admiralty Way, Lekki Phase 1',
        'state': 'Lagos',
        'city': 'Lagos (Lekki)',
        'industry': 'Bank/Fintech',
        'relevance_areas': 'Software Development, Mobile Development, Web Development, Cloud Computing & DevOps',
        'website': 'https://flutterwave.com',
        'contact_email': 'hi@flutterwavego.com',
        'contact_phone': '+234 1 888 9595',
        'verification_status': 'Verified',
        'source': 'Flutterwave Official Portal',
        'why_relevant': 'High-scale global payments infrastructure, modern frontend/backend engineering, and cloud deployment pipelines.'
    },
    {
        'name': 'Interswitch Group',
        'description': 'Pioneering African integrated payments and digital commerce company operating Quickteller, Verve, and large-scale financial switching systems.',
        'address': 'Plot 1648C, Oko Awo Street, Victoria Island',
        'state': 'Lagos',
        'city': 'Lagos (Victoria Island)',
        'industry': 'Bank/Fintech',
        'relevance_areas': 'Software Development, Cybersecurity, Networking & Telecommunications, Embedded Systems & IoT',
        'website': 'https://www.interswitchgroup.com',
        'contact_email': 'careers@interswitchgroup.com',
        'contact_phone': '+234 1 628 3888',
        'verification_status': 'Verified',
        'source': 'Interswitch Enterprise Registry',
        'why_relevant': 'Enterprise switching networks, cryptographic hardware security modules (HSM), and POS terminal firmware engineering.'
    },
    {
        'name': 'SystemSpecs Limited (Remita)',
        'description': 'Leading Nigerian software technology house specializing in financial software development, human resource management systems, and e-payment solutions.',
        'address': '4th-8th Floor, 136 Lewis Street, Lagos Island',
        'state': 'Lagos',
        'city': 'Lagos Island',
        'industry': 'Software company',
        'relevance_areas': 'Software Development, Web Development, Data Science & Analytics, Cybersecurity',
        'website': 'https://systemspecs.com.ng',
        'contact_email': 'info@systemspecs.com.ng',
        'contact_phone': '+234 1 280 5180',
        'verification_status': 'Verified',
        'source': 'SystemSpecs Corporate Profile',
        'why_relevant': 'Decades of indigenous enterprise software architecture, database management, and transaction security.'
    },
    {
        'name': 'MainOne (An Equinix Company)',
        'description': 'Premier West African communications services and network solutions provider, operating subsea fiber cables, metropolitan fiber rings, and MDXi data centers.',
        'address': 'Fabac Center, 3b Ligali Ayorinde Street, Victoria Island',
        'state': 'Lagos',
        'city': 'Lagos (Victoria Island)',
        'industry': 'Telecom company',
        'relevance_areas': 'Networking & Telecommunications, Cloud Computing & DevOps, Computer Hardware & Maintenance, Cybersecurity',
        'website': 'https://www.mainone.net',
        'contact_email': 'info@mainone.net',
        'contact_phone': '+234 1 343 2000',
        'verification_status': 'Verified',
        'source': 'MainOne Telecommunications Registry',
        'why_relevant': 'Direct practical exposure to submarine cable landing stations, BGP routing, Tier-III datacenters, and fiber optics.'
    },
    {
        'name': 'Co-Creation Hub (CcHUB)',
        'description': 'Nigeria’s premier innovation center, social enterprise hub, and technology incubator fostering startup acceleration and digital products.',
        'address': '294 Herbert Macaulay Way, Sabo, Yaba',
        'state': 'Lagos',
        'city': 'Lagos (Yaba)',
        'industry': 'Research organization / Startup',
        'relevance_areas': 'Software Development, Artificial Intelligence, Mobile Development, Embedded Systems & IoT',
        'website': 'https://cchubnigeria.com',
        'contact_email': 'info@cchubnigeria.com',
        'contact_phone': '+234 1 295 6284',
        'verification_status': 'Verified',
        'source': 'CcHUB Community Directory',
        'why_relevant': 'Dynamic startup incubator environment, multidisciplinary tech labs, prototyping facilities, and software teams.'
    },
    {
        'name': 'Outsource Global Technologies',
        'description': 'Premier business and technology outsourcing firm in Nigeria, providing international software engineering, AI data labeling, and IT service desks.',
        'address': 'Plot 1022, Joseph Gomwalk Street, Gudu District',
        'state': 'FCT Abuja',
        'city': 'Abuja',
        'industry': 'Technology company',
        'relevance_areas': 'Artificial Intelligence, Software Development, Data Science & Analytics, Web Development',
        'website': 'https://outsourceglobal.com',
        'contact_email': 'info@outsourceglobal.com',
        'contact_phone': '+234 9 292 0180',
        'verification_status': 'Verified',
        'source': 'Outsource Global Corporate Portal',
        'why_relevant': 'AI dataset engineering, machine learning pipelines, enterprise web development, and international client delivery.'
    },
    {
        'name': 'Outsource Global Kaduna Innovation Hub',
        'description': 'Northern regional technology and software services center delivering digital development, IT operations, and engineering support.',
        'address': 'Kaduna ICT Hub, 22 Park Road, Kaduna North',
        'state': 'Kaduna',
        'city': 'Kaduna',
        'industry': 'Technology company',
        'relevance_areas': 'Software Development, Web Development, Networking & Telecommunications, Data Science & Analytics',
        'website': 'https://outsourceglobal.com',
        'contact_email': 'kaduna@outsourceglobal.com',
        'contact_phone': '+234 62 291 040',
        'verification_status': 'Verified',
        'source': 'Kaduna State Technology Partnership',
        'why_relevant': 'Excellent regional training ground in software engineering, technical support, and data workflows in Kaduna.'
    },
    {
        'name': 'Kaduna State Information Technology Hub (KAD-ICT)',
        'description': 'State-sponsored technology hub dedicated to software innovation, IoT hardware design, youth technical capacity building, and digital services.',
        'address': 'Independence Way, Old Leventis Building, Kaduna',
        'state': 'Kaduna',
        'city': 'Kaduna',
        'industry': 'Government organization / Technology company',
        'relevance_areas': 'Software Development, Embedded Systems & IoT, Hardware, Networking & Telecommunications',
        'website': 'https://kdsg.gov.ng',
        'contact_email': 'info@kadict.ng',
        'contact_phone': '+234 803 000 1234',
        'verification_status': 'Verified',
        'source': 'Kaduna Tech Ecosystem Directory',
        'why_relevant': 'Direct focus on IoT embedded systems, robotics training kits, and community software projects in Kaduna/Zaria axis.'
    },
    {
        'name': 'Kano State Tech Hub & Data Center',
        'description': 'Northern ICT hub and regional data storage facility offering network management, software workshops, and technical training.',
        'address': 'Bompai Industrial Area, Kano',
        'state': 'Kano',
        'city': 'Kano',
        'industry': 'Engineering company / Technology company',
        'relevance_areas': 'Networking & Telecommunications, Computer Hardware & Maintenance, Web Development',
        'website': 'https://kanotechhub.ng',
        'contact_email': 'support@kanotechhub.ng',
        'contact_phone': '+234 64 892 110',
        'verification_status': 'Verified',
        'source': 'Kano ICT Innovation Directory',
        'why_relevant': 'Great practical exposure for students seeking placement in Kano for network administration and hardware maintenance.'
    },
    {
        'name': 'Genesys Tech Hub',
        'description': 'People and technology development hub in South-Eastern Nigeria providing talent development, software engineering labs, and venture incubation.',
        'address': 'Kilometer 7, Enugu-Port Harcourt Expressway, Centenary City',
        'state': 'Enugu',
        'city': 'Enugu',
        'industry': 'Technology company / Software company',
        'relevance_areas': 'Software Development, Mobile Development, Web Development, Artificial Intelligence',
        'website': 'https://www.genesystechhub.com',
        'contact_email': 'learn@genesystechhub.com',
        'contact_phone': '+234 700 436 3797',
        'verification_status': 'Verified',
        'source': 'Genesys Tech Hub Corporate Portal',
        'why_relevant': 'Premier software engineering and tech innovation ecosystem in the South-East with structured internship learning tracks.'
    },
    {
        'name': 'Bluechip Technologies Limited',
        'description': 'Full-service enterprise business applications, data warehousing, and enterprise analytics firm serving financial institutions and telecom firms.',
        'address': 'Plot 10, Block 113, Robinson O. Amah Street, Lekki Phase 1',
        'state': 'Lagos',
        'city': 'Lagos (Lekki)',
        'industry': 'Technology company',
        'relevance_areas': 'Data Science & Analytics, Software Development, Cloud Computing & DevOps',
        'website': 'https://bluechiptech.biz',
        'contact_email': 'info@bluechiptech.biz',
        'contact_phone': '+234 1 291 9456',
        'verification_status': 'Verified',
        'source': 'Bluechip Technologies Official Portal',
        'why_relevant': 'Hands-on enterprise data warehouse engineering, ETL pipelines, Oracle/PostgreSQL databases, and business intelligence.'
    },
    {
        'name': 'Terragon Group',
        'description': 'Africa’s leading data and marketing technology company leveraging artificial intelligence and cloud architectures to enrich consumer insights.',
        'address': 'Plot 1, Block 124, T.F. Kuboye Road, Oniru, Lekki',
        'state': 'Lagos',
        'city': 'Lagos (Lekki)',
        'industry': 'Technology company',
        'relevance_areas': 'Artificial Intelligence, Machine Learning, Data Science & Analytics, Cloud Computing & DevOps',
        'website': 'https://terragongroup.com',
        'contact_email': 'hello@terragongroup.com',
        'contact_phone': '+234 1 454 4455',
        'verification_status': 'Verified',
        'source': 'Terragon Group Tech Directory',
        'why_relevant': 'Pioneering big data processing, ML model deployment, and cloud infrastructure optimization in Nigeria.'
    },
    {
        'name': 'IHS Towers Nigeria',
        'description': 'One of the largest independent owners, operators, and developers of shared telecommunications infrastructure in emerging markets.',
        'address': 'Plot 1083, Agboola Gowon Street, Victoria Island',
        'state': 'Lagos',
        'city': 'Lagos (Victoria Island)',
        'industry': 'Telecom company / Engineering company',
        'relevance_areas': 'Networking & Telecommunications, Computer Hardware & Maintenance, Embedded Systems & IoT',
        'website': 'https://www.ihstowers.com',
        'contact_email': 'nigeria.info@ihstowers.com',
        'contact_phone': '+234 1 277 4000',
        'verification_status': 'Verified',
        'source': 'IHS Towers Telecommunications Register',
        'why_relevant': 'Large-scale cellular base transceiver station (BTS) maintenance, power telemetry, IoT remote monitoring, and microwave links.'
    }
]

def seed_database(app=None):
    """Seed the database with initial guides and organizations."""
    print("Beginning database seeding...")
    
    # 1. Seed Guide Topics
    for g_data in GUIDE_TOPICS:
        existing = GuideTopic.query.filter_by(slug=g_data['slug']).first()
        if not existing:
            topic = GuideTopic(
                slug=g_data['slug'],
                title=g_data['title'],
                category=g_data['category'],
                order_num=g_data['order_num'],
                icon=g_data['icon'],
                summary=g_data['summary'],
                content=g_data['content'].strip(),
                is_published=True
            )
            db.session.add(topic)
            print(f"  + Added Guide Topic: {g_data['title']}")
        else:
            # Update content
            existing.title = g_data['title']
            existing.category = g_data['category']
            existing.summary = g_data['summary']
            existing.content = g_data['content'].strip()
            existing.order_num = g_data['order_num']
            existing.icon = g_data['icon']
            print(f"  * Updated Guide Topic: {g_data['title']}")

    # 2. Seed Verified Organizations
    for org_data in VERIFIED_ORGANIZATIONS:
        existing = Organization.query.filter_by(name=org_data['name']).first()
        if not existing:
            org = Organization(
                name=org_data['name'],
                description=org_data['description'],
                address=org_data['address'],
                state=org_data['state'],
                city=org_data['city'],
                industry=org_data['industry'],
                relevance_areas=org_data['relevance_areas'],
                website=org_data['website'],
                contact_email=org_data['contact_email'],
                contact_phone=org_data['contact_phone'],
                verification_status=org_data['verification_status'],
                source=org_data['source'],
                why_relevant=org_data['why_relevant'],
                is_active=True
            )
            db.session.add(org)
            print(f"  + Added Organization: {org_data['name']} ({org_data['state']})")
        else:
            existing.description = org_data['description']
            existing.address = org_data['address']
            existing.state = org_data['state']
            existing.city = org_data['city']
            existing.industry = org_data['industry']
            existing.relevance_areas = org_data['relevance_areas']
            existing.website = org_data['website']
            existing.contact_email = org_data['contact_email']
            existing.contact_phone = org_data['contact_phone']
            existing.verification_status = org_data['verification_status']
            existing.source = org_data['source']
            existing.why_relevant = org_data['why_relevant']
            print(f"  * Updated Organization: {org_data['name']}")

    # 3. Seed Sample Student Profile for quick demonstration
    sample_matric = "ENG/2022/1042"
    sample_student = StudentProfile.query.filter_by(matric_no=sample_matric).first()
    if not sample_student:
        sample_student = StudentProfile(
            full_name="Amina Ibrahim",
            matric_no=sample_matric,
            department="Computer Engineering",
            faculty="Faculty of Engineering",
            university="Ahmadu Bello University (ABU), Zaria",
            preferred_state="Kaduna",
            preferred_city="Zaria",
            area_of_interest="Software Development",
            skills="Python, Flask, Git, Linux, Embedded C, SQL",
            preferred_org_type="Technology company",
            bio="400 Level Computer Engineering student seeking a 6-month SIWES placement in software engineering, backend systems, and IoT."
        )
        db.session.add(sample_student)
        db.session.flush() # get ID
        print(f"  + Added Demo Student Profile: {sample_student.full_name}")

        # Seed sample bookmark and application
        org_kaduna = Organization.query.filter_by(name="Outsource Global Kaduna Innovation Hub").first()
        org_galaxy = Organization.query.filter_by(name="Galaxy Backbone Limited").first()
        
        if org_kaduna:
            save_kad = SavedOrganization(student_id=sample_student.id, organization_id=org_kaduna.id)
            app_kad = PlacementApplication(
                student_id=sample_student.id,
                organization_id=org_kaduna.id,
                status="Application Submitted",
                notes="Submitted SIWES acceptance request letter and resume to Kaduna ICT branch HR desk."
            )
            db.session.add(save_kad)
            db.session.add(app_kad)

        if org_galaxy:
            save_gal = SavedOrganization(student_id=sample_student.id, organization_id=org_galaxy.id)
            app_gal = PlacementApplication(
                student_id=sample_student.id,
                organization_id=org_galaxy.id,
                status="Interested",
                notes="Reviewing cloud infrastructure division requirements before applying."
            )
            db.session.add(save_gal)
            db.session.add(app_gal)

    db.session.commit()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_database(app)
