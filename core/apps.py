from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        print("CORE READY: starting")

        from apps.core.runtime.startup import Startup

        Startup.initialize()
        print("CORE READY: startup completed")

        import core.signals  # noqa: F401
        print("CORE READY: signals imported")