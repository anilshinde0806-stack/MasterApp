from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        from apps.core.runtime.startup import Startup

        Startup.initialize()

        import core.signals  # noqa: F401