#!/usr/bin/env python3
"""Script to add structlog dependency to the project."""

import re
from pathlib import Path


def add_structlog_dependency():
    """Add structlog to the project dependencies."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    if not pyproject_path.exists():
        print("❌ pyproject.toml not found!")
        return False
    
    content = pyproject_path.read_text()
    
    # Find the dependencies section
    pattern = r'(\[project\.dependencies\]\n(?:[^[]+))'
    match = re.search(pattern, content, re.MULTILINE)
    
    if not match:
        print("❌ Could not find [project.dependencies] section")
        return False
    
    dependencies_section = match.group(1)
    
    # Check if structlog is already present
    if "structlog" in dependencies_section:
        print("✓ structlog is already in dependencies")
        return True
    
    # Add structlog after python-dotenv
    new_dependencies = dependencies_section.replace(
        'python-dotenv = "==1.0.1"',
        'python-dotenv = "==1.0.1"\nstructlog = "==24.1.0"'
    )
    
    # Replace in the content
    new_content = content.replace(dependencies_section, new_dependencies)
    
    # Write back
    pyproject_path.write_text(new_content)
    print("✓ Added structlog==24.1.0 to dependencies")
    
    return True


def main():
    """Main function."""
    print("🔧 Adding structlog dependency...")
    
    if add_structlog_dependency():
        print("\n✅ Success! Now run: pip install -e .[dev]")
    else:
        print("\n❌ Failed to add dependency")


if __name__ == "__main__":
    main()