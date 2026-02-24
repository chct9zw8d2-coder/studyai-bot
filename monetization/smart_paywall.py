# compatibility function (used by bot.py)
async def paywall_trigger_count_for_user(conn, user_id: int) -> int:
    """
    Returns how many times paywall was triggered for user.
    Safe fallback implementation.
    """
    try:
        row = await conn.fetchrow(
            "SELECT paywall_count FROM users WHERE user_id=$1",
            user_id
        )
        if row and row["paywall_count"]:
            return int(row["paywall_count"])
    except:
        pass
    return 0
