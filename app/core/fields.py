from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class FileSizeTrackingMixin:
    """Keep the byte size of a file in the adjacent `<field>_size` field."""

    is_tracked_file_size = True

    @property
    def size_field_name(self):
        return f"{self.attname}_size"

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        current_size = getattr(model_instance, self.size_field_name, 0) or 0

        if not file:
            size = 0
        elif not getattr(file, "_committed", True):
            size = file.size
        elif add and not current_size:
            try:
                size = file.size
            except (FileNotFoundError, OSError, ValueError):
                size = current_size
        else:
            size = current_size

        setattr(model_instance, self.size_field_name, size)
        if size != current_size or not getattr(file, "_committed", True):
            from app.core.subscription_limits import enforce_storage_limit

            enforce_storage_limit(model_instance, self.size_field_name, size)
        pending_sizes = getattr(model_instance, "_pending_file_sizes", {})
        pending_sizes[self.size_field_name] = size
        model_instance._pending_file_sizes = pending_sizes
        return super().pre_save(model_instance, add)


class TrackedFileField(FileSizeTrackingMixin, models.FileField):
    pass


class TrackedImageField(FileSizeTrackingMixin, models.ImageField):
    pass


@receiver(post_save, weak=False)
def persist_tracked_file_sizes(sender, instance, update_fields=None, **kwargs):
    """Persist sizes when save(update_fields=[file_field]) omitted the size field."""
    instance.__dict__.pop("_pending_storage_delta", None)
    pending_sizes = instance.__dict__.pop("_pending_file_sizes", None)
    if not pending_sizes or update_fields is None:
        return

    missing_size_fields = {
        name: size
        for name, size in pending_sizes.items()
        if name not in update_fields
    }
    if missing_size_fields:
        sender._default_manager.filter(pk=instance.pk).update(**missing_size_fields)


def file_size_field(verbose_name="Rozmiar pliku"):
    return models.PositiveBigIntegerField(
        default=0,
        editable=False,
        verbose_name=verbose_name,
        help_text="Rozmiar zapisany w bajtach.",
    )
