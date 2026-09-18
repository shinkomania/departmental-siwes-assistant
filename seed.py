"""
Database Seeding Script
-----------------------
Seeds programme-neutral SIWES guidance, access-control defaults, starter
organization records, and demonstration data.

Organization records in this seed are NOT DSA certifications and do not imply
that an organization is currently accepting SIWES students. Provenance,
internal review state, listing state, and current intake are separate facts.

Run via:
    python seed.py
or:
    flask seed-db

Database schema creation is owned by Alembic/Flask-Migrate.
"""
from models.db import db
from models.guide import GuideTopic
from models.organization import Organization
from models.student import StudentProfile
from models.application import SavedOrganization, PlacementApplication
import os
from datetime import datetime

from models.access import Role, Permission, UserRoleAssignment
from models.user import User
from models.academic import (
    Institution,
    AcademicUnit,
    Department,
    Programme,
    SIWESConfiguration,
)

GUIDE_TOPICS = [
    {
        'slug': 'what-is-siwes', 'title': 'What is SIWES?', 'category': 'Overview',
        'order_num': 1, 'icon': 'info-circle',
        'summary': 'Understand SIWES and how it connects academic learning with supervised workplace experience.',
        'content': """
The **Students Industrial Work Experience Scheme (SIWES)** is a skills-training programme that gives eligible students practical exposure to work situations related to their courses of study.

SIWES is coordinated within Nigeria's national industrial-training framework involving the Industrial Training Fund (ITF), participating institutions, employers and relevant supervisory agencies.

**Important:** SIWES eligibility, duration, semester, documentation and assessment can differ by institution and programme. DSA's general guidance does not override verified instructions from your institution, department or programme.
"""
    },
    {
        'slug': 'purpose-of-siwes', 'title': 'Purpose of SIWES', 'category': 'Overview',
        'order_num': 2, 'icon': 'target',
        'summary': 'Why supervised industrial experience is an important part of eligible programmes.',
        'content': """
SIWES is intended to help students connect academic knowledge with practical workplace experience.

#### Core objectives
1. **Practical skills:** Develop relevant industrial and professional skills.
2. **Workplace exposure:** Experience methods, equipment, systems and practices that may not be available in school.
3. **Work readiness:** Prepare for the realities, responsibilities and discipline of employment.
4. **Knowledge application:** Apply concepts learned in school to real tasks and problems.
5. **Employer participation:** Strengthen employer involvement in preparing students for work.

The exact activities that count as relevant experience depend on the student's programme and approved placement.
"""
    },
    {
        'slug': 'how-to-prepare-for-siwes', 'title': 'How to Prepare for SIWES', 'category': 'Preparation',
        'order_num': 3, 'icon': 'clipboard-check',
        'summary': 'Prepare your documents, placement information, expectations and practical readiness.',
        'content': """
Start with the **official instructions for your institution and programme**.

#### Before commencement
- Attend required SIWES orientation or briefings.
- Obtain the documents and placement letters required by your institution.
- Confirm the approved attachment period and reporting procedure.
- Record your placement details accurately on required SIWES documentation.
- Understand workplace rules, safety requirements, confidentiality and expected conduct.
- Review practical knowledge relevant to your own programme and intended placement.

ITF documentation includes the **Students Commencement of Attachment Form (SCAF)** and **Form 8 (End-of-Programme Report Sheet)** within the national SIWES process. Your institution should tell you which forms you must complete, when they are due and where they should be submitted.
"""
    },
    {
        'slug': 'choosing-a-suitable-organization', 'title': 'Choosing a Suitable Organization', 'category': 'Preparation',
        'order_num': 4, 'icon': 'building',
        'summary': 'Evaluate a placement based on programme relevance, supervision, learning opportunities and approved requirements.',
        'content': """
A useful SIWES placement should provide experience that is relevant to your **programme or approved field of training**.

Consider:
1. **Programme relevance:** Are the organization's activities connected to skills your programme expects you to develop?
2. **Supervision:** Is there a suitable workplace supervisor?
3. **Practical exposure:** Will you participate in meaningful work rather than unrelated errands?
4. **Safety and professionalism:** Does the workplace provide an appropriate environment for training?
5. **Institution approval:** Does the placement satisfy your institution or department's requirements?

A directory listing alone does not prove that an organization is currently accepting SIWES students. Confirm current intake directly and follow your institution's placement-approval process.
"""
    },
    {
        'slug': 'siwes-logbook', 'title': 'SIWES Logbook Guidelines', 'category': 'Logbook',
        'order_num': 5, 'icon': 'book',
        'summary': 'Keep accurate records of your training activities and obtain required supervision or endorsements.',
        'content': """
Your SIWES logbook is an important record of the training you actually performed.

- Record activities regularly and accurately.
- Describe the task, process, tool, equipment, method or lesson in terms appropriate to your field.
- Add sketches, diagrams, tables or other supporting material where useful and permitted.
- Obtain workplace-supervisor review/signatures at the intervals required by your institution.
- Never invent activities or copy another student's entries.

Follow your institution's logbook format whenever it differs from this general guidance.
"""
    },
    {
        'slug': 'weekly-activities', 'title': 'Weekly Activities & Documentation', 'category': 'Logbook',
        'order_num': 6, 'icon': 'calendar',
        'summary': 'Turn daily activities into clear weekly records of tasks, challenges and learning.',
        'content': """
A weekly summary should show what you actually learned and contributed.

Useful elements include:
- the week's main activities or objectives;
- tools, equipment, methods or systems used;
- challenges encountered;
- how problems were handled;
- new skills or knowledge gained; and
- relevant safety or professional lessons.

The terminology should match your discipline. A laboratory, farm, workshop, hospital-related unit, construction site, office, studio or software team will naturally produce different kinds of entries.
"""
    },
    {
        'slug': 'siwes-report', 'title': 'SIWES Report Writing', 'category': 'Report',
        'order_num': 7, 'icon': 'file-text',
        'summary': 'Prepare an evidence-based report using the format required by your institution and programme.',
        'content': """
Your final SIWES report should document your placement, activities, learning and relevant experience clearly.

There is **no single DSA report structure that overrides every institution or programme**. Use the report template, chapter arrangement, formatting rules and submission requirements issued by your institution, faculty, department or programme.

In general, a report may cover the host organization, work performed, skills and knowledge gained, challenges, observations, conclusions and recommendations. Include references, figures, appendices or other evidence where required and permitted.

Respect employer confidentiality and never include protected information without authorization.
"""
    },
    {
        'slug': 'supervisor-visits', 'title': 'SIWES Supervision', 'category': 'Supervision',
        'order_num': 8, 'icon': 'user-check',
        'summary': 'Understand institutional, workplace and ITF supervision during industrial attachment.',
        'content': """
SIWES involves supervision by the participating institution, the employer and the national SIWES framework.

During supervision, students may be expected to demonstrate attendance, explain their activities, present an up-to-date logbook and discuss progress with supervisors.

ITF operational guidance assigns supervision responsibilities to participating bodies and provides for visits during attachment. Your actual supervision schedule and assessment process should follow the verified instructions for your institution and programme.

Keep your placement details current so authorized supervisors can locate and contact you when necessary.
"""
    },
    {
        'slug': 'common-siwes-challenges', 'title': 'Common SIWES Challenges & Responses', 'category': 'Challenges',
        'order_num': 9, 'icon': 'alert-triangle',
        'summary': 'Practical ways to respond to common placement and training difficulties.',
        'content': """
Common challenges include difficulty finding a placement, limited meaningful tasks, transport costs, unfamiliar work methods, documentation problems and communication gaps.

Useful responses include:
- contact your departmental/institutional SIWES coordinator when official guidance is needed;
- ask your workplace supervisor for relevant learning tasks;
- keep accurate records of applications and placement communication;
- learn unfamiliar tools through appropriate documentation and supervised practice;
- plan transport and accommodation realistically; and
- report serious safety, misconduct or placement problems through the appropriate institutional channel.

Do not falsify placement, attendance, logbook entries or acceptance evidence to solve a placement problem.
"""
    },
    {
        'slug': 'general-tips-for-success', 'title': 'General Tips for a Successful SIWES', 'category': 'Tips',
        'order_num': 10, 'icon': 'award',
        'summary': 'Build useful skills, professional habits and reliable evidence throughout your placement.',
        'content': """
Treat SIWES as structured workplace learning.

- Be punctual, responsible and willing to learn.
- Ask thoughtful questions and seek appropriate feedback.
- Keep your logbook and required documents current.
- Build professional relationships without violating workplace boundaries.
- Protect confidential information and follow safety rules.
- Keep evidence of your work only where the organization permits it.
- Prepare reports, presentations or assessments according to your programme's verified requirements.

DSA should help you organize the process, but official institutional and SIWES instructions remain authoritative.
"""
    },
]

