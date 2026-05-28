import aioboto3
from botocore.config import Config
from src.config.settings import get_settings

session = aioboto3.Session()

async def stream_upload_to_r2(file, key: str, content_type: str):
    bucket_name = get_settings().CLOUDFLARE_R2_BUCKET_NAME
    chunk_size = get_settings().CHUNK_SIZE
    endpoint = get_settings().STORAGE_ENDPOINT_URL
    aws_access_key_id = get_settings().CLOUDFLARE_R2_ACCESS_KEY_ID
    aws_secret_access_key = get_settings().CLOUDFLARE_R2_SECRET_ACCESS_KEY 
     
    async with session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    ) as ai_r2_client:

        # Initiate multipart upload asynchronously
        response = await ai_r2_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=key,
            ContentType=content_type
        )
        upload_id = response['UploadId']
        parts = []
        part_number = 1
        total_bytes_uploaded = 0

        try:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                part_response = await ai_r2_client.upload_part(
                    Bucket=bucket_name,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                total_bytes_uploaded += len(chunk)
                part_number += 1

            # Complete multipart upload asynchronously
            await ai_r2_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            return total_bytes_uploaded

        except Exception as e:
            # Abort multipart upload asynchronously in case of failure
            await ai_r2_client.abort_multipart_upload(
                Bucket=bucket_name,
                Key=key,
                UploadId=upload_id
            )
            raise e
