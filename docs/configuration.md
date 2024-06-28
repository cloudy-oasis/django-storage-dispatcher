Configuration
=============

There are two main parts to configuring this application:
[configuring your storages](<#the-storages-variable>) using the ``STORAGES``
variable, and [defining your resolver](<#defining-a-resolver>).
Additionally, on Django < 4.2, you need to set a dispatcher as your default
storage.

The ``STORAGES`` variable
-------------------------

> [!IMPORTANT]
> This variable is required, no matter which Django version you're using.

StorageDispatcher uses the same ``STORAGES`` variable as Django, configured the
same way. It's a dictionary mapping *storage aliases* ("names") to the
following:

- their *backend*: an import path to their class (required);
- their *options*: kwargs, passed to the class as is (optional).

Three default aliases are reserved by Django and StorageDispatcher:
``default``, ``staticfiles``, and ``fallback``. Django reserves the first two,
while StorageDispatcher reserves the last one.

For example, here is a simple configuration:

```python
STORAGES = {
    # StorageDispatcher is set as the default storage.
    "default": {
        "BACKEND": "storage_dispatcher.StorageDispatcher",
        "OPTIONS": {
            # NoneResolver is defined in another example. It always
            # returns None.
            "resolver": NoneResolver(),
        },
    },
    # this is the default static file storage in testing environments
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFileStorage",
    },
    # this is the fallback storage, and also the only storage used
    # (since no other storages are specified)
    "fallback": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
```

This one isn't very useful, because it maps everything to the fallback storage.
In your own configuration, you'd specify multiple storages, as well as a
smarter resolver.

> [!TIP]
> On Django >= 4.2, you can set another storage as the ``default`` storage. If
> you would like to do so, refer to the
> [relevant section](<#additional-configuration-after-django-42>).

Defining a resolver
-------------------

A resolver is a class called whenever a storage API call is performed, in order
to know which storage it should operate on. When called, it can either return a
storage *alias* (a string), or None to use the fallback storage. Here is a
simple resolver, that always returns None:

```python
class NoneResolver(StorageResolver):
    def __init__(self) -> None:
        """
        You'll often want to redefine this function, in order to pass
        some state to your resolver (e.g., available storages), but
        it's not required.
        """
        pass

    def resolve(
        self,
        storages,
        method: Optional[str],
        filename: Optional[str],
        params: Dict[str, Any],
    ) -> Optional[str]:
        """
        This function will be called on each API call.
        """
        return None
```

That's it! You can also redefine the ``__call__()`` function if you want to,
but it's typically not needed.

A resolver can raise a ``ResolutionError`` if resolution failed, in which case
it will be caught and the fallback storage will be used. However, remember that
it is an *exception*: keep it for *exceptional* cases. No other exceptions will
be caught, **do not throw them**.

> [!CAUTION]
> Non-deterministic logic, or inconsistent variable resolution results for the
> same file, can easily result in storage inconsistencies, which can be very
> harmful to your project (files that cannot be found, deleted, etc...).
> **Double-check your resolution logic**, avoid side-effects as much as
> possible, and try not to raise exceptions, even ``ResolutionError``.

### Additional configuration before Django 4.2 ###

> [!IMPORTANT]
> You still need to configure
> [the ``STORAGES`` variable](<#the-storages-variable>).

Before 4.2, Django does not read the STORAGES variable. Therefore, in order to
initialise your dispatcher, you *also* need to specify the following in your
settings:

```python
DEFAULT_FILE_STORAGE = "django_storage_dispatcher.StorageDispatcher"
```

This StorageDispatcher will then read the STORAGES variable and use it to
initialise storages. It will read its parameters from the ``default`` storage,
therefore it needs to be the ``default`` storage.

You do not need to remove ``DEFAULT_FILE_STORAGE`` when migrating to
Django >= 4.2, but you can do so, as it will not be used anymore.

See [Django's documentation][django-DEFAULTSTORAGE] for more information.

### Additional configuration after Django 4.2 ###

After Django 4.2, no additional configuration is needed. You don't have to set
a dispatcher as the ``default`` storage.

[django-DEFAULTSTORAGE]: <https://docs.djangoproject.com/en/3.2/ref/settings/#std-setting-DEFAULT_FILE_STORAGE>

