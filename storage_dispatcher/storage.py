from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from django import get_version
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .resolvers import (
    ResolutionError,
    StorageResolver,
    _NoResolutionError,
    _NoResolver,
)


__all__ = [
    "StorageDispatcher",
    "is_self_managed",
]


def is_self_managed() -> bool:
    """
    We manage our own storage on Django < 4.2
    """
    version = get_version().split(".")

    if int(version[0]) < 4:
        return True
    if int(version[0]) > 4:
        return False

    return int(version[1]) < 2


# Storage backend key in the Django STORAGES variable.
_BACKEND = "BACKEND"

# Storage options key in the Django STORAGES variable.
_OPTIONS = "OPTIONS"

# Default storage key in the Django STORAGES variable.
_DEFAULT = "default"

# Fallback storage alias.
_FALLBACK = "fallback"

# Storages key in a dispatcher's options.
_STORAGES = "storages"

# Resolver key in a dispatcher's options.
_RESOLVER = "resolver"


@deconstructible
class StorageDispatcher(Storage):
    """
    A Storage class that does not implement the API itself, but uses a
    StorageResolver to dispatch calls to storages that do. It may be
    useful if you have models that are stored on multiple storages,
    and you don't know where in advance.

    This class does not implement the Storage API itself and still
    requires your storages to do so. Additionally, it requires a
    resolver to determine which storage you'd like to use when calling
    the storage API with this class (see the resolver documentation
    for details).

    This class uses almost the same configuration as Django, and will
    manage your storages if you're using Django < 4.2, refer to the
    documentation for details.
    """

    def __init__(
        self,
        storages: Dict[str, Dict[str, Union[str, Dict[Any, Any]]]] = {},
        resolver: StorageResolver = _NoResolver(),
    ) -> None:
        """
        Because we won't be passed any arguments on Django < 4.2, this
        is just a wrapper around the _init() function, which will
        actually handle initialisation.

        :param storages: The storages this class uses.
        :param resolver: The resolver used by this class. If this is
            _NoResolver, then this function assumes it has been called
            without arguments (typically on Django < 4.2) and defers
            initialisation.
        """
        self.is_init = False
        if not isinstance(resolver, _NoResolver):
            self._init(storages, resolver)

    def _init(
        self,
        storages: Dict[str, Dict[str, Union[str, Dict[Any, Any]]]],
        resolver: StorageResolver,
    ) -> None:
        """
        Actual initialisation function. This is separate from __init__,
        because initialisation may be deferred if storages can't be
        obtained when this class is constructed.

        :param storages: Storages mapped to by this dispatcher.
        :param resolver: The resolver used by this dispatcher.
        """
        if self.is_init:
            raise RuntimeError(
                "_init called but storage is already initialised"
            )

        if isinstance(resolver, _NoResolver):
            raise RuntimeError("Cannot set this resolver to a _NoResolver")

        if isinstance(getattr(self, "_resolver", _NoResolver()), _NoResolver):
            self._resolver = resolver
        if not isinstance(resolver, StorageResolver):
            raise ImproperlyConfigured(
                "Resolver should derive StorageResolver, but is "
                f"{type(resolver)}"
            )

        if self.self_managed:
            self._init_storages(storages)
        self.is_init = True

    def _init_storages(
        self, storages: Dict[str, Dict[str, Union[str, Dict[Any, Any]]]]
    ) -> None:
        """
        Initialise this dispatcher's storages. Meant to be called by
        _init().

        :param storages: Storages mapped to by this dispatcher.
        """

        if self.is_init:
            raise RuntimeError(
                "_init_storages called but storage is already initialised"
            )
        if not self.self_managed:
            raise RuntimeError(
                "_init_storages called but storage is not self-managed"
            )
        self.is_init = True

        self._managed_storages: Dict[str, Storage] = {}
        storages = storages or getattr(settings, "STORAGES")
        for i in filter(lambda x: x != _DEFAULT, storages):
            self._init_storage(
                i,
                # we know what types these dict keys are, even if
                # mypy doesn't
                storages[i][_BACKEND],  # type: ignore
                storages[i].get(_OPTIONS, {}),  # type: ignore
            )

    def __repr__(self) -> str:
        """
        A fancier and more detailed representation, especially for
        debugging.

        :return: A string like:
        <StorageDispatcher: resolver MyResolver, 5 storages (self-managed)>
        """

        def to_str(x: Any) -> str:
            """
            A shorter and easily readable representation.
            """
            # if x uses the default __repr__ function, use its name instead
            # (so that it is shorter and more readable)
            if x.__repr__ is object.__repr__:
                return x.__class__.__qualname__
            return repr(x).strip("<>")

        if self.self_managed:
            managed_str = "(self-managed)"
        else:
            managed_str = "(externally managed)"

        return (
            f"<{self.__class__.__qualname__}: resolver "
            f"{to_str(self._resolver)}, {len(self._storages())} storages "
            f"({managed_str})>"
        )

    def _init_storage(
        self,
        alias: str,
        backend: str,
        options: dict = {},
    ) -> None:
        """
        Initialise a storage.

        :param alias: Storage alias, i.e. the "name" of the storage
        :param backend: Storage backend, class used as the storage
        :param options: Storage options, passed to the backend
        """
        if not self.self_managed:
            raise RuntimeError(
                "_init_storage was called but storage is not self-managed"
            )
        try:
            self._storages()[alias] = self._import_storage(backend)(**options)
            return self._storages()[alias]
        except ImportError as e:
            raise ImproperlyConfigured(
                f"Could not import storage {backend} (alias) from your "
                "configuration."
            ) from e

    def _import_storage(self, name: str) -> type:
        """
        Import a storage class.

        :param name: Dotted name to the class to import, e.g.,
            django.core.files.storage.Storage
        :return: The imported type
        """
        if not self.self_managed:
            raise RuntimeError(
                "_import_storage was called but storage is not self-managed"
            )
        return import_string(name)

    @cached_property
    def self_managed(self) -> bool:
        """
        Django 4.2 introduces the STORAGES setting. Therefore, as of
        this version, we let Django manage storages itself.
        """
        return is_self_managed()

    def _storages(self):
        """
        This class's storages. This is a stable part of the API, but
        isn't meant to be used directly: you should either resolve
        your storage, or access Django's storages directly (if you're
        on Django >= 4.2).
        """
        # initialisation was deferred: check for options ourselves
        # in the configuration
        if not self.is_init:
            storages = getattr(settings, "STORAGES")
            self._init(
                storages,
                storages[_DEFAULT][_OPTIONS][_RESOLVER],
            )
        if self.self_managed:
            return self._managed_storages
        else:
            from django.core.files.storage import storages

            return storages

    def resolve(
        self,
        method: Optional[str],
        filename: Optional[str],
        params: Dict[str, Any],
    ) -> Storage:
        """
        Resolve a storage from given arguments, using this class's
        resolver.

        :param method: The method called when attempting resolving
        :param filename: The file on which the operation acts (if
            applicable)
        :param params: The arguments passed to the method, as is
        :return: The corresponding storage
        """
        if not self.is_init:
            storages = getattr(settings, "STORAGES")
            self._init(
                storages,
                storages[_DEFAULT][_OPTIONS][_RESOLVER],
            )
        try:
            alias = self._resolver(self._storages(), method, filename, params)
        except ResolutionError:
            alias = None
        except _NoResolutionError as e:
            raise ResolutionError from e
        if alias == _DEFAULT:
            raise ResolutionError(
                "Cannot use default storage: this is the default storage. "
                f"Your resolver should never return {_DEFAULT}."
            )
        try:
            return self._storages()[alias if alias is not None else _FALLBACK]
        # Ideally, we should only be catching KeyError and
        # InvalidStorageError; however, the latter doesn't exist on
        # Django < 4.2, so we catch the closest possible one instead.
        except (KeyError, ImproperlyConfigured) as e:
            try:
                return self._storages()[_FALLBACK]
            except (KeyError, ImproperlyConfigured):
                raise ResolutionError(
                    f'No matching storage found (tried "{alias}" and '
                    f'"{_FALLBACK}").'
                ) from e

    def delete(self, name: str) -> None:
        """
        Dispatch a call to delete() to the right storage.
        """
        return self.resolve(
            method="delete", filename=name, params={"name": name}
        ).delete(name)

    def exists(self, name: str) -> bool:
        """
        Dispatch a call to exists() to the right storage.

        :param name: The file on which the operation acts
        :return: True if the file exists, False otherwise
        """
        return self.resolve(
            method="exists", filename=name, params={"name": name}
        ).exists(name)

    def get_accessed_time(self, name: str) -> datetime:
        """
        Dispatch a call to get_accessed_time() to the right storage.

        :param name: The file on which the operation acts
        :return: The last access time
        """
        return self.resolve(
            method="get_accessed_time", filename=name, params={"name": name}
        ).get_accessed_time(name)

    def get_alternative_name(self, file_root: str, file_ext: str) -> str:
        """
        Dispatch a call to get_alternative_name() to the right storage.
        Passes {file_root}.{file_ext} as the filename to the resolver.

        :param file_root: The root of the filename
        :param file_ext: The extension of the filename
        :return: An alternative filename
        """
        return self.resolve(
            method="get_alternative_name",
            filename=f"{file_root}.{file_ext}",
            params={"file_root": file_root, "file_ext": file_ext},
        ).get_alternative_name(file_root, file_ext)

    def get_available_name(self, max_length: Optional[int] = None) -> str:
        """
        Dispatch a call to get_available_name() to the right storage.
        Passes no filename to the resolver.

        :param max_length: the max length of the filename
        :return: An available name
        """
        return self.resolve(
            method="get_available_name",
            filename=None,
            params={"max_length": max_length},
        ).get_available_name(max_length)

    def get_created_time(self, name: str) -> datetime:
        """
        Dispatch a call to get_created_time() to the right storage.

        :param name: The file on which the operation acts
        :return: The creation time
        """
        return self.resolve(
            method="get_created_time", filename=name, params={"name": name}
        ).get_created_time(name)

    def get_modified_time(self, name: str) -> datetime:
        """
        Dispatch a call to get_modified_time() to the right storage.

        :param name: The file on which the operation acts
        :return: The modification time
        """
        return self.resolve(
            method="get_modified_time", filename=name, params={"name": name}
        ).get_modified_time(name)

    def get_valid_name(self, name: str) -> str:
        """
        Dispatch a call to get_valid_name() to the right storage.

        :param name: The file on which the operation acts
        :return: A valid name
        """
        return self.resolve(
            method="get_valid_name", filename=name, params={"name": name}
        ).get_valid_name(name)

    def generate_filename(self, filename: str) -> str:
        """
        Dispatch a call to generate_filename() to the right storage.

        :param filename: The file on which the operation acts
        :return: The generated filename
        """
        return self.resolve(
            method="generate_filename",
            filename=filename,
            params={"filename": filename},
        ).generate_filename(filename)

    def listdir(self, path: str) -> Tuple[List[str], List[str]]:
        """
        Dispatch a call to listdir() to the right storage.

        :param name: The directory on which the operation acts
        :return: The directory contents
        """
        return self.resolve(
            method="listdir", filename=path, params={"path": path}
        ).listdir(path)

    def open(self, name: str, mode: str = "rb") -> File:
        """
        Dispatch a call to open() to the right storage.

        :param name: The file on which the operation acts
        :param mode: Access mode (binary read mode by default)
        :return: The file contents
        """
        return self.resolve(
            method="open", filename=name, params={"name": name, "mode": mode}
        ).open(name, mode)

    def path(self, name: str) -> str:
        """
        Dispatch a call to path() to the right storage.

        :param name: The file on which the operation acts
        :return: The path usable by Python's open(), if one exists
        """
        return self.resolve(
            method="path", filename=name, params={"name": name}
        ).path(name)

    def save(
        self, name: str, content: File, max_length: Optional[int] = None
    ) -> str:
        """
        Dispatch a call to save() to the right storage.

        :param name: The file on which the operation acts
        :param content: The contents of the file
        :param max_length: The maximum length of the file
        :return: A path to the file
        """
        return self.resolve(
            method="save",
            filename=name,
            params={
                "name": name,
                "content": content,
                "max_length": max_length,
            },
        ).save(name, content, max_length)

    def size(self, name: str) -> int:
        """
        Dispatch a call to size() to the right storage.

        :param name: The file on which the operation acts
        :return: The size of the file
        """
        return self.resolve(
            method="size", filename=name, params={"name": name}
        ).size(name)

    def url(self, name: str) -> str:
        """
        Dispatch a call to url() to the right storage.

        :param name: The file on which the operation acts
        :return: A URL that accesses the file
        """
        return self.resolve(
            method="url", filename=name, params={"name": name}
        ).url(name)
