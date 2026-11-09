"""AWS Lambda entry point: validate a synthetic CSV from S3 and write a JSON report.

Trigger: S3 ObjectCreated events for keys matching incoming/*.csv
Output:  reports/<same name>.json            on success
         reports/<same name>.error.json      when the file itself is unusable
"""
import csv
import datetime as dt
import io
import json
import logging
import os
from urllib.parse import unquote_plus

from validator import validate_patient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

INPUT_PREFIX = "incoming/"
OUTPUT_PREFIX = "reports/"
MAX_BYTES = 2_000_000
MAX_ROWS = 10_000
REQUIRED_COLUMNS = {"patient_id", "age", "blood_pressure"}

_s3 = None


class InputFileError(ValueError):
    """The uploaded file cannot be processed (bad format, too large, ...).

    These are *not* retried: retrying a bad file just produces the same failure.
    """


def _client():
    global _s3
    if _s3 is None:
        import boto3  # provided by the Lambda Python runtime
        _s3 = boto3.client("s3")
    return _s3


def process_csv(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text))
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise InputFileError(
            "CSV requires patient_id, age, blood_pressure columns; missing: " + ", ".join(sorted(missing)))
    results = []
    for line_number, row in enumerate(reader, start=2):
        if len(results) >= MAX_ROWS:
            raise InputFileError(f"CSV exceeds demo limit of {MAX_ROWS:,} rows")
        patient_id = (row.get("patient_id") or "").strip()
        try:
            issues = validate_patient(patient_id, int(row["age"]), int(row["blood_pressure"]))
        except (ValueError, TypeError):
            issues = ["Invalid numeric field"]
            if not patient_id:
                issues.insert(0, "Patient ID is missing")
        results.append({"line": line_number, "patient_id": patient_id,
                        "valid": not issues, "issues": issues})
    valid = sum(r["valid"] for r in results)
    return {"total": len(results), "valid": valid, "invalid": len(results) - valid, "records": results}


def _report_key(key, suffix):
    return OUTPUT_PREFIX + key[len(INPUT_PREFIX):-len(".csv")] + suffix


def _put_json(s3, bucket, key, body):
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(body, indent=2).encode("utf-8"),
                  ContentType="application/json")


def lambda_handler(event, context, s3=None):
    s3 = s3 or _client()
    allowed_bucket = os.environ["BUCKET_NAME"]
    processed, failed = [], []

    for entry in event.get("Records", []):
        bucket = entry["s3"]["bucket"]["name"]
        key = unquote_plus(entry["s3"]["object"]["key"])
        if bucket != allowed_bucket or not key.startswith(INPUT_PREFIX) or not key.lower().endswith(".csv"):
            logger.warning("Skipping unexpected object bucket=%s key=%s", bucket, key)
            continue

        base = {"source_key": key, "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        try:
            size = s3.head_object(Bucket=bucket, Key=key)["ContentLength"]
            if size > MAX_BYTES:
                raise InputFileError(f"CSV is {size:,} bytes; demo limit is {MAX_BYTES:,} bytes")
            raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise InputFileError("CSV is not valid UTF-8 text") from exc
            report = {**base, "status": "processed", **process_csv(text)}
            out_key = _report_key(key, ".json")
            _put_json(s3, bucket, out_key, report)
            logger.info("Report written key=%s total=%d invalid=%d", out_key, report["total"], report["invalid"])
            processed.append(out_key)
        except InputFileError as exc:
            # Record the problem next to the reports instead of retrying a bad file.
            out_key = _report_key(key, ".error.json")
            _put_json(s3, bucket, out_key, {**base, "status": "rejected", "error": str(exc)})
            logger.warning("Rejected key=%s reason=%s", key, exc)
            failed.append(out_key)
        # Any other exception (e.g. S3 permission/network error) propagates so Lambda's
        # asynchronous retry policy runs and the error appears in CloudWatch Logs.

    return {"processed_reports": processed, "rejected_reports": failed}
