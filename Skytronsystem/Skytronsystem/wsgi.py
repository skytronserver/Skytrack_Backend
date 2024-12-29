"""
WSGI config for Skytronsystem project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from whitenoise import WhiteNoise
from django.core.wsgi import get_wsgi_application

from pathlib import Path
import os 
 
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

application = get_wsgi_application()

  
 
application = WhiteNoise(application, root=os.path.join(BASE_DIR, '../staticfiles/'))