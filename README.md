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
- Includes four automated pytest tests

## How to Run

Install pytest:

```bash
python -m pip install pytest
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

Four automated tests check valid records, missing IDs, invalid ages, and invalid blood pressure values.

All data is synthetic. Validation ranges are illustrative, not clinical guidelines.

## AWS serverless extension — deployment pending

An additional `template.yaml` deploys an **S3 → AWS Lambda → S3** flow using AWS SAM and CloudFormation. Uploading a synthetic CSV under `incoming/` triggers a Python validation function; output JSON is saved under `reports/`. See [AWS deployment and verification](docs/AWS_DEPLOYMENT.md) and [Lambda handler](cloud/lambda_handler.py).

**This is source code only until verified in an AWS account.** Unit tests mock/local-run the validation logic; do not claim a successful cloud deployment from these alone. Never upload real patient information or AWS credentials.