PERMISSIONS = [
    ('View Institution Dashboard', 'view_institution_dashboard'),
    ('Manage Coordinators', 'manage_coordinators'),
    ('Manage Institution Settings', 'manage_institution_settings'),
    ('View Verification Statistics', 'view_verification_statistics'),
    ('Review Escalated Cases', 'review_escalated_cases'),
    ('Verify Student Placement', 'verify_student_placement'),
    ('View Department Students', 'view_department_students'),
    ('Review Placement Evidence', 'review_placement_evidence'),
    ('Publish Department Notice', 'publish_department_notice'),
    ('Publish Institution Notice', 'publish_institution_notice'),

    # Platform administration
    (
        'Access Platform Administration Panel',
        'access_platform_admin_panel',
    ),

    # Administrative role-application review permissions
    (
        'Review Institution Administrator Applications',
        'review_institution_admin_applications',
    ),
    (
        'Review Institution SIWES Officer Applications',
        'review_institution_siwes_officer_applications',
    ),
    (
        'Review Coordinator Applications',
        'review_coordinator_applications',
    ),
    (
        'Manage Platform Verification Queue',
        'manage_platform_verification_queue',
    ),
]


ROLE_DEFINITIONS = {
    'platform_administrator': {
        'name': 'Platform Administrator',
        'description': 'Global DSA platform administration role.',
        'permissions': [
            'access_platform_admin_panel',
            'review_institution_admin_applications',
            'review_institution_siwes_officer_applications',
            'review_coordinator_applications',
            'manage_platform_verification_queue',
        ],
    },

    'primary_institution_administrator': {
        'name': 'Primary Institution Administrator',
        'description': (
            'Manages an approved institution within assigned scope.'
        ),
        'permissions': [
            'view_institution_dashboard',
            'manage_coordinators',
            'manage_institution_settings',
            'view_verification_statistics',
            'publish_institution_notice',
            'review_coordinator_applications',
        ],
    },

    'institution_siwes_officer': {
        'name': 'Institution SIWES Officer',
        'description': (
            'Handles authorized institution-level SIWES operations.'
        ),
        'permissions': [
            'view_institution_dashboard',
            'view_verification_statistics',
            'review_escalated_cases',
            'verify_student_placement',
            'review_placement_evidence',
            'publish_institution_notice',
        ],
    },

    'departmental_siwes_coordinator': {
        'name': 'Departmental SIWES Coordinator',
        'description': (
            'Coordinates SIWES only within assigned '
            'department/programme scope.'
        ),
        'permissions': [
            'verify_student_placement',
            'view_department_students',
            'review_placement_evidence',
            'publish_department_notice',
        ],
    },

    'student': {
        'name': 'Student',
        'description': (
            'Compatibility role for student-facing access; '
            'StudentProfile remains separate.'
        ),
        'permissions': [],
    },
}

