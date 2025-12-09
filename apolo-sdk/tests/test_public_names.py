from yarl import URL

import apolo_sdk


def test_public_version() -> None:
    assert "__version__" in apolo_sdk.__all__


def test_module_for_public_names() -> None:
    for name in apolo_sdk.__all__:
        obj = getattr(apolo_sdk, name)
        if isinstance(obj, URL):
            # Default API url
            continue
        if hasattr(obj, "__module__"):
            assert obj.__module__ in (
                "apolo_sdk",
                # objects from typing are public type hint aliases,
                # e.g. Callable[...]
                "typing",
                # collections.abc are also public type hint aliases,
                # e.g. Sequence[...]
                "collections.abc",
                # We re-export entities from admin client
                "neuro_admin_client.entities",
                # We re-export entities from config client
                "neuro_config_client.entities",
            ), f"{obj}.__module__ == {obj.__module__}, expected apolo_sdk"
