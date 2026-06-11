from django.db import migrations


def backfill_last_login(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserLoginActivity = apps.get_model("core", "UserLoginActivity")

    for user in User.objects.exclude(last_login__isnull=True):
        if not UserLoginActivity.objects.filter(user=user, login_at=user.last_login).exists():
            UserLoginActivity.objects.create(
                user=user,
                login_at=user.last_login,
                ip_address=None,
                user_agent="Backfilled from auth_user.last_login",
                session_key="",
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0091_userloginactivity"),
    ]

    operations = [
        migrations.RunPython(backfill_last_login, migrations.RunPython.noop),
    ]