def seed_access_control():
    """Create/update the initial role and permission catalogue idempotently."""
    permission_by_slug = {}
    for name, slug in PERMISSIONS:
        permission = Permission.query.filter_by(slug=slug).first()
        if not permission:
            permission = Permission(name=name, slug=slug)
            db.session.add(permission)
            db.session.flush()
        else:
            permission.name = name
        permission_by_slug[slug] = permission

    for slug, definition in ROLE_DEFINITIONS.items():
        role = Role.query.filter_by(slug=slug).first()
        if not role:
            role = Role(
                name=definition['name'],
                slug=slug,
                description=definition['description'],
                is_active=True,
            )
            db.session.add(role)
            db.session.flush()
        else:
            role.name = definition['name']
            role.description = definition['description']
            role.is_active = True

        role.permissions = [
            permission_by_slug[p]
            for p in definition['permissions']
        ]

def bootstrap_platform_administrator():
    """
    Optionally provision the first Platform Administrator.

    This bootstrap runs only when BOTH environment variables are present:

        PLATFORM_ADMIN_EMAIL
        PLATFORM_ADMIN_PASSWORD

    No administrator password is stored in source control.

    Existing suspended/revoked accounts or assignments are NOT silently
    reactivated by the seed process.
    """
    admin_email = os.getenv(
        "PLATFORM_ADMIN_EMAIL",
        "",
    ).strip().lower()

    admin_password = os.getenv(
        "PLATFORM_ADMIN_PASSWORD",
        "",
    )

    admin_name = os.getenv(
        "PLATFORM_ADMIN_NAME",
        "DSA Platform Administrator",
    ).strip()

    # Bootstrap is intentionally optional.
    if not admin_email and not admin_password:
        print(
            "  - Platform Administrator bootstrap skipped "
            "(credentials not configured)."
        )
        return

    if not admin_email or not admin_password:
        raise RuntimeError(
            "Both PLATFORM_ADMIN_EMAIL and "
            "PLATFORM_ADMIN_PASSWORD must be configured together."
        )

    if len(admin_password) < 12:
        raise RuntimeError(
            "PLATFORM_ADMIN_PASSWORD must contain at least 12 characters."
        )

    role = Role.query.filter_by(
        slug="platform_administrator"
    ).first()

    if not role:
        raise RuntimeError(
            "Platform Administrator role does not exist. "
            "Run seed_access_control() before bootstrapping the administrator."
        )

    if not role.is_active:
        raise RuntimeError(
            "Platform Administrator role is inactive."
        )

    user = User.query.filter_by(
        email=admin_email
    ).first()

    if not user:
        user = User(
            full_name=admin_name,
            email=admin_email,
            account_status="Active",
            email_verified=True,
        )
        user.set_password(admin_password)

        db.session.add(user)
        db.session.flush()

        print(
            f"  + Created Platform Administrator account: {admin_email}"
        )

    else:
        if user.account_status != "Active":
            raise RuntimeError(
                "The configured Platform Administrator account exists "
                "but is not Active. The seed process will not reactivate it."
            )

        print(
            f"  * Platform Administrator account already exists: "
            f"{admin_email}"
        )

    assignment = UserRoleAssignment.query.filter_by(
        user_id=user.id,
        role_id=role.id,
        institution_id=None,
        department_id=None,
        programme_id=None,
    ).first()

    if assignment:
        if assignment.status != "Approved":
            raise RuntimeError(
                "A global Platform Administrator assignment already exists "
                f"for {admin_email}, but its status is "
                f"'{assignment.status}'. The seed process will not "
                "silently reactivate or approve it."
            )

        print(
            "  * Global Platform Administrator role assignment "
            "already exists."
        )
        return

    assignment = UserRoleAssignment(
        user_id=user.id,
        role_id=role.id,
        institution_id=None,
        department_id=None,
        programme_id=None,
        status="Approved",
        approved_at=datetime.utcnow(),
    )

    db.session.add(assignment)

    print(
        "  + Granted global Platform Administrator role."
    )

