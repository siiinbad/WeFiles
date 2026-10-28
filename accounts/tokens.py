from django.contrib.auth.tokens import PasswordResetTokenGenerator


class VerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "wefiles.email.verification"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified_at}{timestamp}"


verification_token = VerificationTokenGenerator()
