#!/usr/bin/env python3
"""
Simple script to find screenshots that show the loading state.
Detects the uniform green loading box by checking color uniformity.

Usage:
    python find-loading-screenshots.py --check
    python find-loading-screenshots.py --delete
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import numpy as np

BACKGROUND_GREEN = np.array([208, 225, 214])
# Word magnets have a light gray background - loading screenshots have none
MAGNET_GRAY = np.array([239, 239, 239])


def check_for_loading_box(image_path):
    """
    Detects loading screenshots using two combined signals:
    1. Center region is uniform green (loading box present, no magnets in center)
    2. Very few magnet-gray pixels across the whole image (no word magnets loaded)

    Valid screenshots with sparse words pass check 1 but fail check 2 (they still
    have magnet-gray pixels from the word tiles that did load).
    """
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        img_array = np.array(img)

        # Check 1: center region is uniform green
        cx, cy = width // 2, height // 2
        center_is_uniform = False
        for box in [
            (cx-400, cy-400, cx+400, cy-100),  # Upper-center
            (cx-400, cy-100, cx+400, cy+100),  # Center
        ]:
            region = img_array[box[1]:box[3], box[0]:box[2]]
            pixels = region.reshape(-1, 3)
            green_ratio = np.mean(np.linalg.norm(pixels - BACKGROUND_GREEN, axis=1) < 15)
            avg_std = np.mean([np.std(region[:, :, c]) for c in range(3)])
            if green_ratio > 0.90 and avg_std < 20:
                center_is_uniform = True
                break

        if not center_is_uniform:
            return False, ""

        # Check 2: very few word-magnet pixels (loading = no magnets loaded yet)
        all_pixels = img_array.reshape(-1, 3)
        magnet_count = int(np.sum(np.linalg.norm(all_pixels - MAGNET_GRAY, axis=1) <= 10))
        if magnet_count >= 80_000:
            return False, ""

        return True, f"magnet_pixels={magnet_count:,}"

    except Exception as e:
        print(f"  ⚠️  Error reading {image_path}: {e}")
        return False, ""


def scan_directory(directory):
    """Scan directory for loading screenshots"""
    results = {
        'loading': [],
        'valid': []
    }

    if not os.path.exists(directory):
        print(f"  ⚠️  Directory does not exist: {directory}")
        return results

    # Get all PNG and JPG files
    image_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        image_files.extend(Path(directory).glob(ext))

    print(f"\nScanning {len(image_files)} screenshots in {directory}...")

    for i, image_path in enumerate(sorted(image_files), 1):
        print(f"  [{i}/{len(image_files)}] Checking {image_path.name}...", end=' ')

        has_loading, details = check_for_loading_box(str(image_path))

        if has_loading:
            print(f"❌ LOADING DETECTED ({details})")
            results['loading'].append({
                'path': str(image_path),
                'filename': image_path.name,
                'details': details
            })
        else:
            print("✅ OK")
            results['valid'].append(str(image_path))

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Find screenshots that captured the loading state'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check for loading screenshots'
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete loading screenshots'
    )
    parser.add_argument(
        '--source',
        type=str,
        default='fridge-poem',
        help='Source directory to check (default: fridge-poem)'
    )
    
    args = parser.parse_args()
    
    if not args.check and not args.delete:
        parser.print_help()
        sys.exit(1)
    
    # Run scan
    results = scan_directory(args.source)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary for {args.source}:")
    print(f"   ✅ Valid screenshots: {len(results['valid'])}")
    print(f"   ❌ Loading screenshots: {len(results['loading'])}")
    
    if results['loading']:
        print(f"\n🚨 Found {len(results['loading'])} screenshot(s) with loading state:")
        for item in results['loading']:
            print(f"     • {item['filename']}")
    
    # Delete if requested
    if args.delete and results['loading']:
        print(f"\n🗑️  Deleting {len(results['loading'])} loading screenshot(s)...")
        
        for item in results['loading']:
            try:
                os.remove(item['path'])
                print(f"   Deleted: {item['filename']}")
            except Exception as e:
                print(f"   ⚠️  Could not delete {item['filename']}: {e}")
        
        print(f"✅ Cleanup complete!")
    elif results['loading'] and not args.delete:
        print(f"\n💡 Run with --delete to remove them.")
    
    # Exit with error if loading screenshots found
    if results['loading'] and not args.delete:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()


