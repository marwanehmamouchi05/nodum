"""UTC normalization must report invalid input rather than escape validation."""
import pytest
from pydantic import TypeAdapter, ValidationError
from app.models.access import UTCTimestamp


@pytest.mark.parametrize('value', ['0001-01-01T00:00:00+14:00', '9999-12-31T23:59:59-12:00'])
def test_unrepresentable_utc_conversion_is_a_validation_error(value):
    with pytest.raises(ValidationError):
        TypeAdapter(UTCTimestamp).validate_python(value)


@pytest.mark.parametrize('value', ['0001-01-01T00:00:00Z', '9999-12-31T23:59:59Z', '2026-10-17T13:00:00+01:00'])
def test_representable_boundary_and_offset_values_remain_valid(value):
    result=TypeAdapter(UTCTimestamp).validate_python(value)
    assert result.utcoffset().total_seconds()==0
