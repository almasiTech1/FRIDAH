from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'

    def ready(self):
        # Private uploads (IDs, agreements, receipts...) are exposed as short-lived signed links, never as /media/ URLs.
        from common.private_files import install
        install()
