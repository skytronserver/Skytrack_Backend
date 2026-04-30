from django.apps import AppConfig
import logging
import os
import sys

logger = logging.getLogger(__name__)


class SkytronApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'skytron_api'
    
    def ready(self):
        """
        Called when Django starts.
        Load login settings from database to Redis cache on startup.
        """
        # Skip DB-dependent cache warmup for build/deploy management commands.
        # This prevents warnings during docker build steps like collectstatic.
        startup_skip_commands = {
            'collectstatic',
            'migrate',
            'makemigrations',
            'check',
            'test',
            'shell',
        }
        if len(sys.argv) > 1 and sys.argv[1] in startup_skip_commands:
            logger.info(
                "Skipping login settings cache preload for management command: %s",
                sys.argv[1],
            )
            return

        # Optional hard override via environment variable.
        # Accepted true values: 1, true, yes, on
        skip_preload = os.getenv('SKIP_LOGIN_SETTINGS_CACHE_ON_STARTUP', '').strip().lower()
        if skip_preload in {'1', 'true', 'yes', 'on'}:
            logger.info("Skipping login settings cache preload due to SKIP_LOGIN_SETTINGS_CACHE_ON_STARTUP")
            return

        # Import here to avoid AppRegistryNotReady error
        try:
            from .login_settings_cache import load_all_login_settings_to_cache
            
            # Load settings to cache on startup
            logger.info("Loading login settings to Redis cache on startup...")
            count = load_all_login_settings_to_cache()
            logger.info(f"Successfully loaded {count} login settings to cache")
            
        except Exception as e:
            logger.error(f"Error loading login settings to cache on startup: {str(e)}")
            # Don't raise exception to prevent app from crashing
            pass
