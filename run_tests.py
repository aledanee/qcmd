#!/usr/bin/env python3
"""
Test runner script for QCMD tests.

This script runs all tests in the project, with options to run specific test categories.
"""
import os
import sys
import unittest
import argparse

def run_tests(categories=None, verbose=False):
    """
    Run the specified test categories.
    
    Args:
        categories: List of test categories to run ('unit', 'integration', 'functional')
                   If None, all tests will be run
        verbose: Whether to show verbose output
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root to the Python path to ensure imports work
    sys.path.insert(0, script_dir)
    
    # Full test suite
    full_suite = unittest.TestSuite()
    
    # If no categories specified, run all tests
    if not categories:
        categories = ['unit', 'integration', 'functional']
    
    # Collect all test modules
    test_modules = []
    for category in categories:
        category_dir = os.path.join(script_dir, 'tests', category)
        if os.path.exists(category_dir):
            print(f"Discovering tests in {category}...")
            
            # Find all test files
            for root, _, files in os.walk(category_dir):
                for file in files:
                    if file.startswith('test_') and file.endswith('.py'):
                        # Convert path to module name
                        rel_path = os.path.relpath(os.path.join(root, file), script_dir)
                        module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
                        test_modules.append(module_name)
        else:
            print(f"Warning: Test directory for {category} not found.")
    
    # Create the test suite
    loader = unittest.TestLoader()
    for module_name in test_modules:
        try:
            print(f"Loading tests from {module_name}")
            module = __import__(module_name, fromlist=['*'])
            tests = loader.loadTestsFromModule(module)
            full_suite.addTest(tests)
        except ImportError as e:
            print(f"Error importing {module_name}: {e}")
    
    # Run the tests
    verbosity = 2 if verbose else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(full_suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run QCMD tests')
    parser.add_argument('-u', '--unit', action='store_true', help='Run unit tests')
    parser.add_argument('-i', '--integration', action='store_true', help='Run integration tests')
    parser.add_argument('-f', '--functional', action='store_true', help='Run functional tests')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine which categories to run
    categories = []
    if args.unit:
        categories.append('unit')
    if args.integration:
        categories.append('integration')
    if args.functional:
        categories.append('functional')
    
    # Exit with the appropriate code
    sys.exit(run_tests(categories=categories, verbose=args.verbose)) 