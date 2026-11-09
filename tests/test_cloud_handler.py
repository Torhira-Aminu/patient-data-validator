import json
from unittest.mock import MagicMock

import pytest

from cloud.lambda_handler import InputFileError, lambda_handler, process_csv

BUCKET = "pdv-data-123456789012"


def test_csv_report():
    result = process_csv("patient_id,age,blood_pressure\nP001,25,120\nP002,999,120\n")
    assert (result["total"], result["valid"], result["invalid"]) == (2, 1, 1)
    assert "Invalid age" in result["records"][1]["issues"]
    assert result["records"][1]["line"] == 3


def test_bad_numeric_data():
    result = process_csv("patient_id,age,blood_pressure\nP003,unknown,120\n")
    assert result["records"][0]["issues"] == ["Invalid numeric field"]


def test_missing_id_and_bad_number_both_reported():
    result = process_csv("patient_id,age,blood_pressure\n,abc,120\n")
    assert result["records"][0]["issues"] == ["Patient ID is missing", "Invalid numeric field"]


def test_short_row_does_not_crash():
    result = process_csv("patient_id,age,blood_pressure\nP009,40\n")
    assert not result["records"][0]["valid"]


def test_missing_columns():
    with pytest.raises(InputFileError, match="blood_pressure"):
        process_csv("patient_id,age\nP001,20\n")


def test_header_only_file():
    assert process_csv("patient_id,age,blood_pressure\n")["total"] == 0


# ---- handler tests with a fake S3 client (no AWS calls) ----

def s3_event(key, bucket=BUCKET):
    return {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}]}


def fake_s3(body: bytes):
    s3 = MagicMock()
    s3.head_object.return_value = {"ContentLength": len(body)}
    s3.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=body))}
    return s3


def written(s3):
    kwargs = s3.put_object.call_args.kwargs
    return kwargs["Key"], json.loads(kwargs["Body"])


@pytest.fixture(autouse=True)
def bucket_env(monkeypatch):
    monkeypatch.setenv("BUCKET_NAME", BUCKET)


def test_handler_writes_report():
    s3 = fake_s3(b"\xef\xbb\xbfpatient_id,age,blood_pressure\nP001,25,120\nP004,30,300\n")
    out = lambda_handler(s3_event("incoming/batch+1.csv"), None, s3=s3)  # '+' = space in S3 events
    key, report = written(s3)
    assert key == "reports/batch 1.json"
    assert out["processed_reports"] == ["reports/batch 1.json"]
    assert (report["status"], report["total"], report["invalid"]) == ("processed", 2, 1)
    assert report["source_key"] == "incoming/batch 1.csv"


def test_handler_ignores_other_prefixes_and_buckets():
    s3 = fake_s3(b"x")
    lambda_handler(s3_event("reports/x.csv"), None, s3=s3)
    lambda_handler(s3_event("incoming/x.csv", bucket="someone-else"), None, s3=s3)
    lambda_handler(s3_event("incoming/notes.txt"), None, s3=s3)
    s3.get_object.assert_not_called()
    s3.put_object.assert_not_called()


def test_oversized_file_rejected_without_download():
    s3 = fake_s3(b"")
    s3.head_object.return_value = {"ContentLength": 5_000_000}
    out = lambda_handler(s3_event("incoming/big.csv"), None, s3=s3)
    s3.get_object.assert_not_called()
    key, report = written(s3)
    assert key == "reports/big.error.json" and report["status"] == "rejected"
    assert out["rejected_reports"] == ["reports/big.error.json"]


def test_bad_columns_produce_error_report_not_exception():
    s3 = fake_s3(b"name,age\nA,3\n")
    lambda_handler(s3_event("incoming/wrong.csv"), None, s3=s3)
    key, report = written(s3)
    assert key == "reports/wrong.error.json" and "missing" in report["error"]


def test_non_utf8_rejected():
    s3 = fake_s3(b"\xff\xfe\x00bad")
    lambda_handler(s3_event("incoming/bin.csv"), None, s3=s3)
    assert written(s3)[1]["error"] == "CSV is not valid UTF-8 text"


def test_aws_errors_propagate_for_retry():
    s3 = fake_s3(b"")
    s3.head_object.side_effect = RuntimeError("AccessDenied")
    with pytest.raises(RuntimeError):
        lambda_handler(s3_event("incoming/a.csv"), None, s3=s3)
