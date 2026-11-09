from cloud.lambda_handler import process_csv

def test_csv_report():
    csv_data = "patient_id,age,blood_pressure\nP001,25,120\nP002,999,120\n"
    result = process_csv(csv_data)
    assert result["total"] == 2
    assert result["valid"] == 1
    assert "Invalid age" in result["records"][1]["issues"]

def test_bad_numeric_data():
    result = process_csv("patient_id,age,blood_pressure\nP003,unknown,120\n")
    assert not result["records"][0]["valid"]

def test_missing_columns():
    import pytest
    with pytest.raises(ValueError):
        process_csv("patient_id,age\nP001,20\n")
