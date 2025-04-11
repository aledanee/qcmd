# Fix for Issue #9: Improved Log File Selection Error Handling

## Description
This PR addresses issue #9 where users encountered issues with the log file selection functionality. When users entered an invalid selection number, the error message was unclear and the function would exit without allowing them to retry.

## Changes Made

### 1. Enhanced Error Messages
- Improved the error message in `display_log_selection()` to be more descriptive and helpful by:
  - Showing the invalid selection that was made
  - Displaying the valid range of numbers to choose from

Example:
- Before: `Invalid selection. Please try again.`
- After: `Invalid selection '5'. Please enter a number between 1 and 5.`

### 2. Comprehensive Test Suite
- Created a well-structured test directory organization:
  - `tests/unit/`: Unit tests for individual components
  - `tests/integration/`: Tests for component interactions
  - `tests/functional/`: End-to-end tests for full workflows
- Added extensive tests to verify the fix and prevent regression
- Added a test runner script (`run_tests.py`) for easy test execution
- Maintained the original test file at `tests/test_log_selection.py` for backward compatibility

### 3. Demo Scripts
- Added demonstration scripts that show the problem and our fix:
  - `demos/demo_log_selection.py`: Shows the specific log selection fix
  - `demos/demo_full_log_analysis.py`: Shows the fix in the context of the full workflow

### 4. Version Update
- Bumped version from 1.0.15 to 1.0.16 in preparation for release
- Updated version in:
  - `qcmd_cli/__init__.py`
  - `pyproject.toml`
  - `qcmd_cli/config/constants.py`
  - `qcmd_cli/qcmd.py`

## How to Test
You can test the fix using these steps:

1. Run the demo script to see the behavior before and after the fix:
   ```
   python3 demos/demo_log_selection.py
   ```

2. Run the full workflow demo:
   ```
   python3 demos/demo_full_log_analysis.py
   ```

3. Run the test suite to verify all tests pass:
   ```
   python3 run_tests.py -v
   ```

## Documentation
- Added a comprehensive README in the tests directory
- Added detailed docstrings to test files and demos

## Related Issues
- Fixes #9 