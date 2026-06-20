from __future__ import annotations

from dataclasses import dataclass


TIME_PERIODS = ("Morning", "Afternoon", "Evening", "Night")
SEASONS = ("Thaw", "Emberwake", "Gloamfall", "Frostwane")
DAYS_PER_SEASON = 30
DAYS_PER_YEAR = DAYS_PER_SEASON * len(SEASONS)
CAMPAIGN_START_YEAR = 1000


@dataclass(frozen=True)
class CalendarDate:
    absolute_day: int
    year: int
    season: str
    day_of_season: int
    time_period: str

    def short_label(self) -> str:
        return f"Year {self.year}, {self.season} {self.day_of_season}"

    def full_label(self) -> str:
        return f"{self.short_label()}, {self.time_period}"


def calendar_date(day: int, time_period: str) -> CalendarDate:
    safe_day = max(1, int(day))
    safe_period = time_period if time_period in TIME_PERIODS else TIME_PERIODS[0]
    day_index = safe_day - 1
    year = CAMPAIGN_START_YEAR + (day_index // DAYS_PER_YEAR)
    season_index = (day_index % DAYS_PER_YEAR) // DAYS_PER_SEASON
    day_of_season = (day_index % DAYS_PER_SEASON) + 1
    return CalendarDate(
        absolute_day=safe_day,
        year=year,
        season=SEASONS[season_index],
        day_of_season=day_of_season,
        time_period=safe_period,
    )


def format_calendar(day: int, time_period: str) -> str:
    return calendar_date(day, time_period).full_label()


def format_timeline_prefix(player) -> str:
    return (
        f"Day {player.day}, {player.time_period} "
        f"({format_calendar(player.day, player.time_period)})"
    )


def append_timeline_entry(player, message: str, **timeline_kwargs) -> str:
    entry = f"{format_timeline_prefix(player)} - {message}"
    player.action_log.append(entry)
    player.event_log.append(entry)
    from app.timeline import add_timeline_entry

    add_timeline_entry(player, message, **timeline_kwargs)
    return entry


def age_band(age_years: int) -> str:
    if age_years < 25:
        return "Young Adult"
    if age_years < 40:
        return "Adult"
    if age_years < 60:
        return "Seasoned"
    if age_years < 80:
        return "Elder"
    return "Ancient"


def advance_time(player, periods: int = 1) -> None:
    if periods <= 0:
        return
    if player.time_period not in TIME_PERIODS:
        player.time_period = TIME_PERIODS[0]
    for _ in range(periods):
        index = TIME_PERIODS.index(player.time_period)
        if index == len(TIME_PERIODS) - 1:
            player.day += 1
            player.time_period = TIME_PERIODS[0]
            _advance_campaign_day(player)
        else:
            player.time_period = TIME_PERIODS[index + 1]
        player.turns_elapsed += 1


def advance_days(player, days: int = 1) -> None:
    if days <= 0:
        return
    advance_time(player, periods=days * len(TIME_PERIODS))


def _advance_campaign_day(player) -> None:
    player.age_days_accumulated += 1
    if player.character is None:
        return
    while player.age_days_accumulated >= DAYS_PER_YEAR:
        player.age_days_accumulated -= DAYS_PER_YEAR
        player.character.age_years += 1
