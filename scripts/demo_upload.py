"""Upload a synthetic CSV to the deployed stack and capture redacted evidence.

    python scripts/demo_upload.py --stack pdv-demo --region us-east-1 --file patients.csv

Needs: s3:PutObject on incoming/*, s3:GetObject on reports/*, cloudformation:DescribeStacks.
Writes docs/evidence/<name>_run.json with the account ID masked.
"""
import argparse
import datetime as dt
import json
import pathlib
import time

import boto3
from botocore.exceptions import ClientError


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stack", required=True)
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--file", default="patients.csv")
    p.add_argument("--timeout", type=int, default=60)
    a = p.parse_args()

    outputs = {o["OutputKey"]: o["OutputValue"] for o in boto3.client("cloudformation", region_name=a.region)
               .describe_stacks(StackName=a.stack)["Stacks"][0].get("Outputs", [])}
    bucket = outputs["DataBucketName"]
    account = bucket.rsplit("-", 1)[-1]
    redacted_bucket = bucket.replace(account, "********" + account[-4:])
    s3 = boto3.client("s3", region_name=a.region)

    src = pathlib.Path(a.file)
    in_key = f"incoming/{src.name}"
    report_key = f"reports/{src.stem}.json"
    error_key = f"reports/{src.stem}.error.json"
    uploaded_at = dt.datetime.now(dt.timezone.utc)
    s3.upload_file(str(src), bucket, in_key)
    print(f"Uploaded {src} -> s3://{redacted_bucket}/{in_key}")

    deadline = time.time() + a.timeout
    while time.time() < deadline:
        for key in (report_key, error_key):
            try:
                obj = s3.get_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey", "AccessDenied"):
                    raise
                continue
            if obj["LastModified"] < uploaded_at - dt.timedelta(seconds=5):
                continue  # stale report from an earlier run
            report = json.loads(obj["Body"].read())
            seconds = (obj["LastModified"] - uploaded_at).total_seconds()
            evidence = {"captured_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        "region": a.region, "stack": a.stack, "bucket": redacted_bucket,
                        "input_key": in_key, "report_key": key,
                        "report_last_modified_minus_upload_s": round(seconds, 1), "report": report}
            out = pathlib.Path("docs/evidence") / f"{src.stem}_run.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(f"Report found: s3://{redacted_bucket}/{key}  status={report.get('status')}")
            print(json.dumps({k: report.get(k) for k in ("total", "valid", "invalid", "error")}, indent=2))
            print(f"Evidence saved to {out}")
            return 0
        time.sleep(3)
    print("No report appeared. Check CloudWatch Logs for the validator function.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
