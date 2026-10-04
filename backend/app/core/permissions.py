from fastapi import Depends, HTTPException, status
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.evidence import EvidenceFile
from app.models.evaluation import ConflictDeclaration
from uuid import UUID

POLICY: dict[str, set[str]] = {
    'challenge.publish':       {'officer'},
    'challenge.create_draft':  {'officer'},
    'startup.register':        {'officer'},
    'startup.verify_eligibility': {'officer'},
    'evaluation.score':        {'evaluator'},
    'evaluation.view':         {'officer', 'evaluator', 'validator'},
    'pilot.approve':           {'officer'},
    'pilot.revise_plan':       {'officer'},
    'agreement.accept_terms':  {'startup'},
    'evidence.submit':         {'startup'},
    'evidence.validate':       {'validator'},
    'evidence.approve_own':    set(),
    'evidence.view':           {'officer', 'validator', 'startup', 'finance'},
    'evidence.decide':         {'validator'},
    'milestone.accept':        {'officer'},
    'milestone.submit_invoice': {'startup'},
    'milestone.approve_invoice': {'finance'},
    'milestone.initiate_payment': {'finance'},
    'milestone.confirm_payment':  {'finance'},
    'transfer.assess':         {'officer', 'validator', 'district'},
    'transfer.profile.manage': {'officer', 'district'},
    'decision.record':         {'officer'},
    'audit.read':              {'officer', 'validator', 'finance'},
    'finance.read':            {'officer', 'finance'},
    'policy.read':             {'officer', 'evaluator', 'validator', 'finance', 'startup', 'district'},
    'challenge.read':          {'officer', 'evaluator', 'validator', 'startup', 'district'},
    'pilot.read':              {'officer', 'evaluator', 'validator', 'startup', 'finance', 'district'},
    'auth.demo_users':         {'officer', 'evaluator', 'validator', 'finance', 'startup'},
    'agreement.approve.named': {'officer', 'validator', 'finance'},
    'pilot.revise_kpi':        {'officer', 'evaluator'},
    'lifecycle.transition.published': {'officer'},
    'lifecycle.transition.applications_open': {'officer'},
    'lifecycle.transition.evaluating': {'officer', 'evaluator'},
    'lifecycle.transition.shortlisted': {'officer', 'evaluator'},
    'lifecycle.transition.agreement_drafted': {'officer'},
    'lifecycle.transition.agreement_approved': {'officer'},
    'lifecycle.transition.pilot_running': {'officer'},
    'lifecycle.transition.evidence_submitted': {'startup'},
    'lifecycle.transition.validated': {'validator'},
    'lifecycle.transition.accepted': {'officer'},
    'lifecycle.transition.invoice_approved': {'finance'},
    'lifecycle.transition.payment_initiated': {'finance'},
    'lifecycle.transition.payment_confirmed': {'finance'},
    'lifecycle.transition.scale_up_review': {'officer', 'district'},
    'lifecycle.transition.decision_recorded': {'officer'},
    'lifecycle.transition.disputed': {'officer', 'evaluator', 'validator', 'finance', 'startup', 'district'},
    'lifecycle.transition.correction_requested': {'officer', 'evaluator', 'validator', 'finance', 'startup', 'district'},
    'lifecycle.transition.terminated': {'officer'},
}

LIFECYCLE_TRANSITION_ACTIONS: dict[str, str] = {
    'Published': 'lifecycle.transition.published',
    'Applications Open': 'lifecycle.transition.applications_open',
    'Evaluating': 'lifecycle.transition.evaluating',
    'Shortlisted': 'lifecycle.transition.shortlisted',
    'Agreement Drafted': 'lifecycle.transition.agreement_drafted',
    'Agreement Approved': 'lifecycle.transition.agreement_approved',
    'Pilot Running': 'lifecycle.transition.pilot_running',
    'Evidence Submitted': 'lifecycle.transition.evidence_submitted',
    'Validated': 'lifecycle.transition.validated',
    'Accepted': 'lifecycle.transition.accepted',
    'Invoice Approved': 'lifecycle.transition.invoice_approved',
    'Payment Initiated': 'lifecycle.transition.payment_initiated',
    'Payment Confirmed': 'lifecycle.transition.payment_confirmed',
    'Scale-up Review': 'lifecycle.transition.scale_up_review',
    'Decision Recorded': 'lifecycle.transition.decision_recorded',
    'Disputed': 'lifecycle.transition.disputed',
    'Correction Requested': 'lifecycle.transition.correction_requested',
    'Terminated': 'lifecycle.transition.terminated',
}


def enforce_action(current_user: OIDCUserInfo, action: str) -> None:
    """Enforce a policy-table action whose name is selected at runtime."""
    allowed = POLICY.get(action)
    if allowed is None:
        raise HTTPException(403, detail='This lifecycle action is not configured.')
    if current_user.role not in allowed:
        raise HTTPException(403, detail=f"Role '{current_user.role}' cannot perform '{action}'.")

def require(role_or_action: str, action: str | None = None):
    """Build a backend permission dependency from the central policy table.

    `require('officer', 'challenge.publish')` is the explicit preferred form.
    `require('challenge.publish')` remains supported for existing routes.
    """
    required_role = role_or_action.lower() if action is not None else None
    policy_action = action if action is not None else role_or_action
    if policy_action not in POLICY:
        raise ValueError(f'Unknown permission action: {policy_action}')
    if required_role is not None and required_role not in POLICY[policy_action]:
        raise ValueError(f"Role '{required_role}' is not permitted by policy action '{policy_action}'.")

    async def _check(current_user: OIDCUserInfo = Depends(get_current_user)):
        allowed = POLICY[policy_action]
        if current_user.role not in allowed or (required_role is not None and current_user.role != required_role):
            raise HTTPException(403, detail=f"Role '{current_user.role}' cannot perform '{policy_action}'.")
        return current_user
    return _check

def require_no_own_evidence_approval(evidence_file_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    try:
        evidence_uuid = UUID(evidence_file_id)
    except ValueError as error:
        raise HTTPException(404, detail='Evidence record not found.') from error
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_uuid).first()
    if ev and str(ev.submitted_by) == current_user.sub:
        raise HTTPException(403, detail="Cannot validate own evidence")
    return current_user

def require_no_conflict(startup_id: str, challenge_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    try:
        evaluator_uuid = UUID(current_user.sub)
        startup_uuid = UUID(startup_id)
    except ValueError as error:
        raise HTTPException(400, detail='Invalid evaluator or applicant identifier.') from error
    conflict = db.query(ConflictDeclaration).filter(
        ConflictDeclaration.evaluator_id == evaluator_uuid,
        ConflictDeclaration.startup_id == startup_uuid,
        ConflictDeclaration.challenge_id == challenge_id
    ).first()
    if conflict and conflict.has_conflict:
        raise HTTPException(403, detail="Evaluator with a declared conflict cannot score this application.")
    return current_user
