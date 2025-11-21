-- ============================================
-- SCHEMA: AUTH SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('STUDENT', 'ENTERPRISE', 'UNIVERSITY_ADMIN', 'UNIVERSITY_SUPERVISOR', 'SYSTEM_ADMIN')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expiry TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE auth.refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE TABLE auth.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE auth.permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE auth.role_permissions (
    role_id INTEGER REFERENCES auth.roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES auth.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_role ON auth.users(role);
CREATE INDEX idx_refresh_tokens_user ON auth.refresh_tokens(user_id);

-- ============================================
-- SCHEMA: STUDENT SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS students;

CREATE TABLE students.students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(20),
    nationality VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    region VARCHAR(100),
    profile_photo VARCHAR(500),
    bio TEXT,
    university_id UUID,
    department_id UUID,
    program VARCHAR(100),
    level VARCHAR(50),
    student_number VARCHAR(50) UNIQUE,
    gpa DECIMAL(3,2),
    expected_graduation DATE,
    linkedin_url VARCHAR(255),
    github_url VARCHAR(255),
    portfolio_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE students.skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50)
);

CREATE TABLE students.student_skills (
    student_id UUID REFERENCES students.students(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES students.skills(id) ON DELETE CASCADE,
    proficiency_level VARCHAR(50) CHECK (proficiency_level IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')),
    PRIMARY KEY (student_id, skill_id)
);

CREATE TABLE students.languages (
    id SERIAL PRIMARY KEY,
    student_id UUID REFERENCES students.students(id) ON DELETE CASCADE,
    language VARCHAR(50) NOT NULL,
    proficiency VARCHAR(50) CHECK (proficiency IN ('BASIC', 'CONVERSATIONAL', 'FLUENT', 'NATIVE'))
);

CREATE TABLE students.academic_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students.students(id) ON DELETE CASCADE,
    degree_type VARCHAR(100),
    field_of_study VARCHAR(200),
    institution VARCHAR(200),
    start_date DATE,
    end_date DATE,
    grade VARCHAR(50),
    description TEXT
);

CREATE INDEX idx_students_user ON students.students(user_id);
CREATE INDEX idx_students_university ON students.students(university_id);

-- ============================================
-- SCHEMA: ENTERPRISE SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS enterprises;

CREATE TABLE enterprises.enterprises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    legal_name VARCHAR(200),
    registration_number VARCHAR(100) UNIQUE,
    tax_id VARCHAR(100),
    industry VARCHAR(100),
    sector VARCHAR(100),
    company_size VARCHAR(50) CHECK (company_size IN ('1-10', '11-50', '51-200', '201-500', '500+')),
    founded_year INTEGER,
    website VARCHAR(255),
    logo VARCHAR(500),
    description TEXT,
    address TEXT,
    city VARCHAR(100),
    region VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Cameroun',
    postal_code VARCHAR(20),
    phone VARCHAR(20),
    is_verified BOOLEAN DEFAULT false,
    verification_date TIMESTAMP,
    verification_documents JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE enterprises.contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID REFERENCES enterprises.enterprises(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    position VARCHAR(100),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE enterprises.certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID REFERENCES enterprises.enterprises(id) ON DELETE CASCADE,
    certification_name VARCHAR(200),
    issuing_authority VARCHAR(200),
    issue_date DATE,
    expiry_date DATE,
    certificate_url VARCHAR(500)
);

CREATE INDEX idx_enterprises_user ON enterprises.enterprises(user_id);
CREATE INDEX idx_enterprises_verified ON enterprises.enterprises(is_verified);

-- ============================================
-- SCHEMA: UNIVERSITY SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS universities;

CREATE TABLE universities.universities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    acronym VARCHAR(20),
    type VARCHAR(50) CHECK (type IN ('PUBLIC', 'PRIVATE')),
    address TEXT,
    city VARCHAR(100),
    region VARCHAR(100),
    website VARCHAR(255),
    logo VARCHAR(500),
    email VARCHAR(255),
    phone VARCHAR(20),
    accreditation_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE universities.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id UUID REFERENCES universities.universities(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(20),
    description TEXT,
    head_of_department VARCHAR(200),
    email VARCHAR(255),
    phone VARCHAR(20)
);

CREATE TABLE universities.programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID REFERENCES universities.departments(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    degree_type VARCHAR(100),
    duration_months INTEGER,
    internship_required BOOLEAN DEFAULT true,
    minimum_internship_duration INTEGER
);

CREATE TABLE universities.supervisors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL,
    university_id UUID REFERENCES universities.universities(id) ON DELETE CASCADE,
    department_id UUID REFERENCES universities.departments(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    title VARCHAR(50),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    specialization TEXT,
    max_students INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE universities.conventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id UUID REFERENCES universities.universities(id) ON DELETE CASCADE,
    enterprise_id UUID,
    convention_number VARCHAR(100) UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'ACTIVE' CHECK (status IN ('DRAFT', 'ACTIVE', 'EXPIRED', 'TERMINATED')),
    document_url VARCHAR(500),
    signed_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_supervisors_university ON universities.supervisors(university_id);

-- ============================================
-- SCHEMA: OFFERS SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS offers;

CREATE TABLE offers.offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT,
    responsibilities TEXT,
    skills_required JSONB,
    duration_months INTEGER NOT NULL,
    start_date DATE,
    end_date DATE,
    application_deadline DATE,
    positions_available INTEGER DEFAULT 1,
    positions_filled INTEGER DEFAULT 0,
    location VARCHAR(200),
    city VARCHAR(100),
    region VARCHAR(100),
    is_remote BOOLEAN DEFAULT false,
    compensation_type VARCHAR(50) CHECK (compensation_type IN ('PAID', 'UNPAID', 'STIPEND')),
    compensation_amount DECIMAL(10,2),
    benefits TEXT,
    status VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED', 'CLOSED', 'CANCELLED')),
    views_count INTEGER DEFAULT 0,
    applications_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE offers.required_documents (
    id SERIAL PRIMARY KEY,
    offer_id UUID REFERENCES offers.offers(id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    is_required BOOLEAN DEFAULT true
);

CREATE TABLE offers.offer_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE offers.offer_category_mapping (
    offer_id UUID REFERENCES offers.offers(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES offers.offer_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (offer_id, category_id)
);

CREATE INDEX idx_offers_enterprise ON offers.offers(enterprise_id);
CREATE INDEX idx_offers_status ON offers.offers(status);
CREATE INDEX idx_offers_deadline ON offers.offers(application_deadline);

-- ============================================
-- SCHEMA: APPLICATIONS SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS applications;

CREATE TABLE applications.applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID NOT NULL,
    student_id UUID NOT NULL,
    cover_letter TEXT,
    cv_document_id UUID,
    status VARCHAR(50) DEFAULT 'SUBMITTED' CHECK (status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'SHORTLISTED', 'INTERVIEW_SCHEDULED', 'ACCEPTED', 'REJECTED', 'WITHDRAWN')),
    submitted_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    rejection_reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(offer_id, student_id)
);

CREATE TABLE applications.application_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications.applications(id) ON DELETE CASCADE,
    document_type VARCHAR(100),
    document_id UUID NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications.interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications.applications(id) ON DELETE CASCADE,
    scheduled_date TIMESTAMP NOT NULL,
    location VARCHAR(200),
    interview_type VARCHAR(50) CHECK (interview_type IN ('PHONE', 'VIDEO', 'IN_PERSON')),
    meeting_link VARCHAR(500),
    interviewer_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'SCHEDULED' CHECK (status IN ('SCHEDULED', 'COMPLETED', 'CANCELLED', 'RESCHEDULED')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications.evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications.applications(id) ON DELETE CASCADE,
    evaluator_id UUID NOT NULL,
    technical_score INTEGER CHECK (technical_score BETWEEN 1 AND 10),
    soft_skills_score INTEGER CHECK (soft_skills_score BETWEEN 1 AND 10),
    motivation_score INTEGER CHECK (motivation_score BETWEEN 1 AND 10),
    overall_score DECIMAL(3,2),
    comments TEXT,
    recommendation VARCHAR(50) CHECK (recommendation IN ('HIGHLY_RECOMMENDED', 'RECOMMENDED', 'MAYBE', 'NOT_RECOMMENDED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_applications_offer ON applications.applications(offer_id);
CREATE INDEX idx_applications_student ON applications.applications(student_id);
CREATE INDEX idx_applications_status ON applications.applications(status);

-- ============================================
-- SCHEMA: INTERNSHIPS SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS internships;

CREATE TABLE internships.internships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID UNIQUE NOT NULL,
    student_id UUID NOT NULL,
    enterprise_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    university_id UUID NOT NULL,
    supervisor_id UUID,
    company_supervisor_name VARCHAR(200),
    company_supervisor_email VARCHAR(255),
    company_supervisor_phone VARCHAR(20),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ONGOING', 'COMPLETED', 'TERMINATED', 'SUSPENDED')),
    termination_reason TEXT,
    convention_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE internships.attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID REFERENCES internships.internships(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in TIME,
    check_out TIME,
    status VARCHAR(50) CHECK (status IN ('PRESENT', 'ABSENT', 'LEAVE', 'HALF_DAY')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(internship_id, date)
);

CREATE TABLE internships.activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID REFERENCES internships.internships(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    hours_spent DECIMAL(4,2),
    skills_applied JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE internships.evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID REFERENCES internships.internships(id) ON DELETE CASCADE,
    evaluator_id UUID NOT NULL,
    evaluator_type VARCHAR(50) CHECK (evaluator_type IN ('COMPANY', 'UNIVERSITY')),
    evaluation_period VARCHAR(50),
    technical_skills_score INTEGER CHECK (technical_skills_score BETWEEN 1 AND 10),
    professional_attitude_score INTEGER CHECK (professional_attitude_score BETWEEN 1 AND 10),
    communication_score INTEGER CHECK (communication_score BETWEEN 1 AND 10),
    teamwork_score INTEGER CHECK (teamwork_score BETWEEN 1 AND 10),
    initiative_score INTEGER CHECK (initiative_score BETWEEN 1 AND 10),
    overall_score DECIMAL(3,2),
    strengths TEXT,
    areas_for_improvement TEXT,
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE internships.issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID REFERENCES internships.internships(id) ON DELETE CASCADE,
    reported_by UUID NOT NULL,
    issue_type VARCHAR(100),
    severity VARCHAR(50) CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')),
    resolution TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_internships_student ON internships.internships(student_id);
CREATE INDEX idx_internships_enterprise ON internships.internships(enterprise_id);
CREATE INDEX idx_internships_status ON internships.internships(status);

-- ============================================
-- SCHEMA: DOCUMENTS SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS documents;

CREATE TABLE documents.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    owner_type VARCHAR(50) NOT NULL CHECK (owner_type IN ('STUDENT', 'ENTERPRISE', 'UNIVERSITY', 'INTERNSHIP')),
    document_type VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    storage_path VARCHAR(500) NOT NULL,
    storage_bucket VARCHAR(100),
    version INTEGER DEFAULT 1,
    is_public BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'VALIDATED', 'REJECTED')),
    validated_by UUID,
    validated_at TIMESTAMP,
    rejection_reason TEXT,
    checksum VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents.document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents.documents(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    file_name VARCHAR(255),
    storage_path VARCHAR(500),
    uploaded_by UUID,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version)
);

CREATE TABLE documents.signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents.documents(id) ON DELETE CASCADE,
    signer_id UUID NOT NULL,
    signer_type VARCHAR(50),
    signature_data TEXT,
    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

CREATE TABLE documents.certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID NOT NULL,
    certificate_number VARCHAR(100) UNIQUE NOT NULL,
    certificate_type VARCHAR(50) CHECK (certificate_type IN ('INTERNSHIP_CERTIFICATE', 'ATTESTATION', 'RECOMMENDATION')),
    document_id UUID REFERENCES documents.documents(id),
    issued_by UUID NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verification_code VARCHAR(50) UNIQUE,
    metadata JSONB
);

CREATE INDEX idx_documents_owner ON documents.documents(owner_id, owner_type);
CREATE INDEX idx_documents_type ON documents.documents(document_type);

-- ============================================
-- SCHEMA: NOTIFICATIONS SERVICE DATABASE
-- ============================================

CREATE SCHEMA IF NOT EXISTS notifications;

CREATE TABLE notifications.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    channel VARCHAR(50) CHECK (channel IN ('EMAIL', 'PUSH', 'SMS', 'IN_APP')),
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'READ')),
    priority VARCHAR(50) DEFAULT 'NORMAL' CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')),
    metadata JSONB,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications.templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    subject VARCHAR(200),
    body_template TEXT NOT NULL,
    channel VARCHAR(50),
    variables JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications.preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL,
    email_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,
    sms_enabled BOOLEAN DEFAULT false,
    notification_types JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications.notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications.notifications(status);
CREATE INDEX idx_notifications_created ON notifications.notifications(created_at);

-- ============================================
-- TRIGGERS FOR updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth.users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON students.students FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_enterprises_updated_at BEFORE UPDATE ON enterprises.enterprises FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers.offers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications.applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_internships_updated_at BEFORE UPDATE ON internships.internships FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();