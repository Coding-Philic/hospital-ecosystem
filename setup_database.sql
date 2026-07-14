-- ============================================================
-- MediFlow AI — Complete Database Schema for Supabase PostgreSQL
-- ============================================================
-- Run this entire file in the Supabase SQL Editor to set up the database.
-- This creates all tables, enums, indexes, RLS policies, and seed data.
-- ============================================================

-- ╔══════════════════════════════════════════════════════════╗
-- ║  1. CUSTOM TYPES / ENUMS                                 ║
-- ╚══════════════════════════════════════════════════════════╝

CREATE TYPE user_role AS ENUM ('patient', 'doctor', 'receptionist', 'pharmacist', 'admin');
CREATE TYPE urgency_level AS ENUM ('routine', 'semi_urgent', 'urgent', 'emergency');
CREATE TYPE doctor_status AS ENUM ('available', 'busy', 'on_break', 'offline');
CREATE TYPE appointment_status AS ENUM ('waiting', 'in_progress', 'completed', 'cancelled', 'no_show');
CREATE TYPE prescription_status AS ENUM ('created', 'sent_to_pharmacy', 'partially_available', 'dispensed', 'cancelled');
CREATE TYPE workflow_state AS ENUM (
    'registered', 'triaged', 'queued', 'in_consultation',
    'investigation_ordered', 'investigation_complete',
    'prescribed', 'at_pharmacy', 'dispensed', 'billing', 'discharged'
);
CREATE TYPE notification_type AS ENUM (
    'queue_update', 'consultation_ready', 'prescription_ready',
    'pharmacy_ready', 'investigation_result', 'appointment_reminder',
    'system_alert', 'workflow_update'
);


-- ╔══════════════════════════════════════════════════════════╗
-- ║  2. TABLES                                               ║
-- ╚══════════════════════════════════════════════════════════╝

-- ── Users (extends Supabase auth.users) ──────────────────────
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role user_role NOT NULL DEFAULT 'patient',
    avatar_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Departments ──────────────────────────────────────────────
CREATE TABLE public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    floor_number INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Doctors ──────────────────────────────────────────────────
CREATE TABLE public.doctors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    department_id UUID NOT NULL REFERENCES public.departments(id),
    specialization TEXT,
    qualification TEXT,
    experience_years INTEGER,
    license_number TEXT,
    consultation_fee DECIMAL(10,2) DEFAULT 0,
    status doctor_status NOT NULL DEFAULT 'offline',
    max_daily_patients INTEGER DEFAULT 30,
    current_token INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ── Patients ─────────────────────────────────────────────────
CREATE TABLE public.patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    patient_id_code TEXT NOT NULL UNIQUE,    -- e.g., MF-XXXXXXXX
    date_of_birth DATE,
    gender TEXT,
    blood_group TEXT,
    address TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    insurance_provider TEXT,
    insurance_id TEXT,
    allergies TEXT[],
    chronic_conditions TEXT[],
    medical_history JSONB DEFAULT '[]'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ── Appointments / Queue Tokens ──────────────────────────────
CREATE TABLE public.appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES public.patients(id),
    doctor_id UUID NOT NULL REFERENCES public.doctors(id),
    department_id UUID NOT NULL REFERENCES public.departments(id),
    token_number TEXT NOT NULL,
    queue_position INTEGER NOT NULL,
    status appointment_status NOT NULL DEFAULT 'waiting',
    urgency urgency_level NOT NULL DEFAULT 'routine',
    symptom_summary TEXT,
    ai_recommended_department TEXT,
    ai_urgency_score TEXT,
    ai_confidence DECIMAL(5,2),
    receptionist_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_by UUID REFERENCES public.users(id),
    scheduled_date DATE NOT NULL DEFAULT CURRENT_DATE,
    estimated_time TIMESTAMPTZ,
    check_in_time TIMESTAMPTZ,
    consultation_start_time TIMESTAMPTZ,
    consultation_end_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Consultations ────────────────────────────────────────────
CREATE TABLE public.consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES public.appointments(id),
    patient_id UUID NOT NULL REFERENCES public.patients(id),
    doctor_id UUID NOT NULL REFERENCES public.doctors(id),
    symptoms TEXT,
    examination_notes TEXT,
    diagnosis TEXT,
    diagnosis_code TEXT,               -- ICD code if applicable
    additional_notes TEXT,
    follow_up_date DATE,
    follow_up_notes TEXT,
    vitals JSONB DEFAULT '{}'::JSONB,  -- {bp, temp, pulse, weight, height, spo2}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Medicines Catalog ────────────────────────────────────────
