#!/usr/bin/python3

from typing import Any, Dict, Optional

from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.test import SimpleTestCase, override_settings

from storage_dispatcher import (
    ResolutionError,
    StorageDispatcher,
    StorageResolver,
)


class TestResolver(StorageResolver):
    def resolve(
        self,
        storages,
        method: Optional[str],
        filename: Optional[str],
        params: Dict[str, Any],
    ) -> Optional[str]:
        if filename is None:
            return None

        if filename[0] in ["A", "B"]:
            return filename[0]

        if filename.startswith("default"):
            return "default"

        return None


storages_variable = {
    "default": {
        "BACKEND": "storage_dispatcher.StorageDispatcher",
        "OPTIONS": {
            "resolver": TestResolver(),
        },
    },
    "A": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "./A",
        },
    },
    "B": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "./B",
        },
    },
    "fallback": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "./fallback",
        },
    },
}


default_file_storage = "storage_dispatcher.StorageDispatcher"


@override_settings(
    STORAGES=storages_variable,
    DEFAULT_FILE_STORAGE=default_file_storage,
)
class StorageDispatcherTest(SimpleTestCase):
    def setUp(self) -> None:
        self.storage = DefaultStorage()

    def test_settings(self) -> None:
        """
        Make sure that settings are correctly applied.
        """
        self.assertEqual(getattr(settings, "STORAGES"), storages_variable)

    def test_default_storage(self) -> None:
        self.assertIsInstance(self.storage, StorageDispatcher)

    def test_django_managed(self) -> None:
        """
        Make sure the dispatcher understands it should manage storages.
        """
        self.assertTrue(self.storage.self_managed)

    def test_valid_dispatch(self) -> None:
        """
        Make sure that storages are correctly dispatched to.
        """
        self.assertIs(
            self.storage.resolve(None, "A", {}),
            self.storage._storages()["A"],
        )
        self.assertIs(
            self.storage.resolve(None, "Abcdef", {}),
            self.storage._storages()["A"],
        )
        self.assertIs(
            self.storage.resolve(None, "B", {}),
            self.storage._storages()["B"],
        )

    def test_fallback_dispatch(self) -> None:
        """
        Make sure that the fallback storage is correctly dispatched to.
        """
        self.assertIs(
            self.storage.resolve(None, "fallback", {}),
            self.storage._storages()["fallback"],
        )
        self.assertIs(
            self.storage.resolve(None, " B", {}),
            self.storage._storages()["fallback"],
        )
        self.assertIs(
            self.storage.resolve(None, "C", {}),
            self.storage._storages()["fallback"],
        )

    def test_default_dispatch_fails(self) -> None:
        """
        Make sure that dispatching to the default storage fails.
        """
        self.assertRaises(
            ResolutionError, self.storage.resolve, None, "default", {}
        )
