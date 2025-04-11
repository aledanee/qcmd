# QCMD Tests

This directory contains tests for the QCMD CLI tool.

## Test Structure

The tests are organized into categories:

- **Unit Tests** (`unit/`): Tests for individual components in isolation
- **Integration Tests** (`integration/`): Tests for component interactions
- **Functional Tests** (`functional/`): End-to-end tests simulating user workflows

## Running Tests

You can run the tests using the `run_tests.py` script in the root directory:

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run only unit tests
python run_tests.py -u

# Run only integration tests
python run_tests.py -i

# Run only functional tests
python run_tests.py -f

# Run multiple categories
python run_tests.py -u -i
```

You can also run individual test files:

```bash
# Run a specific test file
python -m tests.unit.test_log_selection

# Run a specific test case
python -m tests.unit.test_log_selection TestLogSelection.test_valid_selection
```

## Writing Tests

When writing new tests:

1. Determine the appropriate category (unit, integration, or functional)
2. Create a new file in the corresponding directory, named with a `test_` prefix
3. Use the unittest framework and follow existing test patterns
4. Document the test's purpose with clear docstrings

## Test Fixtures

Tests that require temporary files or setup/teardown should use the unittest's
`setUp` and `tearDown` methods as demonstrated in existing tests.

## Test Coverage

To check test coverage, install the `coverage` package and run:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source=qcmd_cli run_tests.py

# Generate HTML report
coverage html

# View report (open the index.html file in the htmlcov directory)
``` 