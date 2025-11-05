# Testing Guide

This directory contains unit tests and integration tests for the trading bot.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov
```

### Run Specific Test File
```bash
pytest tests/test_ml_models.py
```

### Run Specific Test
```bash
pytest tests/test_ml_models.py::TestMLPredictor::test_train_random_forest
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Tests and Generate HTML Coverage Report
```bash
pytest --cov --cov-report=html
open htmlcov/index.html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_delta_client.py     # API client tests
├── test_data_collector.py   # Data collection tests
├── test_feature_engineering.py  # Feature engineering tests
├── test_ml_models.py        # ML model tests
├── test_strategies.py       # Strategy tests
├── test_config.py           # Configuration tests
├── test_execution.py        # Order/Position manager tests
└── test_integration.py      # Integration tests
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test components working together
- End-to-end workflows
- May require more setup

## Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_dir`: Temporary directory for test files
- `sample_ohlc_data`: Sample OHLC DataFrame
- `sample_orderbook`: Sample orderbook data
- `sample_ticker`: Sample ticker data
- `mock_config`: Mock configuration
- `mock_delta_client`: Mock API client

## Writing Tests

### Example Unit Test

```python
def test_my_function():
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == "expected"
```

### Example Test with Fixtures

```python
def test_with_fixture(sample_ohlc_data):
    """Test using fixture."""
    assert not sample_ohlc_data.empty
    assert 'close' in sample_ohlc_data.columns
```

### Example Test with Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked dependency."""
    mock_client = Mock()
    mock_client.get_data.return_value = {'result': 'test'}
    
    result = my_function(mock_client)
    assert result == 'test'
```

## Test Coverage

Current coverage targets:
- **Unit Tests**: >80% coverage
- **Integration Tests**: Key workflows covered

## Running Tests in CI/CD

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov --cov-report=xml
```

## Continuous Testing

For development, use pytest-watch for continuous testing:

```bash
pip install pytest-watch
ptw  # Watch for changes and run tests
```

## Mocking External Services

### API Calls
- Mock `requests.Session` for API calls
- Use fixtures for common responses

### File System
- Use `temp_dir` fixture for temporary files
- Tests clean up after themselves

### ML Models
- Use small datasets for faster tests
- Mock model persistence when possible

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Fast Tests**: Keep unit tests fast (<1 second each)
3. **Clear Names**: Test names should describe what they test
4. **Arrange-Act-Assert**: Structure tests clearly
5. **Mock External Dependencies**: Don't make real API calls in tests
6. **Test Edge Cases**: Test error conditions and boundary cases

## Troubleshooting

### Tests Fail with Import Errors
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

### Tests Fail with Missing Fixtures
- Check `conftest.py` for fixture definitions
- Ensure pytest is finding the fixtures

### Tests Are Slow
- Use smaller test datasets
- Mock external dependencies
- Run tests in parallel: `pytest -n auto`

