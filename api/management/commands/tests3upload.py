from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.core.files import File
import os

class Command(BaseCommand):
    help = 'Test direct S3 upload using Django default_storage.'

    def handle(self, *args, **options):
        from django.conf import settings
        import boto3
        import traceback
        self.stdout.write(self.style.WARNING(f"default_storage class: {default_storage.__class__}"))
        from django.conf import settings
        import os
        self.stdout.write(self.style.WARNING(f"settings.DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', None)}"))
        self.stdout.write(self.style.WARNING(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE', None)}"))
        # Check for local_settings.py
        import os
        if os.path.exists(os.path.join(settings.BASE_DIR, 'merchify_backend', 'local_settings.py')):
            self.stdout.write(self.style.WARNING('local_settings.py found in merchify_backend/'))
        else:
            self.stdout.write(self.style.WARNING('No local_settings.py found in merchify_backend/'))
        local_path = '404.png'  # Place your test image in the project root
        if not os.path.exists(local_path):
            self.stdout.write(self.style.ERROR(f'File not found: {local_path}'))
            return
        try:
            with open(local_path, 'rb') as f:
                django_file = File(f, name='404.png')
                s3_path = '404_debug.png'
                self.stdout.write(self.style.WARNING('Attempting to save file to S3 using default_storage...'))
                saved_path = default_storage.save(s3_path, django_file)
                url = default_storage.url(saved_path)
                self.stdout.write(self.style.SUCCESS(f'Uploaded to S3: {url}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Exception during save: {e}'))
            self.stdout.write(traceback.format_exc())
            return
        # Check existence using boto3
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        try:
            s3.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=saved_path)
            self.stdout.write(self.style.SUCCESS(f'File {saved_path} exists in S3 (verified by boto3).'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'File {saved_path} does NOT exist in S3: {e}'))
        # List all files in the bucket for debug
        resp = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        if 'Contents' in resp:
            self.stdout.write(self.style.SUCCESS('Files in S3 bucket:'))
            for obj in resp['Contents']:
                self.stdout.write(f"- {obj['Key']}")
        else:
            self.stdout.write(self.style.WARNING('No files found in S3 bucket.'))
