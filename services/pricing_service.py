

"""
Pricing Service
V0038.2A - App.py Segregation

Temporary step:
Functions will be moved here from app.py one-by-one.
After each move, imports in app.py will be updated and smoke-tested.
"""


# def calculate_discounted_fee(*args, **kwargs):
#     """
#     Temporary placeholder.
#     Move the existing calculate_discounted_fee()
#     implementation from app.py into this file in the next step.
#     """
#     raise NotImplementedError(
#         "Move calculate_discounted_fee() implementation from app.py before using this service."
#     )
def calculate_discounted_fee(package, persons, session_count=None):
    """
    Final pricing model for SwimTrackPro.

    Returns:
        int  -> final fee
        0 -> requires trainer discussion / invalid pricing case

    Rules:
    - Maximum 5 persons per booking.
    - Single and Monthly packages use group discounts.
    - Custom package:
        * 3 to 11 sessions  -> sessions × ₹750 × persons
        * 12 to 14 sessions -> ₹9,000 × persons
        * More than 14      -> trainer discussion (None)
    - Group discounts for all package types:
        * 1 person  -> 0%
        * 2 persons -> 6%
        * 3 persons -> 11%
        * 4 persons -> 16%
        * 5 persons -> 21%
    """
    try:
        persons = max(1, int(persons or 1))
    except Exception:
        persons = 1

    # Maximum allowed group size
    if persons > 5:
        return 0

    # Discount rules
    discount_map = {
        1: 0,
        2: 6,
        3: 11,
        4: 16,
        5: 21,
    }

    discount = discount_map.get(persons, 0)

    # Custom package special rules
    if package == 'Custom':
        try:
            session_count = max(int(session_count or 0), 0)
        except Exception:
            session_count = 0

        # More than 14 sessions requires trainer discussion
        if session_count > 14:
            return 0

        # 12 to 14 sessions are capped at monthly equivalent
        if 12 <= session_count <= 14:
            actual_amount = 9000 * persons
        else:
            actual_amount = session_count * 750 * persons

    # Single package
    elif package == 'Single':
        actual_amount = 750 * persons

    # Monthly package
    elif package == 'Monthly':
        try:
            weekly_days = max(int(session_count or 3), 1)
        except Exception:
            weekly_days = 3

        actual_amount = weekly_days * 3000 * persons

    # Fallback
    else:
        actual_amount = 9000 * persons

    final_amount = actual_amount * (100 - discount) / 100

    return round(final_amount)
