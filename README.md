# Patient Data Quality Validator

A lightweight Python project that validates patient records from a CSV dataset and uses pytest to verify data validation logic.

## Project Overview

This project demonstrates data quality assurance through automated validation. It identifies missing patient IDs, ages outside an expected range, and blood pressure values outside a predefined example range.

## Technologies Used

- Python
- pytest
- CSV (Python standard library)

## Features

- Reads patient records from a CSV file
- Validates patient IDs, ages, and blood pressure values
- Identifies invalid records and displays errors
- Includes 16 automated pytest tests

## How to Run

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the validator:

```bash
python validator.py
```

Run automated tests:

```bash
python -m pytest -v
```

## Sample Results

```text
P001: Valid
P002: Valid
P003: ['Invalid age']
P004: ['Invalid blood pressure']
P005: Valid
```

## Testing

16 automated tests: 4 for the core validation rules (`test_validator.py`) and 12 for the CSV parser and Lambda handler (`tests/test_cloud_handler.py`), using a fake S3 client so no AWS calls are made.

All data is synthetic. Validation ranges are illustrative, not clinical guidelines.

## AWS serverless extension — deployed and verified

`template.yaml` (AWS SAM → CloudFormation) deploys an **S3 → Lambda → S3** pipeline: uploading a synthetic CSV under `incoming/` triggers a Python Lambda that writes a JSON validation report under `reports/` (or `reports/<name>.error.json` for unusable files).

Highlights: least-privilege IAM (read `incoming/*`, write `reports/*` only), HTTPS-only bucket policy, public access blocked, encryption at rest, 30-day data and log expiry, one automatic retry for transient errors.

See **[architecture, design decisions, failure handling, security limitations and deploy steps](docs/AWS_DEPLOYMENT.md)**.

**Verified in AWS on 2026-11-09:** uploading synthetic CSVs to `incoming/` automatically triggered Lambda, which wrote the expected JSON reports (3 valid / 2 invalid; bad file rejected). The stack was then torn down. Details and the honest performance finding are in [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md#verified-results-2026-11-09-us-east-1); raw evidence is in `docs/evidence/`. Never upload real patient information.

Starter code generated with ChatGPT; reviewed, fixed and extended with Claude's assistance.
