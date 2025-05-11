#!/usr/bin/env python3
import yaml
import os
from datetime import datetime, timezone
import shutil

def test_file_organization(simulate=True):
    """Test the file organization logic
    Args:
        simulate (bool): If True, only print what would happen without making changes
    """
    # Read the shots configuration
    with open('shots.yml', 'r') as f:
        shots = yaml.safe_load(f)

    # Use UTC date to match GitHub Actions
    date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    print("Testing file organization logic:")
    print("--------------------------------")
    
    for shot in shots:
        output = shot['output']
        # Create directory name from output filename (without extension)
        dir_name = os.path.splitext(output)[0]
        
        print(f"\nProcessing {output}:")
        print(f"  Directory: {dir_name}/")
        
        if os.path.exists(output):
            print(f"  ✓ Found source file: {output}")
        else:
            print(f"  ✗ Source file not found: {output}")
            continue
            
        if os.path.exists(dir_name):
            print(f"  ✓ Target directory exists: {dir_name}/")
        else:
            print(f"  i Would create directory: {dir_name}/")
            
        new_name = f"{dir_name}/{date}.png"
        print(f"  → Would move to: {new_name}")
        
        if not simulate:
            os.makedirs(dir_name, exist_ok=True)
            shutil.move(output, new_name)
            print(f"  ✓ File moved successfully")

if __name__ == "__main__":
    # First run in simulation mode
    print("=== Simulation Mode ===")
    test_file_organization(simulate=True)
    
    # Ask if user wants to proceed with actual changes
    response = input("\nWould you like to proceed with the actual file organization? (y/N): ")
    if response.lower() == 'y':
        print("\n=== Executing Changes ===")
        test_file_organization(simulate=False)
    else:
        print("\nNo changes made.") 
