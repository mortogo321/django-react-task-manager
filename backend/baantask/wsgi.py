"""WSGI config for Task Manager project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "baantask.settings")
application = get_wsgi_application()
