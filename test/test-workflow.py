import yaml
import os
from datetime import datetime
import shutil

def test_screenshot_workflow():
    # Read the test shots configuration
    with open('test-shots.yml', 'r') as f:
        shots = yaml.safe_load(f)
    
    print("1. Testing shot-scraper multi command...")
    os.system('shot-scraper multi test-shots.yml')
    
    print("\n2. Testing file organization...")
    date = datetime.now().strftime('%Y-%m-%d')
    
    # Process each shot
    for shot in shots:
        output = shot['output']
        if os.path.exists(output):
            print(f"Found screenshot: {output}")
            
            # Create directory if doesn't exist
            dir_name = os.path.splitext(output)[0]
            os.makedirs(dir_name, exist_ok=True)
            
            # Move file to dated location
            new_name = f"{dir_name}/{date}.png"
            shutil.move(output, new_name)
            print(f"Moved to: {new_name}")
            
            # Simulate S3 upload (just print the command that would be run)
            s3_path = shot['s3_path']
            s3_dest = f"s3://YOUR_BUCKET/{s3_path}/{date}.png"
            print(f"Would upload to: {s3_dest}")
        else:
            print(f"Warning: Screenshot {output} not found!")
    
    print("\nTest complete! Check the output above for any issues.")

if __name__ == "__main__":
    test_screenshot_workflow() 