CREATE TABLE public.medicines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    generic_name TEXT,
    category TEXT,                     -- e.g., Antibiotic, Analgesic
    manufacturer TEXT,
    dosage_form TEXT,                  -- e.g., Tablet, Syrup, Injection
    strength TEXT,                     -- e.g., 500mg, 10ml
    unit_price DECIMAL(10,2) DEFAULT 0,
    requires_prescription BOOLEAN DEFAULT TRUE,
    alternative_medicine_ids UUID[],   -- Pre-approved generic alternatives
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Prescriptions ────────────────────────────────────────────
CREATE TABLE public.prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_code TEXT NOT NULL UNIQUE,  -- RX-XXXXXXXXXX
    consultation_id UUID NOT NULL REFERENCES public.consultations(id),
    patient_id UUID NOT NULL REFERENCES public.patients(id),
    doctor_id UUID NOT NULL REFERENCES public.doctors(id),
    status prescription_status NOT NULL DEFAULT 'created',
    pharmacy_notes TEXT,
    total_amount DECIMAL(10,2) DEFAULT 0,
    dispensed_by UUID REFERENCES public.users(id),
    dispensed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Prescription Items ───────────────────────────────────────
CREATE TABLE public.prescription_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES public.prescriptions(id) ON DELETE CASCADE,
    medicine_id UUID REFERENCES public.medicines(id),
    medicine_name TEXT NOT NULL,
    dosage TEXT NOT NULL,                    -- e.g., "500mg"
    frequency TEXT NOT NULL,                 -- e.g., "Twice daily (BD)"
    duration TEXT NOT NULL,                  -- e.g., "5 days"
    route TEXT DEFAULT 'Oral',
    quantity INTEGER NOT NULL DEFAULT 1,
    instructions TEXT,                       -- e.g., "Take after meals"
    is_in_stock BOOLEAN,
    substitute_medicine_id UUID REFERENCES public.medicines(id),
    substitute_approved_by UUID REFERENCES public.users(id),
    substitute_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Pharmacy Inventory ───────────────────────────────────────
CREATE TABLE public.pharmacy_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medicine_id UUID NOT NULL REFERENCES public.medicines(id),
    batch_number TEXT,
    quantity_available INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    expiry_date DATE,
    unit_cost DECIMAL(10,2) DEFAULT 0,
    selling_price DECIMAL(10,2) DEFAULT 0,
    last_restocked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Workflow State Tracking ──────────────────────────────────
CREATE TABLE public.workflow_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES public.appointments(id),
    patient_id UUID NOT NULL REFERENCES public.patients(id),
    current_state workflow_state NOT NULL DEFAULT 'registered',
    previous_state workflow_state,
    transitioned_by UUID REFERENCES public.users(id),
    transitioned_by_role user_role,
    notes TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Audit Log ────────────────────────────────────────────────
CREATE TABLE public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES public.users(id),
    actor_role user_role,
    action TEXT NOT NULL,                    -- e.g., "ai_triage", "override_department", "approve_substitute"
    entity_type TEXT NOT NULL,               -- e.g., "appointment", "prescription"
    entity_id UUID,
    details JSONB DEFAULT '{}'::JSONB,
    ai_model_used TEXT,
    ai_confidence DECIMAL(5,2),
    was_overridden BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Notifications ────────────────────────────────────────────
CREATE TABLE public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ╔══════════════════════════════════════════════════════════╗
-- ║  3. INDEXES                                              ║
-- ╚══════════════════════════════════════════════════════════╝

CREATE INDEX idx_users_role ON public.users(role);
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_doctors_department ON public.doctors(department_id);
CREATE INDEX idx_doctors_status ON public.doctors(status);
CREATE INDEX idx_doctors_user ON public.doctors(user_id);
CREATE INDEX idx_patients_user ON public.patients(user_id);
CREATE INDEX idx_patients_code ON public.patients(patient_id_code);
CREATE INDEX idx_appointments_patient ON public.appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON public.appointments(doctor_id);
CREATE INDEX idx_appointments_date ON public.appointments(scheduled_date);
CREATE INDEX idx_appointments_status ON public.appointments(status);
CREATE INDEX idx_consultations_appointment ON public.consultations(appointment_id);
CREATE INDEX idx_prescriptions_patient ON public.prescriptions(patient_id);
CREATE INDEX idx_prescriptions_status ON public.prescriptions(status);
CREATE INDEX idx_prescription_items_prescription ON public.prescription_items(prescription_id);
CREATE INDEX idx_pharmacy_inventory_medicine ON public.pharmacy_inventory(medicine_id);
CREATE INDEX idx_workflow_states_appointment ON public.workflow_states(appointment_id);
CREATE INDEX idx_workflow_states_patient ON public.workflow_states(patient_id);
CREATE INDEX idx_audit_log_entity ON public.audit_log(entity_type, entity_id);
CREATE INDEX idx_notifications_user ON public.notifications(user_id);
CREATE INDEX idx_notifications_unread ON public.notifications(user_id, is_read) WHERE is_read = FALSE;


