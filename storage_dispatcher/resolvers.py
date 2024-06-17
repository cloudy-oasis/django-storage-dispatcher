from typing import Any, Dict, Optional

from django.core.exceptions import ImproperlyConfigured


__all__ = [
    "ExtensionResolver",
    "ResolutionError",
    "StorageResolver",
]


class ResolutionError(ImproperlyConfigured):
    """
    An exception relating to a storage resolver or resolution of a
    storage. Because the resolver is considered to be part of your
    configuration, this is considered a configuration error.
    """

    pass


class _NoResolutionError(ImproperlyConfigured):
    """
    An internal exception used to detect a missing resolver. Do
    not use this exception. You do not need to check for this
    exception.
    """

    pass


class StorageResolver:
    """
    Base storage resolver class, inherit this class to create your
    own. You only need to redefine resolve().
    """

    def resolve(
        self,
        storages,
        method: Optional[str],
        filename: Optional[str],
        params: Dict[str, Any],
    ) -> Optional[str]:
        """
        Resolve a storage from given arguments. This is the only
        function you have to redefine in order to write a resolver.
        """
        raise ResolutionError("Storage resolvers must implement resolve()")

    def __call__(
        self,
        storages,
        method: Optional[str],
        filename: str,
        params: Dict[str, Any],
    ) -> Optional[str]:
        """
        Call this class's resolve function. You may redefine this
        function if you would like to implement calling logic outside
        of resolve(), but it usually isn't needed.
        """
        return self.resolve(storages, method, filename, params)


class ExtensionResolver(StorageResolver):
    """
    A stateless resolver that matches storages based on extensions in
    their alias. For example, with filename == "hello.py", this would
    match the following storages: "py", "py|txt|cpp", "py|"; but would
    not match the following: "txt|", "p|y". Storage aliases including
    dots will never match any files. Files that don't include any dots
    will match storages with an empty component (e.g., "|py", "").

    You probably won't want to use this resolver in your code, as you
    should be using project-specific logic instead; it's intended to be
    an example, for educational and test purposes.
    """

    def resolve(
        self,
        storages,
        method: Optional[str],
        filename: Optional[str],
        params: Dict[str, Any],
        delimiter: str = "|",
    ) -> Optional[str]:
        """
        Resolve based on the filename given, ignoring all arguments
        other than this and storages. Returns None if no storages
        matched the file's extension or if no filename was given.
        """
        if filename is None:
            return None

        _, _, extension = filename.rpartition(".")
        for storage in storages:
            if extension in storage.split("|"):
                return storage
        return None
