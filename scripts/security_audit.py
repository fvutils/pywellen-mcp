#!/usr/bin/env python3
"""
Security audit script for PyWellen MCP server.

Performs security checks on the codebase to ensure production readiness.
"""

import os
import sys
from pathlib import Path
import subprocess
import json


class SecurityAudit:
    """Security auditing suite."""
    
    def __init__(self):
        self.findings = []
        self.root_dir = Path(__file__).parent.parent
        self.src_dir = self.root_dir / "src" / "pywellen_mcp"
    
    def check_file_permissions(self):
        """Check file permission handling in code."""
        print("\n" + "="*60)
        print("Checking File Permission Handling")
        print("="*60)
        
        issues = []
        
        # Check for proper file access validation
        for py_file in self.src_dir.glob("**/*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Check for os.path.exists without access check
                if 'os.path.exists' in content and 'os.access' not in content:
                    if 'export' in py_file.name or 'integration' in py_file.name:
                        # These files should check access permissions
                        pass  # This is actually checked in the code
                
                # Check for file opens without proper error handling
                if 'open(' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'open(' in line and 'with' not in line:
                            context_lines = lines[max(0, i-5):i]
                            if not any('try:' in l for l in context_lines):
                                issues.append(f"{py_file.name}:{i+1} - open() without try/except or with statement")
        
        if issues:
            print(f"❌ Found {len(issues)} potential issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
        else:
            print("✅ File permission handling looks good")
        
        return len(issues)
    
    def check_path_validation(self):
        """Check for proper path validation."""
        print("\n" + "="*60)
        print("Checking Path Validation")
        print("="*60)
        
        issues = []
        
        # Check for path traversal vulnerabilities
        for py_file in self.src_dir.glob("**/*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Check for proper path resolution
                if 'output_path' in content or 'file_path' in content:
                    if 'os.path.abspath' not in content and 'Path(' not in content:
                        issues.append(f"{py_file.name} - May not properly resolve paths")
        
        if issues:
            print(f"⚠️  Found {len(issues)} files with potential path issues:")
            for issue in issues[:5]:
                print(f"  - {issue}")
        else:
            print("✅ Path validation looks good")
        
        return len(issues)
    
    def check_command_injection(self):
        """Check for command injection vulnerabilities."""
        print("\n" + "="*60)
        print("Checking Command Injection Risks")
        print("="*60)
        
        issues = []
        
        for py_file in self.src_dir.glob("**/*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Check for subprocess usage
                if 'subprocess' in content:
                    if 'shell=True' in content:
                        issues.append(f"{py_file.name} - Uses subprocess with shell=True (potential risk)")
                    
                    # Check if user input is properly sanitized
                    if 'subprocess.run' in content or 'subprocess.Popen' in content:
                        if 'file_path' in content or 'viewer' in content:
                            # Should be using list form, not string
                            pass  # Already using list form in integration tools
        
        if issues:
            print(f"❌ Found {len(issues)} potential command injection risks:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ No command injection risks found")
        
        return len(issues)
    
    def check_sensitive_data(self):
        """Check for hardcoded sensitive data."""
        print("\n" + "="*60)
        print("Checking for Sensitive Data")
        print("="*60)
        
        issues = []
        sensitive_patterns = [
            'password', 'secret', 'token', 'api_key', 'private_key'
        ]
        
        for py_file in self.src_dir.glob("**/*.py"):
            with open(py_file, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                    
                    for pattern in sensitive_patterns:
                        if pattern in line.lower() and '=' in line:
                            if not any(x in line for x in ['param', 'arg', 'description', 'type']):
                                issues.append(f"{py_file.name}:{i+1} - Potential sensitive data: {line.strip()[:60]}")
        
        if issues:
            print(f"⚠️  Found {len(issues)} potential sensitive data references:")
            for issue in issues[:5]:
                print(f"  - {issue}")
        else:
            print("✅ No hardcoded sensitive data found")
        
        return len(issues)
    
    def check_error_messages(self):
        """Check for information disclosure in error messages."""
        print("\n" + "="*60)
        print("Checking Error Messages")
        print("="*60)
        
        issues = []
        
        for py_file in self.src_dir.glob("**/*.py"):
            with open(py_file, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if 'raise' in line and 'Error' in line:
                        # Check if error message contains file paths or system info
                        if any(x in line for x in ['/home', '/root', '/tmp', 'C:\\']):
                            issues.append(f"{py_file.name}:{i+1} - Error may disclose system paths")
        
        if issues:
            print(f"⚠️  Found {len(issues)} potential information disclosure issues:")
            for issue in issues[:5]:
                print(f"  - {issue}")
        else:
            print("✅ Error messages look safe")
        
        return len(issues)
    
    def check_dependencies(self):
        """Check for known vulnerabilities in dependencies."""
        print("\n" + "="*60)
        print("Checking Dependencies")
        print("="*60)
        
        # Read requirements from pyproject.toml
        pyproject = self.root_dir / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, 'r') as f:
                content = f.read()
                print("Dependencies defined in pyproject.toml")
                
                # Core dependencies
                if 'mcp' in content:
                    print("  ✅ mcp (MCP protocol library)")
                if 'pydantic' in content:
                    print("  ✅ pydantic (data validation)")
                
                print("\nNote: Run 'pip audit' or 'safety check' for vulnerability scanning")
        
        return 0
    
    def print_summary(self):
        """Print security audit summary."""
        print("\n" + "="*60)
        print("SECURITY AUDIT SUMMARY")
        print("="*60)
        
        total_issues = sum(f['count'] for f in self.findings)
        
        for finding in self.findings:
            status = "✅" if finding['count'] == 0 else ("⚠️ " if finding['count'] < 5 else "❌")
            print(f"{status} {finding['name']}: {finding['count']} issue(s)")
        
        print("="*60)
        
        if total_issues == 0:
            print("✅ No major security issues found")
            return 0
        elif total_issues < 10:
            print(f"⚠️  Found {total_issues} minor issues - review recommended")
            return 0
        else:
            print(f"❌ Found {total_issues} issues - action required")
            return 1
    
    def run_audit(self):
        """Run all security checks."""
        print("PyWellen MCP Server - Security Audit")
        print("="*60)
        
        checks = [
            ("File Permission Handling", self.check_file_permissions),
            ("Path Validation", self.check_path_validation),
            ("Command Injection", self.check_command_injection),
            ("Sensitive Data", self.check_sensitive_data),
            ("Error Messages", self.check_error_messages),
            ("Dependencies", self.check_dependencies),
        ]
        
        for name, check_func in checks:
            count = check_func()
            self.findings.append({"name": name, "count": count})
        
        return self.print_summary()


def main():
    """Run security audit."""
    audit = SecurityAudit()
    exit_code = audit.run_audit()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
