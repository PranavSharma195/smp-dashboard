from django.contrib.auth.forms import AuthenticationForm


class FriendlyAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "That username and password don't match. Check them and try again.",
        "inactive": "This account is switched off. Ask an administrator to re-enable it.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autofocus": True, "autocomplete": "username", "placeholder": "Username"}
        )
        self.fields["password"].widget.attrs.update(
            {"autocomplete": "current-password", "placeholder": "Password"}
        )
