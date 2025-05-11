#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import datetime
import subprocess
import yaml

def load_screenshot_config():
    """Load the screenshot configuration to get directory names"""
    with open('shots.yml', 'r') as f:
        shots = yaml.safe_load(f)
    return [os.path.splitext(shot['output'])[0] for shot in shots]

def backup_to_r2(directory, bucket, endpoint_url):
    """Backup a directory to R2"""
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} does not exist, skipping...")
        return

    # Use AWS CLI with R2 endpoint
    cmd = [
        'aws', 's3', 'sync',
        directory,
        f's3://{bucket}/{directory}',
        '--endpoint-url', endpoint_url
    ]
    
    print(f"Backing up {directory}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ Successfully backed up {directory}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to backup {directory}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Backup screenshot archives to Cloudflare R2')
    parser.add_argument('--bucket', required=True, help='R2 bucket name')
    parser.add_argument('--endpoint', required=True, help='R2 endpoint URL')
    parser.add_argument('--directories', nargs='*', help='Specific directories to backup (optional)')
    args = parser.parse_args()

    # Get directories to backup
    if args.directories:
        dirs_to_backup = args.directories
    else:
        # Use directories from shots.yml
        dirs_to_backup = load_screenshot_config()
        print(f"Found directories from shots.yml: {', '.join(dirs_to_backup)}")

    # Ensure AWS credentials are set
    required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("Error: Missing required environment variables:")
        print("\n".join(f"- {var}" for var in missing_vars))
        print("\nPlease set them using:")
        print("export AWS_ACCESS_KEY_ID=your_access_key_id")
        print("export AWS_SECRET_ACCESS_KEY=your_secret_access_key")
        sys.exit(1)

    # Backup each directory
    for directory in dirs_to_backup:
        backup_to_r2(directory, args.bucket, args.endpoint)

if __name__ == "__main__":
    main() 
