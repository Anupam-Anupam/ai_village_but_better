import os
import time
import base64
from datetime import datetime
from minio import Minio
from minio.error import S3Error
import asyncio
from pathlib import Path
from typing import Dict, Optional

# Get environment variables
minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
minio_bucket = os.getenv("MINIO_BUCKET", "screenshots")
minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
agent_id = os.getenv("AGENT_ID", "1")

# Initialize MinIO client
minio_client = Minio(
    minio_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=minio_secure
)

def ensure_bucket_exists():
    """Ensure the MinIO bucket exists and is publicly accessible."""
    try:
        if not minio_client.bucket_exists(minio_bucket):
            minio_client.make_bucket(minio_bucket)
            print(f"Created bucket: {minio_bucket}")
            
            # Set bucket policy to public read
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{minio_bucket}/*"]
                    }
                ]
            }
            minio_client.set_bucket_policy(minio_bucket, policy)
            print(f"Set public read policy on bucket: {minio_bucket}")
    except S3Error as e:
        print(f"Error ensuring bucket exists: {e}")

async def upload_screenshot_to_minio(screenshot_data: bytes, filename: str) -> Optional[str]:
    """Upload a screenshot to MinIO and return the public URL."""
    try:
        # Create a unique object name with agent ID and timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        object_name = f"{agent_id}/screenshots/{timestamp}_{filename}"
        
        # Upload the screenshot
        result = minio_client.put_object(
            minio_bucket,
            object_name,
            data=io.BytesIO(screenshot_data),
            length=len(screenshot_data),
            content_type="image/png"
        )
        
        print(f"Uploaded screenshot to MinIO: {object_name}")
        return object_name
    except Exception as e:
        print(f"Error uploading to MinIO: {e}")
        return None

async def take_screenshot() -> Optional[bytes]:
    """Take a screenshot using Playwright."""
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to the agent's status page or any other relevant page
            # For now, we'll just create a simple page with the agent's status
            await page.set_content(
                f"""
                <html>
                    <head>
                        <title>Agent {agent_id} Status</title>
                        <style>
                            body {{ 
                                font-family: Arial, sans-serif; 
                                padding: 20px;
                                background-color: #f5f5f5;
                            }}
                            .status-container {{
                                max-width: 800px;
                                margin: 0 auto;
                                background: white;
                                padding: 20px;
                                border-radius: 8px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            }}
                            h1 {{ color: #333; }}
                            .timestamp {{ color: #666; font-size: 0.9em; }}
                        </style>
                    </head>
                    <body>
                        <div class="status-container">
                            <h1>Agent {agent_id} Status</h1>
                            <div class="timestamp">Last updated: {datetime.utcnow().isoformat()} UTC</div>
                            <p>This is an automated screenshot from the agent's environment.</p>
                        </div>
                    </body>
                </html>
                """
            )
            
            # Take a screenshot
            screenshot = await page.screenshot(full_page=True, type="png")
            await browser.close()
            
            return screenshot
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

async def screenshot_loop(interval_seconds: int = 30):
    """Run the screenshot loop."""
    ensure_bucket_exists()
    
    while True:
        try:
            print(f"Taking screenshot for agent {agent_id}...")
            screenshot = await take_screenshot()
            if screenshot:
                object_name = await upload_screenshot_to_minio(screenshot, "status.png")
                if object_name:
                    print(f"Screenshot uploaded: {object_name}")
                    
                    # Also save the latest.png for easy access
                    minio_client.put_object(
                        minio_bucket,
                        f"{agent_id}/latest.png",
                        data=io.BytesIO(screenshot),
                        length=len(screenshot),
                        content_type="image/png"
                    )
                    print(f"Updated latest.png for agent {agent_id}")
        except Exception as e:
            print(f"Error in screenshot loop: {e}")
        
        # Wait for the next interval
        await asyncio.sleep(interval_seconds)

if __name__ == "__main__":
    # For testing
    import io
    asyncio.run(screenshot_loop(10))  # Run with 10-second interval for testing