-- ╔══════════════════════════════════════════════════════════╗
-- ║  4. ROW LEVEL SECURITY (RLS)                             ║
-- ╚══════════════════════════════════════════════════════════╝

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consultations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medicines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prescription_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pharmacy_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- ── Users policies ───────────────────────────────────────────
CREATE POLICY "Users can view own profile"
    ON public.users FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Admins can view all users"
    ON public.users FOR SELECT
    TO authenticated
    USING (
        (auth.jwt() -> 'user_metadata' ->> 'role') = 'admin'
    );

CREATE POLICY "Receptionists can view all users"
    ON public.users FOR SELECT
    TO authenticated
    USING (
        (auth.jwt() -> 'user_metadata' ->> 'role') = 'receptionist'
    );

CREATE POLICY "Users can update own profile"
    ON public.users FOR UPDATE
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Allow user creation on signup"
    ON public.users FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

-- ── Departments policies (public read) ───────────────────────
CREATE POLICY "Anyone can view departments"
    ON public.departments FOR SELECT
    TO authenticated
    USING (TRUE);

CREATE POLICY "Admins can manage departments"
    ON public.departments FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
    );

-- ── Doctors policies ─────────────────────────────────────────
CREATE POLICY "Anyone can view doctors"
    ON public.doctors FOR SELECT
    TO authenticated
    USING (TRUE);

CREATE POLICY "Doctors can update own record"
    ON public.doctors FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Admins can manage doctors"
    ON public.doctors FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
    );

-- ── Patients policies ────────────────────────────────────────
CREATE POLICY "Patients can view own record"
    ON public.patients FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Patients can update own record"
    ON public.patients FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Patients can insert own record"
    ON public.patients FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Doctors can view their patients"
    ON public.patients FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'receptionist', 'admin'))
    );

-- ── Appointments policies ────────────────────────────────────
CREATE POLICY "Patients can view own appointments"
    ON public.appointments FOR SELECT
    TO authenticated
    USING (
        patient_id IN (SELECT id FROM public.patients WHERE user_id = auth.uid())
    );

CREATE POLICY "Staff can view all appointments"
    ON public.appointments FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'receptionist', 'admin'))
    );

CREATE POLICY "Authenticated users can create appointments"
    ON public.appointments FOR INSERT
    TO authenticated
    WITH CHECK (TRUE);

CREATE POLICY "Staff can update appointments"
    ON public.appointments FOR UPDATE
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'receptionist', 'admin'))
    );

-- ── Consultations policies ───────────────────────────────────
CREATE POLICY "Patients can view own consultations"
    ON public.consultations FOR SELECT
    TO authenticated
    USING (
        patient_id IN (SELECT id FROM public.patients WHERE user_id = auth.uid())
    );

CREATE POLICY "Doctors can manage consultations"
    ON public.consultations FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'admin'))
    );

-- ── Medicines policies (public read) ─────────────────────────
CREATE POLICY "Anyone can view medicines"
    ON public.medicines FOR SELECT
    TO authenticated
    USING (TRUE);

CREATE POLICY "Pharmacists and admins can manage medicines"
    ON public.medicines FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('pharmacist', 'admin'))
    );

-- ── Prescriptions policies ───────────────────────────────────
CREATE POLICY "Patients can view own prescriptions"
    ON public.prescriptions FOR SELECT
    TO authenticated
    USING (
        patient_id IN (SELECT id FROM public.patients WHERE user_id = auth.uid())
    );

CREATE POLICY "Doctors can manage prescriptions"
    ON public.prescriptions FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'admin'))
    );

CREATE POLICY "Pharmacists can view and update prescriptions"
    ON public.prescriptions FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'pharmacist')
    );

CREATE POLICY "Pharmacists can update prescription status"
    ON public.prescriptions FOR UPDATE
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'pharmacist')
    );

