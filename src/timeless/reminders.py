from __future__ import annotations

from datetime import datetime, timedelta


def reminder_fires(
    kind: str,
    modality: str,
    start: datetime,
    submit: datetime | None = None,
    present: datetime | None = None,
) -> list[tuple[str, datetime]]:
    fires: list[tuple[str, datetime]] = []
    if kind == "hackathon":
        fires.append(("start_1d", start - timedelta(days=1)))
        if modality == "virtual":
            fires.append(("start_30m", start - timedelta(minutes=30)))
        else:
            fires.append(("start_2h", start - timedelta(hours=2)))
        if submit:
            fires.append(("submit_4h", submit - timedelta(hours=4)))
        if present:
            fires.append(("present_30m", present - timedelta(minutes=30)))
        return fires
    if modality == "virtual":
        fires.append(("start_30m", start - timedelta(minutes=30)))
        return fires
    fires.append(("start_1d", start - timedelta(days=1)))
    fires.append(("start_2h", start - timedelta(hours=2)))
    return fires
