from validator import validate_patient


def test_valid_patient():
    result = validate_patient("P001", 25, 120)
    assert result == []


def test_missing_patient_id():
    result = validate_patient("", 25, 120)
    assert "Patient ID is missing" in result


def test_invalid_age():
    result = validate_patient("P002", 150, 120)
    assert "Invalid age" in result


def test_invalid_blood_pressure():
    result = validate_patient("P003", 30, 300)
    assert "Invalid blood pressure" in result
