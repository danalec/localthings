"""NW9300MD wall combo (issue #525): a microwave cavity over an oven
cavity. The microwave is the master and routes to the microwave registry;
the oven is an indexed subdevice at /device/2 with its own oven entities."""

from custom_components.localthings.registry.by_type import resolve
from custom_components.localthings.registry.discovery import discover
from tests.conftest import _discover_full, _load_device_full

NAME = "microwave_nw9300md"
DEVICE_TYPES = ("oic.wk.d", "oic.d.oven")


def test_every_href_binds():
    """/diagnosis/vs/0 was the one href the microwave registry left
    unbound, which raised the incomplete-coverage repair."""
    resources, _oic_res, _seeds = _load_device_full(NAME)
    reg = resolve(resources, device_types=DEVICE_TYPES)
    assert reg is not None and reg.name == "microwave"
    unbound = []
    discover(resources, reg.capabilities, reg.pattern_capabilities, log=unbound.append)
    assert unbound == []


def test_the_oven_cavity_is_its_own_subdevice():
    resources, oic_res, seeds = _load_device_full(NAME)
    bound, subdevices, skipped, _full, _name = _discover_full(
        resources, oic_res, seeds, DEVICE_TYPES
    )
    assert [s.key for s in subdevices] == ["2"]
    assert skipped == []
    oven_keys = {b.desc.key for b in bound if b.subdevice.key == "2"}
    assert {"oven_mode", "oven_setpoint"} <= oven_keys
