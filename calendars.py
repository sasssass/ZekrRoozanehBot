"""Calendar conversions used to look up the occasions of a given day.

Kept dependency-free on purpose: `send_daily_zekr.py` runs on a bare GitHub
Actions runner with no `pip install` step, so everything here is stdlib only.
"""

import os
from datetime import date


# The tabular (arithmetical) Hijri calendar can land a day off the calendar a
# given community follows, because the real one waits for the new moon to be
# seen. Set HIJRI_OFFSET_DAYS=1 or -1 to nudge every lunar date at once.
HIJRI_OFFSET_DAYS = int(os.environ.get("HIJRI_OFFSET_DAYS", "0"))

HIJRI_MONTHS = (
    "محرم",
    "صفر",
    "ربیع‌الاول",
    "ربیع‌الثانی",
    "جمادی‌الاول",
    "جمادی‌الثانی",
    "رجب",
    "شعبان",
    "رمضان",
    "شوال",
    "ذی‌القعده",
    "ذی‌الحجه",
)

JALALI_MONTHS = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)


def gregorian_to_jdn(day: date) -> int:
    """Julian day number, the common ground between the three calendars."""
    a = (14 - day.month) // 12
    year = day.year + 4800 - a
    month = day.month + 12 * a - 3
    return (
        day.day
        + (153 * month + 2) // 5
        + 365 * year
        + year // 4
        - year // 100
        + year // 400
        - 32045
    )


def gregorian_to_hijri(day: date) -> tuple[int, int, int]:
    """Convert to the tabular Hijri calendar, shifted by HIJRI_OFFSET_DAYS."""
    left = gregorian_to_jdn(day) - HIJRI_OFFSET_DAYS - 1948440 + 10632
    cycles = (left - 1) // 10631
    left = left - 10631 * cycles + 354
    year_in_cycle = ((10985 - left) // 5316) * ((50 * left) // 17719) + (left // 5670) * (
        (43 * left) // 15238
    )
    left = (
        left
        - ((30 - year_in_cycle) // 15) * (17719 * year_in_cycle // 50)
        - (year_in_cycle // 16) * (15238 * year_in_cycle // 43)
        + 29
    )
    month = (24 * left) // 709
    return 30 * cycles + year_in_cycle - 30, month, left - (709 * month) // 24


def gregorian_to_jalali(day: date) -> tuple[int, int, int]:
    """Convert to the Persian solar calendar. This one is exact."""
    months_before = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    years = day.year - 1600
    day_number = (
        365 * years
        + (years + 3) // 4
        - (years + 99) // 100
        + (years + 399) // 400
        + months_before[day.month - 1]
        + day.day
        - 1
    )
    if day.month > 2 and (day.year % 4 == 0 and day.year % 100 != 0 or day.year % 400 == 0):
        day_number += 1

    day_number -= 79  # 1 Farvardin 979 AP == 21 March 1600 CE
    cycles = day_number // 12053  # one 33-year cycle
    day_number %= 12053
    year = 979 + 33 * cycles + 4 * (day_number // 1461)
    day_number %= 1461
    if day_number >= 366:
        year += (day_number - 1) // 365
        day_number = (day_number - 1) % 365

    if day_number < 186:
        return year, day_number // 31 + 1, day_number % 31 + 1

    day_number -= 186
    return year, day_number // 30 + 7, day_number % 30 + 1
