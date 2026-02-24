
def should_reduce_limits(api_cost_today: float, revenue_today: float) -> bool:
    """
    If costs approach revenue, tighten FREE limits.
    """
    if revenue_today == 0:
        return True
    ratio = api_cost_today / revenue_today
    return ratio > 0.6
