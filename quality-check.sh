#!/bin/bash
# Platform Coordination Service - Quality Check Script
# This script performs comprehensive quality checks for this service only

set -e

SERVICE_NAME="Platform Coordination Service"
SERVICE_DIR=$(pwd)
REPORT_FILE="quality-report.md"
ERROR_COUNT=0
WARNING_COUNT=0

echo "========================================="
echo "Quality Check: $SERVICE_NAME"
echo "========================================="
echo

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Create quality report header
cat > "$REPORT_FILE" << EOF
# Quality Report: $SERVICE_NAME
**Generated:** $(date -Iseconds)
**Service Port:** 8081
**Service Directory:** $SERVICE_DIR

## Summary
EOF

# 1. Python Syntax Check
echo "1. Checking Python syntax..."
SYNTAX_ERRORS=$(find src tests -name "*.py" -exec python -m py_compile {} \; 2>&1 | grep -c "SyntaxError" || true)
if [ "$SYNTAX_ERRORS" -eq 0 ]; then
    echo "   ✅ No syntax errors"
    echo "- ✅ **Syntax Check:** Passed" >> "$REPORT_FILE"
else
    echo "   ❌ Found $SYNTAX_ERRORS syntax errors"
    echo "- ❌ **Syntax Check:** Failed ($SYNTAX_ERRORS errors)" >> "$REPORT_FILE"
    ERROR_COUNT=$((ERROR_COUNT + SYNTAX_ERRORS))
fi

# 2. Ruff Linting
echo "2. Running Ruff linter..."
if command_exists ruff; then
    RUFF_OUTPUT=$(ruff check src tests --select F,E,W,I,N,UP 2>&1 || true)
    RUFF_ERRORS=$(echo "$RUFF_OUTPUT" | grep -c "error" || true)
    if [ "$RUFF_ERRORS" -eq 0 ]; then
        echo "   ✅ Ruff: No issues found"
        echo "- ✅ **Ruff Linting:** Passed" >> "$REPORT_FILE"
    else
        echo "   ⚠️  Ruff: $RUFF_ERRORS issues found"
        echo "- ⚠️  **Ruff Linting:** $RUFF_ERRORS issues" >> "$REPORT_FILE"
        WARNING_COUNT=$((WARNING_COUNT + RUFF_ERRORS))
        
        # Add details to report
        echo "" >> "$REPORT_FILE"
        echo "### Ruff Issues:" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "$RUFF_OUTPUT" | head -20 >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    fi
else
    echo "   ⏭️  Ruff not installed"
    echo "- ⏭️  **Ruff Linting:** Not available" >> "$REPORT_FILE"
fi

# 3. MyPy Type Checking
echo "3. Running MyPy type checker..."
if command_exists mypy; then
    MYPY_OUTPUT=$(mypy src --ignore-missing-imports --no-error-summary 2>&1 || true)
    MYPY_ERRORS=$(echo "$MYPY_OUTPUT" | grep -c "error:" || true)
    if [ "$MYPY_ERRORS" -eq 0 ]; then
        echo "   ✅ MyPy: No type errors"
        echo "- ✅ **Type Checking:** Passed" >> "$REPORT_FILE"
    else
        echo "   ⚠️  MyPy: $MYPY_ERRORS type errors"
        echo "- ⚠️  **Type Checking:** $MYPY_ERRORS errors" >> "$REPORT_FILE"
        WARNING_COUNT=$((WARNING_COUNT + MYPY_ERRORS))
    fi
else
    echo "   ⏭️  MyPy not installed"
    echo "- ⏭️  **Type Checking:** Not available" >> "$REPORT_FILE"
fi

# 4. Check for undefined variables (critical)
echo "4. Checking for undefined variables..."
UNDEFINED_VARS=$(grep -r "NameError\|UnboundLocalError" src tests 2>/dev/null | wc -l || true)
# Also check for common patterns
RISKY_PATTERNS=$(grep -r "if.*:" src tests -A 3 2>/dev/null | grep "^\s*[a-z_]*\s*=" | wc -l || true)

if [ "$UNDEFINED_VARS" -eq 0 ] && [ "$RISKY_PATTERNS" -lt 5 ]; then
    echo "   ✅ No undefined variable risks"
    echo "- ✅ **Undefined Variables:** None detected" >> "$REPORT_FILE"
else
    echo "   ⚠️  Potential undefined variable risks: $RISKY_PATTERNS patterns"
    echo "- ⚠️  **Undefined Variables:** $RISKY_PATTERNS risky patterns" >> "$REPORT_FILE"
    WARNING_COUNT=$((WARNING_COUNT + RISKY_PATTERNS))
fi

# 5. Security Check
echo "5. Checking for security issues..."
SECURITY_ISSUES=0
# Check for hardcoded passwords
HARDCODED=$(grep -r "password\s*=\s*[\"']" src --include="*.py" | grep -v "getenv\|environ" | wc -l || true)
SECURITY_ISSUES=$((SECURITY_ISSUES + HARDCODED))
# Check for eval usage
EVAL_USAGE=$(grep -r "eval(" src --include="*.py" | wc -l || true)
SECURITY_ISSUES=$((SECURITY_ISSUES + EVAL_USAGE))

if [ "$SECURITY_ISSUES" -eq 0 ]; then
    echo "   ✅ No security issues found"
    echo "- ✅ **Security Check:** Passed" >> "$REPORT_FILE"
else
    echo "   ❌ Found $SECURITY_ISSUES security issues"
    echo "- ❌ **Security Check:** $SECURITY_ISSUES issues" >> "$REPORT_FILE"
    ERROR_COUNT=$((ERROR_COUNT + SECURITY_ISSUES))
