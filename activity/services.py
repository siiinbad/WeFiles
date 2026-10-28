from .models import ActivityEvent


def record(actor, action, obj):
    return ActivityEvent.objects.create(
        actor=actor,
        action=action,
        object_type=obj._meta.model_name,
        object_id=obj.pk,
        object_label=str(obj)[:255],
    )