STARTER_ORGANIZATIONS = [
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
        'source': 'Federal Government Enterprise Directory',
        'source_type': 'Other',
        'source_name': 'Federal Government Enterprise Directory',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Official NITDA Agency Portal',
        'source_type': 'Other',
        'source_name': 'Official NITDA Agency Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Paystack Careers & Engineering Portal',
        'source_type': 'Other',
        'source_name': 'Paystack Careers & Engineering Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Flutterwave Official Portal',
        'source_type': 'Other',
        'source_name': 'Flutterwave Official Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Interswitch Enterprise Registry',
        'source_type': 'Other',
        'source_name': 'Interswitch Enterprise Registry',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'SystemSpecs Corporate Profile',
        'source_type': 'Other',
        'source_name': 'SystemSpecs Corporate Profile',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'MainOne Telecommunications Registry',
        'source_type': 'Other',
        'source_name': 'MainOne Telecommunications Registry',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
        'why_relevant': 'Direct practical exposure to submarine cable landing stations, BGP routing, Tier-III datacenters, and fiber optics.'
    },
    {
        'name': 'Co-Creation Hub (CcHUB)',
        "description": "Nigeria's premier innovation center, social enterprise hub, and technology incubator fostering startup acceleration and digital products.",
        'address': '294 Herbert Macaulay Way, Sabo, Yaba',
        'state': 'Lagos',
        'city': 'Lagos (Yaba)',
        'industry': 'Research organization / Startup',
        'relevance_areas': 'Software Development, Artificial Intelligence, Mobile Development, Embedded Systems & IoT',
        'website': 'https://cchubnigeria.com',
        'contact_email': 'info@cchubnigeria.com',
        'contact_phone': '+234 1 295 6284',
        'source': 'CcHUB Community Directory',
        'source_type': 'Other',
        'source_name': 'CcHUB Community Directory',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Outsource Global Corporate Portal',
        'source_type': 'Other',
        'source_name': 'Outsource Global Corporate Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Kaduna State Technology Partnership',
        'source_type': 'Other',
        'source_name': 'Kaduna State Technology Partnership',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Kaduna Tech Ecosystem Directory',
        'source_type': 'Other',
        'source_name': 'Kaduna Tech Ecosystem Directory',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Kano ICT Innovation Directory',
        'source_type': 'Other',
        'source_name': 'Kano ICT Innovation Directory',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Genesys Tech Hub Corporate Portal',
        'source_type': 'Other',
        'source_name': 'Genesys Tech Hub Corporate Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'Bluechip Technologies Official Portal',
        'source_type': 'Other',
        'source_name': 'Bluechip Technologies Official Portal',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
        'why_relevant': 'Hands-on enterprise data warehouse engineering, ETL pipelines, Oracle/PostgreSQL databases, and business intelligence.'
    },
    {
        'name': 'Terragon Group',
        "description": "Africa's leading data and marketing technology company leveraging artificial intelligence and cloud architectures to enrich consumer insights.",
        'address': 'Plot 1, Block 124, T.F. Kuboye Road, Oniru, Lekki',
        'state': 'Lagos',
        'city': 'Lagos (Lekki)',
        'industry': 'Technology company',
        'relevance_areas': 'Artificial Intelligence, Machine Learning, Data Science & Analytics, Cloud Computing & DevOps',
        'website': 'https://terragongroup.com',
        'contact_email': 'hello@terragongroup.com',
        'contact_phone': '+234 1 454 4455',
        'source': 'Terragon Group Tech Directory',
        'source_type': 'Other',
        'source_name': 'Terragon Group Tech Directory',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
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
        'source': 'IHS Towers Telecommunications Register',
        'source_type': 'Other',
        'source_name': 'IHS Towers Telecommunications Register',
        'review_status': 'Pending',
        'listing_status': 'Unknown',
        'acceptance_status': 'Unknown',
        'why_relevant': 'Large-scale cellular base transceiver station (BTS) maintenance, power telemetry, IoT remote monitoring, and microwave links.'
    }
]