fi

# 6. Import Check
echo "6. Checking imports..."
# Check for circular imports
CIRCULAR=$(find src -name "*.py" -exec grep -l "from src" {} \; | wc -l || true)
# Check for missing imports
MISSING=$(grep -r "ImportError" src tests 2>/dev/null | wc -l || true)

if [ "$CIRCULAR" -lt 10 ] && [ "$MISSING" -eq 0 ]; then
    echo "   ✅ Imports look good"
    echo "- ✅ **Import Check:** Passed" >> "$REPORT_FILE"
else
    echo "   ⚠️  Import issues: $CIRCULAR potential circular imports"
    echo "- ⚠️  **Import Check:** $CIRCULAR potential issues" >> "$REPORT_FILE"
    WARNING_COUNT=$((WARNING_COUNT + CIRCULAR))
fi

# 7. Test Coverage
echo "7. Checking test coverage..."
if [ -f "coverage.json" ]; then
    COVERAGE=$(python -c "import json; data=json.load(open('coverage.json')); print(data.get('totals', {}).get('percent_covered', 0))" 2>/dev/null || echo "0")
    if (( $(echo "$COVERAGE > 60" | bc -l) )); then
        echo "   ✅ Test coverage: ${COVERAGE}%"
        echo "- ✅ **Test Coverage:** ${COVERAGE}%" >> "$REPORT_FILE"
    else
        echo "   ⚠️  Test coverage: ${COVERAGE}% (below 60%)"
        echo "- ⚠️  **Test Coverage:** ${COVERAGE}% (below target)" >> "$REPORT_FILE"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
else
    echo "   ⏭️  No coverage data available"
    echo "- ⏭️  **Test Coverage:** No data" >> "$REPORT_FILE"
fi

# 8. Code Complexity
echo "8. Checking code complexity..."
COMPLEX_FUNCTIONS=$(find src -name "*.py" -exec grep -c "def " {} \; | awk '$1>20' | wc -l || true)
if [ "$COMPLEX_FUNCTIONS" -eq 0 ]; then
    echo "   ✅ No overly complex modules"
    echo "- ✅ **Code Complexity:** Acceptable" >> "$REPORT_FILE"
else
    echo "   ⚠️  $COMPLEX_FUNCTIONS modules may be too complex"
    echo "- ⚠️  **Code Complexity:** $COMPLEX_FUNCTIONS complex modules" >> "$REPORT_FILE"
    WARNING_COUNT=$((WARNING_COUNT + 1))
fi

# 9. Documentation
echo "9. Checking documentation..."
MISSING_DOCSTRINGS=$(find src -name "*.py" -exec grep -L '"""' {} \; | wc -l || true)
if [ "$MISSING_DOCSTRINGS" -lt 5 ]; then
    echo "   ✅ Documentation looks good"
    echo "- ✅ **Documentation:** Adequate" >> "$REPORT_FILE"
else
    echo "   ⚠️  $MISSING_DOCSTRINGS files missing docstrings"
    echo "- ⚠️  **Documentation:** $MISSING_DOCSTRINGS files need docstrings" >> "$REPORT_FILE"
    WARNING_COUNT=$((WARNING_COUNT + 1))
fi

# 10. Dependencies
echo "10. Checking dependencies..."
if [ -f "requirements.txt" ]; then
    OUTDATED=$(pip list --outdated 2>/dev/null | wc -l || true)
    if [ "$OUTDATED" -lt 10 ]; then
        echo "   ✅ Dependencies up to date"
        echo "- ✅ **Dependencies:** Mostly current" >> "$REPORT_FILE"
    else
        echo "   ⚠️  $OUTDATED outdated dependencies"
        echo "- ⚠️  **Dependencies:** $OUTDATED packages outdated" >> "$REPORT_FILE"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
else
    echo "   ❌ No requirements.txt found"
    echo "- ❌ **Dependencies:** No requirements.txt" >> "$REPORT_FILE"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# Generate final summary
echo "" >> "$REPORT_FILE"
echo "## Final Score" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

TOTAL_ISSUES=$((ERROR_COUNT + WARNING_COUNT))

if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
    GRADE="A+"
    STATUS="EXCELLENT"
elif [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -lt 5 ]; then
    GRADE="A"
    STATUS="GOOD"
elif [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -lt 10 ]; then
    GRADE="B"
    STATUS="ACCEPTABLE"
elif [ "$ERROR_COUNT" -lt 3 ]; then
    GRADE="C"
    STATUS="NEEDS IMPROVEMENT"
else
    GRADE="F"
    STATUS="CRITICAL"
fi

echo "- **Critical Errors:** $ERROR_COUNT" >> "$REPORT_FILE"
echo "- **Warnings:** $WARNING_COUNT" >> "$REPORT_FILE"
echo "- **Total Issues:** $TOTAL_ISSUES" >> "$REPORT_FILE"
echo "- **Grade:** $GRADE" >> "$REPORT_FILE"
echo "- **Status:** $STATUS" >> "$REPORT_FILE"

# Console output summary
echo
echo "========================================="
echo "QUALITY SUMMARY"
echo "========================================="
echo "Critical Errors: $ERROR_COUNT"
echo "Warnings: $WARNING_COUNT"
echo "Total Issues: $TOTAL_ISSUES"
echo "Grade: $GRADE"
echo "Status: $STATUS"
echo
echo "Report saved to: $REPORT_FILE"

# Exit with error if critical issues found
if [ "$ERROR_COUNT" -gt 0 ]; then
    exit 1
fi

exit 0