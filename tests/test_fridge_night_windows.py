"""The fridge's night windows: a UTC start time, a duration in minutes and
the board's UTC offset, shown as local start and end times. The cabinet
light's schedule and the "Don't make ice at night" window (#599) store the
same shape under different field names."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from custom_components.localthings.registry.capabilities import fridge

FIXTURES = Path(__file__).parent / "fixtures"

# #599's AILITE_REF_25K: 21:00 UTC at +03:00 is midnight, for 360 minutes.
_CABINET = {
    "night.starttime": "2025-09-12T21:00:00",
    "night.duration.minute": "360",
    "timezone.offset": "+03:00",
}


def _desc(capability, key):
    return next(d for d in capability.entities if d.key == key)


class TestCabinetLightSchedule:
    def test_start_and_end_are_local(self):
        cap = fridge.CABINET_LIGHT_ENHANCED
        assert _desc(cap, "night_start").rep_fn(_CABINET) == datetime.time(0, 0)
        assert _desc(cap, "night_end").rep_fn(_CABINET) == datetime.time(6, 0)

    def test_writing_the_start_keeps_the_date_and_stores_utc(self):
        write = _desc(fridge.CABINET_LIGHT_ENHANCED, "night_start").write_fn

        assert write(datetime.time(1, 30), _CABINET) == (
            ["cabinet", "light", "enhanced", "vs", "0"],
            {"night.starttime": "2025-09-12T22:30:00"},
        )

    def test_writing_the_end_stores_the_duration(self):
        write = _desc(fridge.CABINET_LIGHT_ENHANCED, "night_end").write_fn

        assert write(datetime.time(7, 0), _CABINET) == (
            ["cabinet", "light", "enhanced", "vs", "0"],
            {"night.duration.minute": "420"},
        )

    def test_an_end_before_the_start_wraps_past_midnight(self):
        write = _desc(fridge.CABINET_LIGHT_ENHANCED, "night_end").write_fn
        rep = {**_CABINET, "night.starttime": "2025-09-12T19:00:00"}  # 22:00 local

        assert write(datetime.time(6, 0), rep)[1] == {"night.duration.minute": "480"}

    @pytest.mark.parametrize("value", ["N/A", None, ""])
    def test_an_unset_start_reads_unknown_and_takes_no_end(self, value):
        cap = fridge.CABINET_LIGHT_ENHANCED
        rep = {**_CABINET, "night.starttime": value}

        assert _desc(cap, "night_start").rep_fn(rep) is None
        assert _desc(cap, "night_end").rep_fn(rep) is None
        assert _desc(cap, "night_end").write_fn(datetime.time(6, 0), rep) is None

    def test_a_bad_offset_reads_as_utc(self):
        rep = {**_CABINET, "timezone.offset": "local"}

        assert _desc(fridge.CABINET_LIGHT_ENHANCED, "night_start").rep_fn(rep) == (
            datetime.time(21, 0)
        )


# #599's /icemaker/nighttime/vs/0, as read on the reporter's fridge.
_ICE = {
    "ice.night.status": "Off",
    "ice.night.starttime": "2025-09-12T21:00:00",
    "ice.night.duration": "360",
    "ice.night.timezone": "+03:00",
}


class TestIceNightWindow:
    def test_the_window_reads_as_the_app_shows_it(self):
        """12:00 AM - 6:00 AM in the SmartThings app."""
        cap = fridge.ICEMAKER_NIGHTTIME
        assert _desc(cap, "ice_night_start").rep_fn(_ICE) == datetime.time(0, 0)
        assert _desc(cap, "ice_night_end").rep_fn(_ICE) == datetime.time(6, 0)

    def test_writes_go_to_the_icemaker_resource_under_its_own_fields(self):
        cap = fridge.ICEMAKER_NIGHTTIME

        assert _desc(cap, "ice_night_start").write_fn(datetime.time(1, 0), _ICE) == (
            ["icemaker", "nighttime", "vs", "0"],
            {"ice.night.starttime": "2025-09-12T22:00:00"},
        )
        assert _desc(cap, "ice_night_end").write_fn(datetime.time(7, 0), _ICE) == (
            ["icemaker", "nighttime", "vs", "0"],
            {"ice.night.duration": "420"},
        )

    def test_an_unset_window_reads_unknown(self):
        """The #495 fixture's board reports N/A until the window is set."""
        cap = fridge.ICEMAKER_NIGHTTIME
        rep = {**_ICE, "ice.night.starttime": "N/A", "ice.night.duration": "N/A"}

        assert _desc(cap, "ice_night_start").rep_fn(rep) is None
        assert _desc(cap, "ice_night_end").rep_fn(rep) is None

    def test_a_board_without_the_window_gets_only_the_switch(self):
        cap = fridge.ICEMAKER_NIGHTTIME
        rep = {"ice.night.status": "Off"}

        assert not _desc(cap, "ice_night_start").exists_fn(rep, {})
        assert not _desc(cap, "ice_night_end").exists_fn(rep, {})

    def test_the_end_needs_the_start_it_is_worked_out_from(self):
        rep = {"ice.night.status": "Off", "ice.night.duration": "360"}

        assert not _desc(fridge.ICEMAKER_NIGHTTIME, "ice_night_end").exists_fn(rep, {})

    def test_a_stub_at_discovery_keeps_both_entities(self):
        """A warm-tier href can be a bare stub until its first sub-poll."""
        stub = {"href": "/icemaker/nighttime/vs/0"}
        cap = fridge.ICEMAKER_NIGHTTIME

        assert _desc(cap, "ice_night_start").exists_fn(stub, {})
        assert _desc(cap, "ice_night_end").exists_fn(stub, {})

    def test_a_populated_fixture_window_reads_in_its_own_offset(self):
        """The TP1X_REF_21K airfilter dump: 12:00 UTC at +09:00, 540 minutes."""
        rep = json.loads((FIXTURES / "refrigerator_tp1x_ref_21k_airfilter_device.json").read_text())
        ice = next(r["rep"] for r in rep["device0"] if r.get("href") == "/icemaker/nighttime/vs/0")
        cap = fridge.ICEMAKER_NIGHTTIME

        assert _desc(cap, "ice_night_start").rep_fn(ice) == datetime.time(21, 0)
        assert _desc(cap, "ice_night_end").rep_fn(ice) == datetime.time(6, 0)
