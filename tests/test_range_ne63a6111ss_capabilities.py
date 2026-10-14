"""NE63A6111SS range (issue #473). Its modeSpec declares Bake as the one
mode a remote may start; the start itself is covered in
test_cook_start.py."""

from custom_components.localthings.registry.adapter import flatten
from custom_components.localthings.registry.by_type import resolve
from custom_components.localthings.registry.discovery import discover
from tests.conftest import _load_device


def _range():
    resources = _load_device("range_ne63a6111ss")
    return resolve(resources), resources


def test_resolves_to_range_registry():
    reg, _ = _range()
    assert reg is not None and reg.name == "range"


def test_no_unbound_hrefs():
    reg, resources = _range()
    unbound = []
    discover(resources, reg.capabilities, reg.pattern_capabilities, log=unbound.append)
    assert unbound == []


def test_keep_warm_reads_as_the_live_mode():
    reg, resources = _range()
    state = flatten(discover(resources, reg.capabilities, reg.pattern_capabilities), resources)
    assert state["oven_mode"] == "KeepWarm"
    assert state["oven_setpoint"] == 175
