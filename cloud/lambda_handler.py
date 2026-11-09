"""AWS Lambda entry point: validate synthetic CSV from S3, write JSON report."""
import csv
import io
import json
import os
from urllib.parse import unquote_plus

import boto3
from validator import validate_patient

def process_csv(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))
    expected = {"patient_id", "age", "blood_pressure"}
    if not expected.issubset(set(reader.fieldnames or [])):
        raise ValueError("CSV requires patient_id, age, blood_pressure columns")
    results = []
    for row in reader:
        patient_id = row["patient_id"]
        try:
            age = int(row["age"])
            bp = int(row["blood_pressure"])
            issues = validate_patient(patient_id, age, bp)
        except (ValueError, TypeError):
            issues = ["Invalid numeric field"]
        results.append({"patient_id": patient_id, "valid": not issues, "issues": issues})
    return {"total": len(results), "valid": sum(r["valid"] for r in results), "records": results}

def lambda_handler(event, context):
    bucket_allowed = os.environ["BUCKET_NAME"]
    s3 = boto3.client("s3")
    processed = []
    for entry in event.get("Records", []):
        bucket = entry["s3"]["bucket"]["name"]
        key = unquote_plus(entry["s3"]["object"]["key"])
        if bucket != bucket_allowed or not key.startswith("incoming/") or not key.endswith(".csv"):
            continue
        source = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        if len(source) > 2_000_000:
            raise ValueError("CSV exceeds demo limit of 2 MB")
        report = process_csv(source.decode("utf-8-sig"))
        output_key = "reports/" + key[len("incoming/"):-4] + ".json"
        s3.put_object(
            Bucket=bucket, Key=output_key,
            Body=json.dumps(report, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        processed.append(output_key)
    return {"processed_reports": processed}
