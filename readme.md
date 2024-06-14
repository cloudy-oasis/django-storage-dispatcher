django-storage-dispatcher
=========================

Storage Dispatcher is an app for Django that allows you to dynamically dispatch
a single model to multiple storages at runtime.

Abstract and usage
------------------

Django requires you to know in advance where each instance of a model should be
stored. For example, you might have users, each with a profile picture. Django
needs you to know which storage you would like to use for this model, which
needs to be identical for all images. This app provides a storage class, which
simply dispatches calls to other storages, so that you can give a single
storage to Django, while actually using multiple storages.

This app provides two important classes:

- ``StorageDispatcher``: This is the class mentioned above. It is a storage
  class, which doesn't directly implement the storage API. Instead, it
  dispatches calls to other storages.
- ``StorageResolver``: This is the class used by a ``StorageDispatcher`` to
  know where to map files. When using this package, you will define your own
  resolver, with the logic needed to know which storage to use at runtime.

This app intentionally doesn't define much else: specifically, no *models* are
defined, which also means no changes to your database. It's designed to be as
simple and as seamless as possible.

This app supports all Django versions from 2.2 LTS to 5.0 (the latest stable
release as of writing this).

Configuration
-------------

StorageDispatcher's configuration attempts to mirror Django's configuration as
closely as possible. This means that setting it up should be fast, with very
little configuration diverging from that of Django.

Additionally, this app attempts to keep configuration stable accross Django
versions, meaning that you should not need to make a single change to your
configuration when migrating, even from Django 2.0 to Django 5.0.

When using Django >= 4.2, you only need to configure the ``STORAGES`` variable.
When using older versions, you will need to configure a few other variables,
because Django does not manage storages itself on those versions.

### All versions: the ``STORAGES`` variable ###

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
        "BACKEND": "django_storage_dispatcher.StorageDispatcher",
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

### Writing a resolver ###

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
> Non-deterministic logic, or variable resolution results for the same file,
> can easily result in storage inconsistencies, which can be very harmful to
> your project (files that cannot be found, deleted, etc...). **Double-check
> your resolution logic**, avoid side-effects as much as possible, and raise
> exceptions as rarely as possible, even ``ResolutionError``.

### Additional configuration before Django 4.2 ###

> [!IMPORTANT]
> You still need to configure
> [the ``STORAGES`` variable](<#all-versions-the-storages-variable>).

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
Django >= 4.2, but you can do so, it will not be used anymore.

See [Django's documentation][django-DEFAULTSTORAGE] for more information.

### Additional configuration after Django 4.2 ###

> [!IMPORTANT]
> You still need to configure
> [the ``STORAGES`` variable](<#all-versions-the-storages-variable>).

After Django 4.2, no additional configuration is needed. You don't have to set
a dispatcher as the ``default`` storage.

[django-STORAGES]: https://docs.djangoproject.com/en/5.0/ref/settings/#storages
[django-DEFAULTSTORAGE]: https://docs.djangoproject.com/en/3.2/ref/settings/#std-setting-DEFAULT_FILE_STORAGE
[django-storageapi]: https://docs.djangoproject.com/en/5.0/ref/files/storage/#the-storage-class

