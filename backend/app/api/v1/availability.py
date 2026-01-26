from __future__ import annotations
from datetime import datetime, timezone, date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, delete
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user
from app.api.v1.shifts import _require_manager_permission, _require_membership
from app.db.session import get_session
from app.models.availability import AvailabilityRequestCreate, \
    AvailabilityRequest, AvailabilitySubmission, AvailabilityDay, \
        AvailabilitySubmissionUpdate
from app.models.user import User


router = APIRouter(tags=['availability'])


# ------------------------- Availability API endpoints ------------------------

# Request availability from the employee
@router.post(
    '/restaurants/{restaurant_id}/availability/requests',
    status_code=status.HTTP_201_CREATED
)
def request_availability(
    *,
    restaurant_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    payload: AvailabilityRequestCreate
) -> dict:
    '''Create a monthly availability request for a restaurant.

    Owners/managers use this to open a time window in which employees can
    submit or update their availability for the target (year, month).
    '''
    check_membership = _require_membership(
        session=session,
        restaurant_id=restaurant_id,
        user_id=current_user.id
    )
    _require_manager_permission(check_membership)
    # Check month range
    # TODO: add an option to request availability weekly / twice per month
    if payload.month < 1 or payload.month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Month must be an integer between 1 and 12'
        )
    # Get closes_at date
    closes_at_utc = payload.closes_at_utc
    # Get opens_at date or insert if not set
    opens_at_utc = payload.opens_at_utc or datetime.now(timezone.utc)
    # Check open/close date timezones
    if opens_at_utc.tzinfo is None or closes_at_utc.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='opens_at_utc and closes_at_utc must be timezone-aware datetimes'
        )
    # Normalize datetime timezones into UTC for storage
    opens_at_utc = opens_at_utc.astimezone(timezone.utc)
    closes_at_utc = closes_at_utc.astimezone(timezone.utc)
    # Validate the open/close window
    if closes_at_utc <= opens_at_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='opens_at must be before closes_at'
        )
    # Prevent availability requests overlapping
    existing = session.exec(
        select(AvailabilityRequest).where(
            AvailabilityRequest.restaurant_id == restaurant_id,
            AvailabilityRequest.year == payload.year,
            AvailabilityRequest.month == payload.month,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Availability request already exists for this restaurant and month'
        )
    # Add request to the session and commit
    req = AvailabilityRequest(
        restaurant_id=restaurant_id,
        year=payload.year,
        month=payload.month,
        opens_at_utc=opens_at_utc,
        closes_at_utc=closes_at_utc,
        created_by_user_id=current_user.id
    )
    session.add(req)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Enable to commit DB changes due to Integrity Error: {e}'
        )
    session.refresh(req)

    return {
        'id': str(req.id),
        'restaurant_id': str(req.restaurant_id),
        'year': req.year,
        'month': req.month,
        'opens_at_utc': req.opens_at_utc.isoformat(),
        'closes_at_utc': req.closes_at_utc.isoformat(),
        'created_by_user_id': str(req.created_by_user_id)
    }


# Employee creates his submission
@router.get('/availability/requests/{request_id}/my-submission')
def get_create_submission(
    *,
    request_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    '''Get or create the current user's submission for a given request.

    - Before opens_at_utc: no draft submissions are allowed.
    - While open (now < closes_at_utc): create submission if missing.
    - After close (now >= closes_at_utc): allow read-only access if submission
      exists; otherwise return 404.
    '''
    req = session.get(AvailabilityRequest, request_id)
    # Check if request exists
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Availability request not found'
        )
    # If request exists: check employee membership
    _require_membership(
        session=session,
        restaurant_id=req.restaurant_id,
        user_id=current_user.id
    )
    # Get current datetime (UTC)
    now_utc = datetime.now(timezone.utc)
    # No drafts before open
    if now_utc < req.opens_at_utc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Availability window has not opened yet'
        )
    # Get submission from storage if already exists
    sub = session.exec(
        select(AvailabilitySubmission)
        .where(AvailabilitySubmission.request_id == request_id)
        .where(AvailabilitySubmission.user_id == current_user.id)
    ).first()
    # If closed: allow read-only if submission exists, else 404
    if now_utc >= req.closes_at_utc:
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='No submission found (availability window is closed)'
            )
    else:  # Window open: create if missing
        if not sub:
            sub = AvailabilitySubmission(
                request_id=request_id,
                user_id=current_user.id,
                status='draft',
                submitted_at_utc=None
            )
            session.add(sub)
            try: # Avoid to commit two same requests
                session.commit()
            except IntegrityError as e:
                session.rollback()
                constraint = getattr(
                    getattr(e.orig, 'diag', None), 'constraint_name', None
                )
                if constraint == 'uq_availabilitysubmission_request_user':
                    # Fetch another request if it commited in the same time
                    sub = session.exec(
                        select(AvailabilitySubmission)
                        .where(AvailabilitySubmission.request_id == request_id)
                        .where(AvailabilitySubmission.user_id == current_user.id)
                    ).first()
                    if not sub:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Submission creation conflicted but row could not be loaded'
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail='Unable to create submission due to a database integrity constraint'
                    )
            session.refresh(sub)
    days = session.exec(
        select(AvailabilityDay.date_local)
        .where(AvailabilityDay.submission_id == sub.id)
    ).all()

    return {
        'submission_id': str(sub.id),
        'request_id': str(req.id),
        'restaurant_id': str(req.restaurant_id),
        'status': sub.status,
        'available_dates': [d.isoformat() for d in days],
        'is_window_open': now_utc < req.closes_at_utc,
        'opens_at_utc': req.opens_at_utc.isoformat(),
        'closes_at_utc': req.closes_at_utc.isoformat(),
    }


