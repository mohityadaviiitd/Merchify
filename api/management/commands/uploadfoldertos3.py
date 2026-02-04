from django.core.management.base import BaseCommand
import os
import boto3
from django.conf import settings

class Command(BaseCommand):
    help = 'Upload all files from a local folder to S3 using boto3.'

    def add_arguments(self, parser):
        parser.add_argument('--folder', type=str, default='local_images', help='Local folder to upload')
        parser.add_argument('--prefix', type=str, default='', help='S3 key prefix (optional)')

    def handle(self, *args, **options):
        folder = options['folder']
        prefix = options['prefix']
        if not os.path.isdir(folder):
            self.stdout.write(self.style.ERROR(f'Folder not found: {folder}'))
            return
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        uploaded = 0
        for root, dirs, files in os.walk(folder):
            for fname in files:
                local_path = os.path.join(root, fname)
                rel_path = os.path.relpath(local_path, folder)
                s3_key = os.path.join(prefix, rel_path).replace('\\', '/')
                try:
                    s3.upload_file(local_path, bucket, s3_key)
                    self.stdout.write(self.style.SUCCESS(f'Uploaded {local_path} to s3://{bucket}/{s3_key}'))
                    uploaded += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to upload {local_path}: {e}'))
        self.stdout.write(self.style.SUCCESS(f'Total files uploaded: {uploaded}'))