-- ── Prescription Items policies ──────────────────────────────
CREATE POLICY "Staff can view prescription items"
    ON public.prescription_items FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'pharmacist', 'admin'))
    );

CREATE POLICY "Patients can view own prescription items"
    ON public.prescription_items FOR SELECT
    TO authenticated
    USING (
        prescription_id IN (
            SELECT id FROM public.prescriptions WHERE patient_id IN (
                SELECT id FROM public.patients WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Doctors can manage prescription items"
    ON public.prescription_items FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'admin'))
    );

CREATE POLICY "Pharmacists can update prescription items"
    ON public.prescription_items FOR UPDATE
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'pharmacist')
    );

-- ── Pharmacy Inventory policies ──────────────────────────────
CREATE POLICY "Staff can view inventory"
    ON public.pharmacy_inventory FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('pharmacist', 'doctor', 'admin'))
    );

CREATE POLICY "Pharmacists can manage inventory"
    ON public.pharmacy_inventory FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('pharmacist', 'admin'))
    );

-- ── Workflow States policies ─────────────────────────────────
CREATE POLICY "Patients can view own workflow"
    ON public.workflow_states FOR SELECT
    TO authenticated
    USING (
        patient_id IN (SELECT id FROM public.patients WHERE user_id = auth.uid())
    );

CREATE POLICY "Staff can view all workflows"
    ON public.workflow_states FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'receptionist', 'pharmacist', 'admin'))
    );

CREATE POLICY "Staff can insert workflow transitions"
    ON public.workflow_states FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role IN ('doctor', 'receptionist', 'pharmacist', 'admin'))
    );

-- ── Audit Log policies ──────────────────────────────────────
CREATE POLICY "Admins can view audit log"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "System can insert audit entries"
    ON public.audit_log FOR INSERT
    TO authenticated
    WITH CHECK (TRUE);

-- ── Notifications policies ───────────────────────────────────
CREATE POLICY "Users can view own notifications"
    ON public.notifications FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can update own notifications"
    ON public.notifications FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "System can create notifications"
    ON public.notifications FOR INSERT
    TO authenticated
    WITH CHECK (TRUE);


-- ╔══════════════════════════════════════════════════════════╗
-- ║  5. FUNCTIONS & TRIGGERS                                 ║
-- ╚══════════════════════════════════════════════════════════╝

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_doctors_updated_at
    BEFORE UPDATE ON public.doctors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_patients_updated_at
    BEFORE UPDATE ON public.patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_appointments_updated_at
    BEFORE UPDATE ON public.appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_consultations_updated_at
    BEFORE UPDATE ON public.consultations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_prescriptions_updated_at
    BEFORE UPDATE ON public.prescriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ╔══════════════════════════════════════════════════════════╗
-- ║  6. SEED DATA                                            ║
-- ╚══════════════════════════════════════════════════════════╝

-- ── Insert Departments ───────────────────────────────────────
INSERT INTO public.departments (name, description, floor_number) VALUES
    ('General Medicine', 'General outpatient consultations and primary care', 1),
    ('Cardiology', 'Heart and cardiovascular system', 2),
    ('Dermatology', 'Skin, hair, and nail conditions', 1),
    ('Orthopedics', 'Bones, joints, muscles, and ligaments', 2),
    ('Pediatrics', 'Child and adolescent healthcare', 1),
    ('ENT (Ear, Nose, Throat)', 'Ear, nose, throat, and related structures', 3),
    ('Ophthalmology', 'Eye and vision care', 3),
    ('Gynecology', 'Women''s reproductive health', 2),
    ('Neurology', 'Brain, spinal cord, and nervous system', 3),
    ('Psychiatry', 'Mental health and behavioral disorders', 3),
    ('Pulmonology', 'Lungs and respiratory system', 2),
    ('Gastroenterology', 'Digestive system and gastrointestinal tract', 2),
    ('Urology', 'Urinary tract and male reproductive system', 3),
    ('Dental', 'Oral and dental health', 1),
    ('Emergency', 'Emergency and critical care', 1)
ON CONFLICT (name) DO NOTHING;