def seed_academic_directory():
    """
    Seed the first controlled DSA academic-directory pilot.

    Pilot hierarchy:
        Ahmadu Bello University
        -> Faculty of Engineering
        -> Computer Engineering
        -> B.Eng. Computer Engineering

    Programme identity is stored separately from its SIWES configuration.
    Exact SIWES timing and requirements remain Pending Verification until
    supported by sufficiently specific evidence.
    """
    print("Seeding pilot academic directory...")

    institution = Institution.query.filter_by(
        name="Ahmadu Bello University"
    ).first()

    if not institution:
        institution = Institution(
            name="Ahmadu Bello University",
            institution_type="University",
            city="Zaria",
            state="Kaduna",
            official_website="https://abu.edu.ng/",
            directory_status="Verified",
            administration_status="Unclaimed",
            verification_source=(
                "Official Ahmadu Bello University website and "
                "Faculty of Engineering website."
            ),
            last_verified=datetime.utcnow(),
            is_active=True,
        )
        db.session.add(institution)
        db.session.flush()
    else:
        institution.institution_type = "University"
        institution.city = "Zaria"
        institution.state = "Kaduna"
        institution.official_website = "https://abu.edu.ng/"
        institution.directory_status = "Verified"
        institution.administration_status = (
            institution.administration_status or "Unclaimed"
        )
        institution.is_active = True

    academic_unit = AcademicUnit.query.filter_by(
        institution_id=institution.id,
        name="Faculty of Engineering",
    ).first()

    if not academic_unit:
        academic_unit = AcademicUnit(
            institution_id=institution.id,
            name="Faculty of Engineering",
            unit_type="Faculty",
            is_active=True,
        )
        db.session.add(academic_unit)
        db.session.flush()
    else:
        academic_unit.unit_type = "Faculty"
        academic_unit.is_active = True

    department = Department.query.filter_by(
        academic_unit_id=academic_unit.id,
        name="Computer Engineering",
    ).first()

    if not department:
        department = Department(
            academic_unit_id=academic_unit.id,
            name="Computer Engineering",
            is_active=True,
        )
        db.session.add(department)
        db.session.flush()
    else:
        department.is_active = True

    programme = Programme.query.filter_by(
        department_id=department.id,
        name="Computer Engineering",
    ).first()

    if not programme:
        programme = Programme(
            department_id=department.id,
            name="Computer Engineering",
            award="B.Eng.",
            duration_years=5,
            is_active=True,
        )
        db.session.add(programme)
        db.session.flush()
    else:
        programme.award = "B.Eng."
        programme.duration_years = 5
        programme.is_active = True

    siwes_config = SIWESConfiguration.query.filter_by(
        programme_id=programme.id
    ).first()

    if not siwes_config:
        siwes_config = SIWESConfiguration(
            programme_id=programme.id,
            siwes_status="Pending Verification",
            verification_source=(
                "Official ABU Department of Computer Engineering "
                "information confirms SIWES within the Faculty; "
                "current programme-specific SIWES configuration "
                "requires further verification."
            ),
            verification_reference=(
                "https://engineering.abu.edu.ng/"
                "department/compeng/public/"
            ),
        )
        db.session.add(siwes_config)

    print(
        "  Pilot academic hierarchy ready: "
        "Ahmadu Bello University -> Faculty of Engineering -> "
        "Computer Engineering -> B.Eng. Computer Engineering"
    )

