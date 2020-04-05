
#pragma once

struct PatientRef
{
    bool dead = false;

    ~PatientRef()
    {
        dead = true;
    }
};

struct Nurse
{
    // robotpy-build should auto-detect the reference and add a keepalive here
    Nurse(PatientRef &p) : m_p(p) {}

    bool patientDead()
    {
        return m_p.dead;
    }

    PatientRef &m_p;
};
