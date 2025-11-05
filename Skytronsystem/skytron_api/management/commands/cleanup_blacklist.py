"""
Django management command to cleanup expired blacklisted tokens

Usage:
    python manage.py cleanup_blacklist

Add to crontab for daily cleanup:
    0 3 * * * cd /path/to/project && python manage.py cleanup_blacklist
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from skytron_api.models import TokenBlacklist


class Command(BaseCommand):
    help = 'Cleanup expired tokens from the blacklist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.NOTICE('Starting token blacklist cleanup...'))
        
        # Get count of expired tokens
        expired_tokens = TokenBlacklist.objects.filter(expires_at__lt=timezone.now())
        count = expired_tokens.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired tokens to cleanup.'))
            return
        
        self.stdout.write(f'Found {count} expired tokens to cleanup.')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No tokens will be deleted.'))
            # Show sample of tokens that would be deleted
            for token in expired_tokens[:10]:
                self.stdout.write(
                    f'  - Token for user {token.user_id}, '
                    f'expired at {token.expires_at}, '
                    f'reason: {token.reason}'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            # Actually delete the expired tokens
            deleted_count = TokenBlacklist.cleanup_expired()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleaned up {deleted_count} expired tokens.'
                )
            )
