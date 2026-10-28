from django.db import migrations


def assign_existing_avatars(apps, schema_editor):
    """Assign a stable, varied icon to accounts that predate the avatar picker."""
    User = apps.get_model("accounts", "User")
    # Freeze this migration's catalog; later catalog edits must not change it.
    icons = (
        "avatar-smile", "avatar-cat", "avatar-fox", "avatar-bear",
        "avatar-panda", "avatar-rabbit", "avatar-owl", "avatar-frog",
        "avatar-penguin", "avatar-koala", "avatar-bot", "avatar-astronaut",
        "avatar-ghost", "avatar-ninja", "avatar-dino", "avatar-whale",
        "avatar-rocket", "avatar-planet", "avatar-moon", "avatar-sun",
        "avatar-leaf", "avatar-mountain", "avatar-crown", "avatar-bolt",
    )
    for user in User.objects.using(schema_editor.connection.alias).only("pk").iterator():
        User.objects.using(schema_editor.connection.alias).filter(pk=user.pk).update(
            avatar_icon=icons[user.pk.int % len(icons)]
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_avatar_icon_user_valid_user_avatar")]
    operations = [migrations.RunPython(assign_existing_avatars, migrations.RunPython.noop)]
