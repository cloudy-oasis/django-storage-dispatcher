django-storage-dispatcher
=========================

Storage Dispatcher is a Django application that allows you to dynamically
dispatch a single model field to multiple storages at runtime.

Abstract and usage
------------------

Django requires you to know in advance where each instance of a model field
should be stored. For example, you might have users, each with a profile
picture. Django needs you to know which storage you would like to use for this
image field, which needs to be identical for all images. This app provides a
storage class, which simply dispatches calls to other storages, so that you can
give a single storage to Django, which then dispatches to multiple storages
under the hood.

This app provides two important classes:

- ``StorageDispatcher``: This is the class mentioned above. It is a storage
  class, which doesn't directly implement the storage API. Instead, it
  dispatches calls to other storages.
- ``StorageResolver``: This is the class used by a ``StorageDispatcher`` to
  know where to map files. When using this package, you will define your own
  resolver as part of your configuration, with the logic needed to know which
  storage to use at runtime.

This app intentionally doesn't define much else: specifically, no models or
fields are defined, which also means no changes to your database. It's designed
to be a thin and seamless layer over your own logic.

As of writing this readme, this app supports all Django versions from 2.2 LTS
to 5.1a1.

Configuration
-------------

StorageDispatcher's configuration attempts to mirror Django's configuration as
closely as possible. This means that setting it up should be fast, with very
little configuration diverging from that of Django.

Additionally, this app attempts to keep configuration stable accross Django
versions, meaning that you should not need to make a single change to your
configuration when migrating, even from Django 2.2 to Django 5.0.

There are two main parts to configuring this application:

- [Defining a resolver](<./docs/configuration.md#defining-a-resolver>)
- [Defining your storages](<./docs/configuration.md#the-storages-variable>)

When using Django >= 4.2, you only need to configure the ``STORAGES`` variable.
On older versions, you will also need to cofigure ``DEFAULT_FILE_STORAGE``.
For more details, see the
[configuration documentation](./docs/configuration.md).

