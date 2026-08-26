LEAGUE_WINDOW_TITLES = ("League of Legends (TM) Client", "League of Legends")


def is_league_title(title: str) -> bool:
    return title in LEAGUE_WINDOW_TITLES


def should_show(
    in_game: bool, foreground_is_league: bool, dragging: bool, preview_active: bool
) -> bool:
    return preview_active or (in_game and (foreground_is_league or dragging))