def seed_database(app=None):
    """Seed programme-neutral guides, access-control defaults, starter organizations, and demo data."""
    print("Beginning database seeding...")

    # 0. Seed access-control catalogue
    seed_access_control()

    # 0a. Seed controlled academic-directory pilot
    seed_academic_directory()

    # 0b. Optionally bootstrap the first Platform Administrator
    bootstrap_platform_administrator()


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

    # 2. Seed starter organizations (provenance-aware; no intake guarantee)
    for org_data in STARTER_ORGANIZATIONS:
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
                verification_status='Online Source',
                source=org_data['source'],
                why_relevant=org_data['why_relevant'],
                source_type=org_data.get('source_type', 'Other'),
                source_name=org_data.get('source_name'),
                source_url=org_data.get('source_url'),
                source_reference=org_data.get('source_reference'),
                review_status=org_data.get('review_status', 'Pending'),
                listing_status=org_data.get('listing_status', 'Unknown'),
                acceptance_status=org_data.get('acceptance_status', 'Unknown'),
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
            existing.verification_status = 'Online Source'
            existing.source = org_data['source']
            existing.why_relevant = org_data['why_relevant']
            existing.source_type = org_data.get('source_type', 'Other')
            existing.source_name = org_data.get('source_name')
            existing.source_url = org_data.get('source_url')
            existing.source_reference = org_data.get('source_reference')
            existing.review_status = org_data.get('review_status', 'Pending')
            existing.listing_status = org_data.get('listing_status', 'Unknown')
            existing.acceptance_status = org_data.get('acceptance_status', 'Unknown')
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
        seed_database(app)
