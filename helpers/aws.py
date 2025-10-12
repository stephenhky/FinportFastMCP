
from typing import Union
from os import PathLike

import boto3

from app.apischemas.schemas import S3UploadResponse



def copy_file_to_s3(
        filepath: Union[PathLike, str],
        s3_bucket: str,
        target_filename: str
) -> S3UploadResponse:
    s3_client = boto3.client("s3")
    s3_client.upload_file(filepath, s3_bucket, target_filename)
    return S3UploadResponse(
        filename=target_filename,
        url=f"https://{s3_bucket}.s3.amazonaws.com/{target_filename}",
    )
