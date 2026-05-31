from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import math


def datetime2color(dt: datetime | None = None) -> tuple[int, int, int]:
	"""
	Return an RGB color for a Bluetooth speaker based on:
	- Traditional Chinese seasonal cycle, approximated with solar-term season starts
	- Time of day, smoothly blended across dawn/day/sunset/night

	Assumptions:
	- China timezone is Asia/Shanghai.
	- If dt is None, the current China local datetime is used.
	- If dt is naive, it is interpreted as China local time.
	"""

	china_tz = ZoneInfo("Asia/Shanghai")

	if dt is None:
		dt = datetime.now(china_tz)
	elif dt.tzinfo is None:
		dt = dt.replace(tzinfo=china_tz)
	else:
		dt = dt.astimezone(china_tz)

	year = dt.year

	season_anchors = [
		(_day_of_year_float(datetime(year, 2, 4, tzinfo=china_tz)),  (70, 220, 150)),
		(_day_of_year_float(datetime(year, 5, 5, tzinfo=china_tz)),  (255, 95, 45)),
		(_day_of_year_float(datetime(year, 8, 7, tzinfo=china_tz)),  (255, 210, 120)),
		(_day_of_year_float(datetime(year, 11, 7, tzinfo=china_tz)), (55, 80, 170)),
	]

	season_color = _cyclic_blend_by_year(dt, season_anchors)

	hour = dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3_600_000_000

	time_anchors = [
		(0.0,  (20, 25, 70)),
		(5.5,  (255, 145, 95)),
		(12.0, (255, 255, 235)),
		(18.5, (255, 105, 45)),
		(22.0, (80, 60, 150)),
	]

	time_tint = _cyclic_blend(hour, 24.0, time_anchors)

	brightness = 0.55 + 0.45 * max(0.0, math.sin(math.pi * hour / 24.0))
	if hour < 5 or hour > 22:
		brightness *= 0.65

	mixed = _mix_rgb(season_color, time_tint, 0.35)

	return tuple(
		max(0, min(255, round(channel * brightness)))
		for channel in mixed
	)


def _day_of_year_float(dt: datetime) -> float:
	start = datetime(dt.year, 1, 1, tzinfo=dt.tzinfo)
	return (dt - start).total_seconds() / 86400.0


def _cyclic_blend_by_year(
	dt: datetime,
	anchors: list[tuple[float, tuple[int, int, int]]]
) -> tuple[float, float, float]:
	days_in_year = 366.0 if _is_leap_year(dt.year) else 365.0
	x = _day_of_year_float(dt)
	return _cyclic_blend(x, days_in_year, anchors)


def _cyclic_blend(
	x: float,
	period: float,
	anchors: list[tuple[float, tuple[int, int, int]]]
) -> tuple[float, float, float]:
	anchors = sorted(anchors, key=lambda item: item[0])
	x = x % period

	for i, (a_pos, a_color) in enumerate(anchors):
		b_pos, b_color = anchors[(i + 1) % len(anchors)]

		if i == len(anchors) - 1:
			b_pos += period
			x_check = x if x >= a_pos else x + period
		else:
			x_check = x

		if a_pos <= x_check <= b_pos:
			t = (x_check - a_pos) / (b_pos - a_pos)
			t = _smoothstep(t)
			return _mix_rgb(a_color, b_color, t)

	return tuple(float(c) for c in anchors[0][1])


def _smoothstep(t: float) -> float:
	t = max(0.0, min(1.0, t))
	return t * t * (3.0 - 2.0 * t)


def _mix_rgb(
	a: tuple[int | float, int | float, int | float],
	b: tuple[int | float, int | float, int | float],
	t: float
) -> tuple[float, float, float]:
	return tuple(a[i] * (1.0 - t) + b[i] * t for i in range(3))


def _is_leap_year(year: int) -> bool:
	return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)