from collections.abc import Sized


class DisabledLength:
    __len__ = None


class EnabledLength:
    def __len__(self):
        return 3


results = {
    "disabled_has_attribute": hasattr(DisabledLength(), "__len__"),
    "disabled_sized_protocol": isinstance(DisabledLength(), Sized),
    "enabled_has_attribute": hasattr(EnabledLength(), "__len__"),
    "enabled_sized_protocol": isinstance(EnabledLength(), Sized),
}
