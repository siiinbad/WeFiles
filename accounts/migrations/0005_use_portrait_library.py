from django.db import migrations


def use_portraits(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.using(schema_editor.connection.alias).only("pk", "avatar_icon").iterator():
        if not user.avatar_icon.startswith("portrait-"):
            User.objects.using(schema_editor.connection.alias).filter(pk=user.pk).update(
                avatar_icon=f"portrait-{user.pk.int % 30 + 1:02d}"
            )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_remove_user_valid_user_avatar_alter_user_avatar_icon_and_more")]
    operations = [migrations.RunPython(use_portraits, migrations.RunPython.noop)]
