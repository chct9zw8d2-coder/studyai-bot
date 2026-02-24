
def get_dynamic_free_limit(active_users_today: int) -> int:
    """
    Adjust FREE text limits based on load.
    """
    if active_users_today < 100:
        return 25
    elif active_users_today < 500:
        return 20
    elif active_users_today < 2000:
        return 15
    else:
        return 10