# Employee updates his submission
@router.put('/availability/submissions/{submission_id}')
def update_my_submission(
    *,
    submission_id: UUID,
    payload: AvailabilitySubmissionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    '''Replace all availability dates for the current user's submission.

    Editing is allowed only while the request window is open:
    opens_at_utc <= now < closes_at_utc (exclusive close).
    '''
    sub = session.get(AvailabilitySubmission, submission_id)
    # Check if submission exists
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Submission not found'
        )
    # Check if submission belongs to the current user
    if sub.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Submission belongs to another user'
        )
    req = session.get(AvailabilityRequest, sub.request_id)
    # Check if request exists
    if not req:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Availability request not found for submission'
        )
    now_utc = datetime.now(timezone.utc)
    # No edits before open
    if now_utc < req.opens_at_utc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Availability window has not opened yet'
        )
    # Exclusive close: edits allowed only while now < closes_at_utc
    if now_utc >= req.closes_at_utc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Availability window is closed'
        )
    # Validate all dates belong to the target year/month
    for d in payload.available_dates:
        if d.year != req.year or d.month != req.month:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Date {d.isoformat()} is outside requested month' \
                    f'{req.year}-{req.month:02d}'
            )
    # Replace-all: delete than insert
    session.exec(
        delete(AvailabilityDay)
        .where(AvailabilityDay.submission_id == submission_id)
    )
    for d in payload.available_dates:
        session.add(
            AvailabilityDay(submission_id=submission_id, date_local=d)
        )
    sub.status = 'submitted'
    sub.submitted_at_utc = now_utc
    session.add(sub)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        constraint = getattr(
            getattr(e.orig, 'diag', None), 'constraint_name', None
        )
        if constraint == 'ck_availabilitysubmission_status_valid':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid submission status. Allowed values: draft, submitted.'
            )
        if constraint == 'uq_availabilitysubmission_request_user':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Submission already exists for this user and request'
            )
        else: 
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Unable to commit due to a database integrity constraint'
            )

    return {
        'submission_id': str(sub.id),
        'request_id': str(req.id),
        'status': sub.status,
        'submitted_at_utc': sub.submitted_at_utc.isoformat() \
            if sub.submitted_at_utc else None,
        'available_dates': [d.isoformat() for d in payload.available_dates],
    }


# Get availability by day
@router.get('/restaurants/{restaurant_id}/availability/by-day')
def get_availability_by_day(
    *,
    restaurant_id: UUID,
    date_local: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> dict:
    # Require manager permission
    membership = _require_membership(
        session=session,
        restaurant_id=restaurant_id,
        user_id=current_user.id
    )
    _require_manager_permission(membership)
    # Find the monthly request for this reataurant and month
    req = session.exec(
        select(AvailabilityRequest).where(
            AvailabilityRequest.restaurant_id == restaurant_id,
            AvailabilityRequest.year == date_local.year,
            AvailabilityRequest.month == date_local.month,
        )
    ).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Availability request not found for this month'
        )
    # Query all submissions that include this day
    rows = session.exec(
        select(
            User.id,
            User.phone_e164,
            AvailabilitySubmission.id,
            AvailabilitySubmission.status,
            AvailabilitySubmission.submitted_at_utc,
        )
        .select_from(AvailabilityDay)
        .join(
            AvailabilitySubmission,
            AvailabilitySubmission.id == AvailabilityDay.submission_id
        )
        .join(User, User.id == AvailabilitySubmission.user_id)
        .where(AvailabilitySubmission.request_id == req.id)
        .where(AvailabilityDay.date_local == date_local)
    ).all()

    return {
        'restaurant_id': str(restaurant_id),
        'date_local': date_local.isoformat(),
        'request_id': str(req.id),
        'includes_statuses': ['draft', 'submitted'],
        'results': [
            {
                'user_id': str(user_id),
                'phone_e164': phone_e164,
                'submission_id': str(submission_id),
                'status': status_value,
                'submitted_at_utc': submitted_at.isoformat() \
                    if submitted_at else None,
            }
            for (user_id, phone_e164, submission_id, status_value, submitted_at) \
                in rows
        ]
    }