from datetime import date


def season_from_date(game_date: date) -> str:
    """Return a season label like '2024-25' from a game date.

    NBA season spans October through June of the following year.
    Oct–Dec: belongs to the season starting that year  (Oct 2024 → '2024-25')
    Jan–Sep: belongs to the season starting the prior year (Jan 2025 → '2024-25')
    """
    if game_date.month >= 10:
        start = game_date.year
    else:
        start = game_date.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def season_date_range(season: str) -> tuple[date, date]:
    """Return (start_date, end_date) for a season label like '2024-25'.

    NBA regular season runs Oct 1 – Jun 30 of the following calendar year.
    """
    start_year = int(season.split("-")[0])
    return date(start_year, 10, 1), date(start_year + 1, 6, 30)


def prior_season(season: str) -> str:
    """Return the season label one year before the given season ('2024-25' → '2023-24')."""
    start_year = int(season.split("-")[0])
    prior = start_year - 1
    return f"{prior}-{str(start_year)[-2:]}"
