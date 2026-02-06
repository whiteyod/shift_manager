from datetime import date
from fastapi import HTTPException, status
from sqlmodel import Session
from uuid import UUID


from app.models.availability import AvailabilityDay, AvailabilityRequest, \
     AvailabilitySubmission
from app.models.user import User


# --------------------------- Permission API Helpers ---------------------------


def _require_membership(
    *,
    session: Session,
    restaurant_id: UUID,
    user_id: UUID
) -> RestaurantMembership:
    '''Ensure the user belongs to the restaurant.'''
    membership = session.exec(
        select(RestaurantMembership)
        .where(RestaurantMembership.restaurant_id == restaurant_id)
        .where(RestaurantMembership.user_id == user_id)
    ).first()
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail='Not a member of this restaurant'
        )
    
    return membership


def _require_manager_permission(membership: RestaurantMembership) -> None:
    '''Only OWNER/MANAGER can create shifts.'''
    if membership.role not in {RestaurantRole.OWNER, RestaurantRole.MANAGER}:
        raise HTTPException(
            status_code=403,
            detail='Not enough permissions'
        )


# --------------------------- Availability API Helpers --------------------------


def _get_monthly_request_or_404(
    *,
    session: Session,
    restaurant_id: UUID,
    year: int,
    month: int
) -> AvailabilityRequest:
    '''
    Load the monthly AvailabilityRequest for (restaurant_id, year, month).
 
    Raises 404 if it is missing.
    '''
    req = session.exec(
        select(AvailabilityRequest).where(
            AvailabilityRequest.restaurant_id == restaurant_id,
            AvailabilityRequest.year == year,
            AvailabilityRequest.month == month,
        )
    ).first()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Availability request not found for this month'
        )

    return req


def _availability_by_employee_in_rnage(
    *,
    session: Session,
    req: AvailabilityRequest,
    start_date_local: date,
    end_date_local: date
) -> list[dict]:
    '''Return availability grouped by employee for a given request and date range.'''
    rows = session.exec(
        select(
            User.id,
            User.phone_e164,
            AvailabilitySubmission.id,
            AvailabilitySubmission.status,
            AvailabilitySubmission.submitted_at_utc,
            AvailabilityDay.date_local,
        )
        .select_from(AvailabilityDay)
        .join(
            AvailabilitySubmission,
            AvailabilitySubmission.id == AvailabilityDay.submission_id
        )
        .join(User, User.id == AvailabilitySubmission.user_id)
        .where(AvailabilitySubmission.request_id == req.id)
        .where(AvailabilityDay.date_local >= start_date_local)
        .where(AvailabilityDay.date_local <= end_date_local)
    ).all()

    grouped: dict[UUID, dict] = {}

    for user_id, phone_e164, submission_id, status, submitted_at, day in rows:
        if user_id not in grouped:
            grouped[user_id] = {
                'user_id': str(user_id),
                'phone_e164': phone_e164,
                'submission_id': str(submission_id),
                'status': status,
                'submitted_at_utc': submitted_at.isoformat() \
                    if submitted_at else None,
                'available_dates': [],
            }
        grouped[user_id]['available_dates'].append(day.isoformat())

    # Optional sorting
    for item in grouped.values():
        item['available_dates'] = sorted(set(item['available_dates']))

    return list(grouped.values())
        


# ----------------------- Date API Helpers -----------------------


def _utc_native(dt: datetime) -> datetime:
    '''Normalize datetime for DB comparisons.

    Why:
    - DB columns are currently TIMESTAMP WITHOUT TIME ZONE,
      so values may come back as naive.
    - Comparing naive and aware datetimes raises TypeError.
    '''
    if dt.tzinfo is None:
        return dt

    return dt.astimezone(timezone.utc).replace(tzinfo=None)

