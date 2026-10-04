"""Idempotently seed synthetic PilotProof demo records."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.passwords import hash_password
from app.db.base import Base
import app.models  # noqa: F401 — register all declarative models
import app.workflow.models  # noqa: F401 — register lifecycle tables
from app.models.challenge import Challenge, ChallengeVersion
from app.models.evaluation import RubricVersion
from app.models.organisation import Organisation
from app.models.policy import PolicySource
from app.models.startup import Application, EligibilityCheck, Startup
from app.models.transfer import DistrictProfile
from app.models.user import Role, User

ROLE_DATA = [
    ('officer', 'Officer', 'Publishes challenges and records procurement decisions.'),
    ('startup', 'Startup Applicant', 'Submits applications, evidence, and invoices.'),
    ('evaluator', 'Evaluator', 'Scores applications when no conflict is declared.'),
    ('validator', 'Validator', 'Independently reviews evidence.'),
    ('finance', 'Finance', 'Reviews invoices and records payment status.'),
    ('district', 'Receiving District', 'Reviews transfer readiness.'),
]
USER_DATA = [
    ('officer@pilotproof.dev', 'Officer Priya Sharma', 'officer', 'MSInS Demo Department'),
    ('startup@pilotproof.dev', 'Startup Arjun Mehta', 'startup', 'Vidarbha Civic Tech (Synthetic)'),
    ('evaluator@pilotproof.dev', 'Expert Kavita Nair', 'evaluator', 'MSInS Evaluation Panel'),
    ('validator@pilotproof.dev', 'Validator Rajan Patel', 'validator', 'Independent Validation Body'),
    ('finance@pilotproof.dev', 'Finance Deepa Rao', 'finance', 'MSInS Finance Desk'),
    ('district@pilotproof.dev', 'District Collector Suresh Bhat', 'district', 'Pune Urban Receiving District'),
]
POLICY_DATA = [
    ('Maharashtra municipal work-order limit (synthetic reference)', 'Maharashtra', '2019-15L', date(2019, 4, 1), 'procurement_limit', 'Synthetic historical demo reference: work-order limit ₹15 lakh. Confirm the applicable official circular before use.'),
    ('Maharashtra municipal work-order limit (synthetic reference)', 'Maharashtra', '2023-25L', date(2023, 7, 1), 'procurement_limit', 'Synthetic later demo reference: work-order limit ₹25 lakh. Confirm official sources; this is not legal advice.'),
    ('Pilot eligibility conditions (synthetic demo policy)', 'Maharashtra (demo only)', 'ELIG-DEMO-1.0', date(2026, 1, 1), 'eligibility', 'Synthetic demo condition: DPIIT recognition and annual turnover at or below ₹100 lakh; exemptions require a cited source and human review. Not official policy.'),
]
STARTUP_DATA = [
    ('AquaMap Systems (Synthetic)', 'Pune', 'Water', 2021, 48, True, ['water leakage detection', 'IoT sensors', 'GIS mapping'], 'Two municipal pilot deployments in water networks.', ['Marathi', 'English'], 'Pilot-ready; field installation checklist available.', ['Synthetic pilot report: mapped water assets in a sample ward.']),
    ('Swasthya Connect (Synthetic)', 'Nashik', 'Health', 2019, 160, True, ['health workflow', 'clinic scheduling', 'patient follow-up'], 'Three years supporting clinic workflow pilots.', ['Marathi', 'Hindi', 'English'], 'Pilot deployed in synthetic clinic locations.', ['Synthetic clinic note: follow-up workflow tested with staff.']),
    ('Shiksha Setu Labs (Synthetic)', 'Nagpur', 'Education', 2023, 22, False, ['school attendance', 'learning support', 'offline education'], 'One school demonstration; sample requires verification.', ['Marathi'], 'Prototype; production support not documented.', ['Synthetic demo: offline attendance workflow shown to staff.']),
    ('GramRoute Mobility (Synthetic)', 'Kolhapur', 'Mobility', 2017, 320, False, ['route planning', 'public transport', 'GIS mapping'], 'Regional route work described; records not attached.', ['Hindi', 'English'], 'Deployment plan not documented.', ['Synthetic capability tags need source artefacts.']),
    ('JalRakshak Analytics (Synthetic)', 'Aurangabad', 'Water', 2020, 85, True, ['water quality', 'sensor telemetry', 'offline sync'], 'Water-quality field experience stated; references pending.', ['Marathi', 'English'], 'Pilot package documented; connectivity checks pending.', ['Synthetic note: offline sampling demonstrated.']),
    ('ShetSetu Digital (Synthetic)', 'Amravati', 'Agriculture', 2018, 125, True, ['crop advisory', 'soil data', 'farmer messaging'], 'Four seasons of synthetic advisory field notes.', ['Marathi', 'Hindi'], 'Low-bandwidth plan documented.', ['Synthetic note: low-bandwidth messaging tested.']),
    ('CivicQueue Labs (Synthetic)', 'Mumbai', 'Public service', 2022, 36, True, ['service centre workflow', 'queue management', 'analytics'], 'Service-centre references attached.', ['Marathi', 'English', 'Hindi'], 'Production support rota documented.', ['Synthetic service log: queue tickets linked to timestamps.']),
    ('ArogyaPath Systems (Synthetic)', 'Pune', 'Health', 2016, 520, False, ['clinic workflow', 'referral routing', 'reporting'], 'Seven years claimed; turnover exceeds demo threshold.', ['Marathi', 'English'], 'Live deployment claims require independent validation.', ['Synthetic clinic deployment claim; verification pending.']),
    ('GramSakhi Connect (Synthetic)', 'Gadchiroli', 'Public service', 2024, 9, False, ['Marathi voice interface', 'offline forms', 'citizen support'], 'New venture; field references not documented.', ['Marathi'], 'Prototype for intermittent network.', ['Synthetic prototype note: offline form shown.']),
    ('NagarPulse Technologies (Synthetic)', 'Thane', 'Public service', 2015, 290, True, ['complaint routing', 'municipal analytics', 'GIS mapping'], 'Municipal operations experience described.', ['Marathi', 'English'], 'Deployment readiness evidence incomplete.', ['Synthetic case summary: complaint routing dashboard sample.']),
]


def seed() -> None:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session.begin() as db:
        for role_name, label, description in ROLE_DATA:
            role = db.get(Role, role_name)
            if role is None:
                db.add(Role(name=role_name, label=label, description=description))
            else:
                role.label, role.description = label, description
        db.flush()

        organizations: dict[str, Organisation] = {}
        for _, _, _, organization_name in USER_DATA:
            organization = db.query(Organisation).filter_by(name=organization_name).first()
            if organization is None:
                organization = Organisation(
                    id=uuid4(), name=organization_name,
                    org_type='startup' if 'Synthetic)' in organization_name else 'department',
                    district='Maharashtra',
                )
                db.add(organization)
            organizations[organization_name] = organization
        db.flush()

        users: dict[str, User] = {}
        for email, name, role_name, organization_name in USER_DATA:
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                user = User(id=uuid4(), email=email, full_name=name, role=role_name,
                            hashed_password=hash_password('demo1234'), organisation_id=organizations[organization_name].id)
                db.add(user)
            else:
                user.role = role_name
                user.organisation_id = organizations[organization_name].id
                if not user.hashed_password.startswith('pbkdf2_sha256$'):
                    user.hashed_password = hash_password('demo1234')
            users[role_name] = user
        db.flush()

        for title, jurisdiction, version, effective_date, policy_type, notes in POLICY_DATA:
            if not db.query(PolicySource).filter_by(version=version).first():
                db.add(PolicySource(
                    id=uuid4(), title=title, jurisdiction=jurisdiction, version=version,
                    effective_date=effective_date,
                    url=f'https://example.invalid/synthetic-policy/{version}',
                    policy_type=policy_type, notes=notes,
                ))

        challenge = db.query(Challenge).filter_by(id='MH-MUNI-SC-001').first()
        if challenge is None:
            challenge = Challenge(
                id='MH-MUNI-SC-001', title='Municipal Service-Centre Wait-Time and Routing Pilot (Synthetic)',
                department='Maharashtra State Innovation Society', district='Pune Urban',
                sector='Public service', status='Open', published_by=users['officer'].id,
                measurement_locked=True,
            )
            db.add(challenge)
            db.flush()
        if not db.query(ChallengeVersion).filter_by(challenge_id=challenge.id, version=1).first():
            db.add(ChallengeVersion(
                id=uuid4(), challenge_id=challenge.id, version=1,
                description='Synthetic challenge: improve queue visibility and service-request routing at municipal service centres.',
                problem_statement='Residents face uncertain waits and repeated referrals when requesting municipal services.',
                outcomes=['Make service-centre wait and routing evidence reviewable.'],
                budget=2500000, target_pct=None, deadline=date(2026, 12, 31),
                metric='Median request-to-routing time; repeat-referral count',
                baseline='Baseline unavailable',
                test_plan='Collect a pre-pilot baseline, test at urban and rural sites, and record network conditions.',
                test_duration_days=60,
                acceptance_criteria=['Independent validator can reproduce results from attached source records.'],
                input_language='en', change_note='Initial synthetic seeded version',
                is_published=True, created_by=users['officer'].id,
            ))

        startup_profiles: dict[str, Startup] = {}
        for item in STARTUP_DATA:
            name, city, sector, founded, turnover, dpiit, tags, experience, languages, readiness, snippets = item
            startup = db.query(Startup).filter_by(name=name).first()
            organization_id = organizations['Vidarbha Civic Tech (Synthetic)'].id if name.startswith('Shiksha Setu') else None
            if startup is None:
                startup = Startup(
                    id=uuid4(), name=name, city=city, sector=sector, founded_year=founded,
                    annual_turnover_lakhs=turnover, dpiit_recognised=dpiit,
                    organisation_id=organization_id, capability_tags=tags, domain_experience=experience,
                    languages_supported=languages, deployment_readiness=readiness, evidence_snippets=snippets,
                )
                db.add(startup)
            else:
                startup.capability_tags, startup.domain_experience = tags, experience
                startup.languages_supported, startup.deployment_readiness = languages, readiness
                startup.evidence_snippets = snippets
                if organization_id:
                    startup.organisation_id = organization_id
            startup_profiles[name] = startup
        db.flush()

        for name, kind, volume, bandwidth, notes in [
            ('Pune Urban', 'Urban', 180, 50.0, 'Synthetic profile: higher bandwidth, lower daily service-centre volume.'),
            ('Gadchiroli Rural', 'Rural', 620, 2.0, 'Synthetic profile: lower bandwidth, higher daily volume; offline-first review matters.'),
        ]:
            profile = db.query(DistrictProfile).filter_by(name=name).first()
            if profile is None:
                db.add(DistrictProfile(id=uuid4(), name=name, district_type=kind,
                                       daily_case_volume=volume, bandwidth_mbps=bandwidth,
                                       primary_language='Marathi', notes=notes))

        if not db.query(RubricVersion).filter_by(challenge_id=challenge.id, version=1).first():
            db.add(RubricVersion(id=uuid4(), challenge_id=challenge.id, version=1,
                                 weights={'capability_evidence': 35, 'domain_experience': 25, 'language_support': 20, 'deployment_readiness': 20},
                                 criteria=[
                                     {'key': 'capability_evidence', 'label': 'Capability evidence', 'weight': 35},
                                     {'key': 'domain_experience', 'label': 'Domain experience', 'weight': 25},
                                     {'key': 'language_support', 'label': 'Language support', 'weight': 20},
                                     {'key': 'deployment_readiness', 'label': 'Deployment readiness', 'weight': 20},
                                 ],
                                 published_by=users['officer'].id))

        profile = startup_profiles['Shiksha Setu Labs (Synthetic)']
        if not db.query(Application).filter_by(startup_id=profile.id, challenge_id=challenge.id).first():
            db.add(Application(id=uuid4(), startup_id=profile.id, challenge_id=challenge.id, status='Shortlisted'))
        if not db.query(EligibilityCheck).filter_by(startup_id=profile.id, challenge_id=challenge.id).first():
            db.add(EligibilityCheck(
                id=uuid4(), startup_id=profile.id, challenge_id=challenge.id,
                checked_by=users['officer'].id, passed=False,
                note='Synthetic seeded reason: DPIIT recognition document is not recorded; verification required.',
                evidence_ref='Synthetic demo rule ELIG-DEMO-1.0; upload a current DPIIT recognition certificate.',
            ))

    print('Seed complete: 6 roles/users, 1 municipal service-centre challenge, 10 synthetic startups, 2 district profiles, 3 policy sources.')
    print('All demo passwords: demo1234')
    engine.dispose()


if __name__ == '__main__':
    seed()
