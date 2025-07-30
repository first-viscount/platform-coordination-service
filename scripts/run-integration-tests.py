#!/usr/bin/env python3
"""Run integration tests with various options."""

import sys
import subprocess
from pathlib import Path

def run_tests(args):
    """Run pytest with integration tests."""
    cmd = [
        "pytest",
        "tests/integration",
        "-v",
        "--tb=short",
        "--maxfail=10",
    ] + args
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--performance", action="store_true", help="Run only performance tests")
    parser.add_argument("--security", action="store_true", help="Run only security tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    parser.add_argument("-x", "--exitfirst", action="store_true", help="Exit on first failure")
    
    args, unknown = parser.parse_known_args()
    
    pytest_args = unknown
    
    if args.coverage:
        pytest_args.extend(["--cov=src", "--cov-report=term-missing"])
    
    if args.performance:
        pytest_args.extend(["-k", "performance"])
    elif args.security:
        pytest_args.extend(["-k", "security"])
    elif args.quick:
        pytest_args.extend(["-m", "not slow"])
    
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    
    if args.exitfirst:
        pytest_args.append("-x")
    
    return run_tests(pytest_args)

if __name__ == "__main__":
    sys.exit(main())
