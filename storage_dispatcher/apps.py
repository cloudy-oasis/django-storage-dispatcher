from django.apps import AppConfig


class StorageDispatcherConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_storage_dispatcher"
    verbose_name = "Django Storage Dispatcher"
    label = "storage_dispatcher"
