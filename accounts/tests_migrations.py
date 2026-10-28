"""Verify upgrades for accounts created before avatar support existed."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PortraitUpgradeTests(TransactionTestCase):
    def test_existing_account_upgrades_through_both_avatar_libraries(self):
        original = [("accounts", "0001_initial")]
        current = [("accounts", "0005_use_portrait_library")]
        executor = MigrationExecutor(connection)
        try:
            executor.migrate(original)
            old_user = executor.loader.project_state(original).apps.get_model("accounts", "User")
            user = old_user.objects.create(email="existing@example.test", username="existing")
            user_id = user.pk
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            new_user = executor.loader.project_state(current).apps.get_model("accounts", "User")
            upgraded = new_user.objects.get(pk=user_id)
            self.assertTrue(upgraded.avatar_icon.startswith("portrait-"))
            self.assertEqual(upgraded.email, "existing@example.test")
            self.assertEqual(upgraded.status, "pending")
        finally:
            MigrationExecutor(connection).migrate(current)