-- ── Insert Sample Medicines ──────────────────────────────────
INSERT INTO public.medicines (name, generic_name, category, manufacturer, dosage_form, strength, unit_price, requires_prescription) VALUES
    ('Paracetamol 500mg', 'Paracetamol', 'Analgesic/Antipyretic', 'Generic', 'Tablet', '500mg', 2.50, FALSE),
    ('Amoxicillin 500mg', 'Amoxicillin', 'Antibiotic', 'Generic', 'Capsule', '500mg', 8.00, TRUE),
    ('Azithromycin 500mg', 'Azithromycin', 'Antibiotic', 'Generic', 'Tablet', '500mg', 15.00, TRUE),
    ('Omeprazole 20mg', 'Omeprazole', 'Proton Pump Inhibitor', 'Generic', 'Capsule', '20mg', 5.00, TRUE),
    ('Metformin 500mg', 'Metformin', 'Antidiabetic', 'Generic', 'Tablet', '500mg', 3.50, TRUE),
    ('Amlodipine 5mg', 'Amlodipine', 'Antihypertensive', 'Generic', 'Tablet', '5mg', 4.00, TRUE),
    ('Cetirizine 10mg', 'Cetirizine', 'Antihistamine', 'Generic', 'Tablet', '10mg', 3.00, FALSE),
    ('Ibuprofen 400mg', 'Ibuprofen', 'NSAID', 'Generic', 'Tablet', '400mg', 3.50, FALSE),
    ('Pantoprazole 40mg', 'Pantoprazole', 'Proton Pump Inhibitor', 'Generic', 'Tablet', '40mg', 6.00, TRUE),
    ('Atorvastatin 10mg', 'Atorvastatin', 'Statin', 'Generic', 'Tablet', '10mg', 7.00, TRUE),
    ('Losartan 50mg', 'Losartan', 'ARB Antihypertensive', 'Generic', 'Tablet', '50mg', 5.50, TRUE),
    ('Metoprolol 25mg', 'Metoprolol', 'Beta Blocker', 'Generic', 'Tablet', '25mg', 4.00, TRUE),
    ('Salbutamol Inhaler', 'Salbutamol', 'Bronchodilator', 'Generic', 'Inhaler', '100mcg', 120.00, TRUE),
    ('Diclofenac Gel', 'Diclofenac', 'NSAID Topical', 'Generic', 'Gel', '1%', 45.00, FALSE),
    ('Montelukast 10mg', 'Montelukast', 'Leukotriene Inhibitor', 'Generic', 'Tablet', '10mg', 8.00, TRUE),
    ('Doxycycline 100mg', 'Doxycycline', 'Antibiotic', 'Generic', 'Capsule', '100mg', 6.00, TRUE),
    ('Clopidogrel 75mg', 'Clopidogrel', 'Antiplatelet', 'Generic', 'Tablet', '75mg', 9.00, TRUE),
    ('Levothyroxine 50mcg', 'Levothyroxine', 'Thyroid Hormone', 'Generic', 'Tablet', '50mcg', 5.00, TRUE),
    ('Fluconazole 150mg', 'Fluconazole', 'Antifungal', 'Generic', 'Capsule', '150mg', 12.00, TRUE),
    ('ORS Sachets', 'Oral Rehydration Salts', 'Rehydration', 'Generic', 'Powder', '21.8g', 10.00, FALSE);

-- ── Insert Pharmacy Inventory for all medicines ──────────────
INSERT INTO public.pharmacy_inventory (medicine_id, batch_number, quantity_available, reorder_level, expiry_date, selling_price)
SELECT
    m.id,
    'BATCH-' || LPAD(ROW_NUMBER() OVER ()::TEXT, 4, '0'),
    CASE WHEN random() > 0.15 THEN (random() * 200 + 10)::INTEGER ELSE 0 END,  -- ~15% out of stock
    10,
    CURRENT_DATE + INTERVAL '1 year',
    m.unit_price * 1.3  -- 30% markup
FROM public.medicines m;

-- ╔══════════════════════════════════════════════════════════╗
-- ║  ATOMIC FUNCTIONS (Multi-User Safety)                     ║
-- ╚══════════════════════════════════════════════════════════╝

-- Atomically increment a doctor's current_token and return the new value.
-- Prevents race conditions when multiple patients submit at the same time.
CREATE OR REPLACE FUNCTION increment_and_return_token(p_doctor_id UUID)
RETURNS INT AS $$
DECLARE new_token INT;
BEGIN
    UPDATE doctors
    SET current_token = COALESCE(current_token, 0) + 1
    WHERE id = p_doctor_id
    RETURNING current_token INTO new_token;
    RETURN new_token;
END;
$$ LANGUAGE plpgsql;

-- ══════════════════════════════════════════════════════════════
-- SETUP COMPLETE
-- ══════════════════════════════════════════════════════════════
