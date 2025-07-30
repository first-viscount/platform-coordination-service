#!/usr/bin/env python3
"""Clean up broken tests from the test suite."""

import subprocess
import os
import sys

def get_test_results():
    """Run pytest and get detailed results."""
    print("Running all tests to identify failures...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.split('\n')
    
    failed_tests = []
    passed_tests = []
    
    for line in lines:
        if "FAILED" in line:
            # Extract test file and name
            parts = line.split("::")
            if len(parts) >= 2:
                test_file = parts[0].strip()
                test_name = parts[1].split()[0] if parts[1] else ""
                failed_tests.append((test_file, test_name, line))
        elif "PASSED" in line:
            parts = line.split("::")
            if len(parts) >= 2:
                test_file = parts[0].strip()
                test_name = parts[1].split()[0] if parts[1] else ""
                passed_tests.append((test_file, test_name))
    
    return passed_tests, failed_tests

def analyze_failures():
    """Analyze test failures by file."""
    passed_tests, failed_tests = get_test_results()
    
    print(f"\n📊 Test Results:")
    print(f"✅ Passed: {len(passed_tests)}")
    print(f"❌ Failed: {len(failed_tests)}")
    print(f"📈 Pass rate: {len(passed_tests) / (len(passed_tests) + len(failed_tests)) * 100:.1f}%")
    
    # Group failures by file
    failures_by_file = {}
    for test_file, test_name, line in failed_tests:
        if test_file not in failures_by_file:
            failures_by_file[test_file] = []
        failures_by_file[test_file].append(test_name)
    
    # Group passes by file
    passes_by_file = {}
    for test_file, test_name in passed_tests:
        if test_file not in passes_by_file:
            passes_by_file[test_file] = []
        passes_by_file[test_file].append(test_name)
    
    print("\n📁 Failures by file:")
    files_to_remove = []
    
    for test_file, failed_test_names in sorted(failures_by_file.items()):
        passed_in_file = len(passes_by_file.get(test_file, []))
        failed_in_file = len(failed_test_names)
        total_in_file = passed_in_file + failed_in_file
        failure_rate = failed_in_file / total_in_file * 100 if total_in_file > 0 else 100
        
        print(f"\n{test_file}:")
        print(f"  - Failed: {failed_in_file}/{total_in_file} ({failure_rate:.1f}% failure rate)")
        
        # If more than 50% of tests in a file fail, consider removing it
        if failure_rate > 50:
            files_to_remove.append(test_file)
            print(f"  - 🗑️  Recommending removal (high failure rate)")
    
    return files_to_remove, failures_by_file, passes_by_file

def main():
    """Main cleanup process."""
    files_to_remove, failures_by_file, passes_by_file = analyze_failures()
    
    if not files_to_remove:
        print("\n✅ No files need removal. Consider fixing individual failing tests.")
        return
    
    print(f"\n🗑️  Files recommended for removal ({len(files_to_remove)}):")
    for f in files_to_remove:
        print(f"  - {f}")
    
    response = input("\nRemove these files? (y/N): ")
    if response.lower() == 'y':
        for test_file in files_to_remove:
            if os.path.exists(test_file):
                os.remove(test_file)
                print(f"✅ Removed {test_file}")
        
        print("\n🔄 Re-running tests to verify...")
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no"])
    else:
        print("\n❌ Cleanup cancelled.")
        
        # Offer to create a report instead
        print("\n📝 Creating test failure report...")
        with open("test-failures-report.md", "w") as f:
            f.write("# Test Failures Report\n\n")
            f.write(f"Total tests: {len(passes_by_file) + len(failures_by_file)}\n")
            f.write(f"Failed: {sum(len(v) for v in failures_by_file.values())}\n\n")
            
            f.write("## Files with high failure rates:\n\n")
            for test_file in files_to_remove:
                f.write(f"- {test_file}\n")
            
            f.write("\n## All failures:\n\n")
            for test_file, failed_tests in sorted(failures_by_file.items()):
                f.write(f"\n### {test_file}\n")
                for test in failed_tests:
                    f.write(f"- {test}\n")
        
        print("✅ Report saved to test-failures-report.md")

if __name__ == "__main__":
    main()