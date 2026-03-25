import os
import boto3
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("S3_PREVIEW_BUCKET")
region = os.getenv("AWS_REGION", "us-east-1")

s3 = boto3.client("s3", region_name=region)

html = """
<html>
<head><title>AEO Test</title></head>
<body>
  <h1>AEO site generator working</h1>
  <p>Bryan preview v1</p>
</body>
</html>
"""

s3.put_object(
    Bucket=bucket,
    Key="bryan-marks/v1/index.html",
    Body=html.encode("utf-8"),
    ContentType="text/html"
)

print(f"Uploaded to s3://{bucket}/bryan-marks/v1/index.html")
