#!/usr/bin/env python3
"""
Test runner script for WinGet Manifest Generator Tool.

This script provides a convenient way to run different types of tests
with various configurations and options.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Test runner for the WinGet Manifest Generator Tool."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        
    def run_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        print(f"Running: {' '.join(command)}")
        return subprocess.run(command, check=check, cwd=self.project_root)
    
    def install_dependencies(self) -> None:
        """Install required dependencies."""
        print("Installing dependencies...")
        self.run_command([sys.executable, "-m", "pip", "install", "-r", "src/requirements.txt"])
        
        # Install additional testing dependencies
        test_deps = [
            "pytest-cov", "pytest-xdist", "pytest-asyncio", "pytest-html",
            "pytest-benchmark", "coverage", "black", "flake8", "mypy"
        ]
        self.run_command([sys.executable, "-m", "pip", "install"] + test_deps)
    
    def run_tests(self, test_type: str = "all", verbose: bool = True, 
                  coverage: bool = False, parallel: bool = False,
                  markers: Optional[str] = None, output_file: Optional[str] = None) -> None:
        """Run tests with specified options."""
        
        command = [sys.executable, "-m", "pytest"]
        
        # Determine test directory
        if test_type == "unit":
            command.append(str(self.test_dir / "unit"))
            if not markers:
                markers = "unit or (not integration and not e2e)"
        elif test_type == "integration":
            command.append(str(self.test_dir / "integration"))
            if not markers:
                markers = "integration"
        elif test_type == "e2e":
            command.append(str(self.test_dir / "e2e"))
            if not markers:
                markers = "e2e"
        else:  # all
            command.append(str(self.test_dir))
        
        # Add options
        if verbose:
            command.append("-v")
        
        if coverage:
            command.extend([
                f"--cov={self.src_dir}",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        if parallel:
            command.extend(["-n", "auto"])
        
        if markers:
            command.extend(["-m", markers])
        
        if output_file:
            command.extend(["--html", output_file, "--self-contained-html"])
        
        # Set environment variables for testing
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(self.project_root),
            "TOKEN_1": "test_token_123",  # Mock token for tests
            "TOKEN_2": "test_token_456",
        })
        
        try:
            subprocess.run(command, check=True, cwd=self.project_root, env=env)
        except subprocess.CalledProcessError as e:
            print(f"Tests failed with exit code {e.returncode}")
            sys.exit(e.returncode)
    
    def run_linting(self) -> None:
        """Run linting checks."""
        print("Running linting checks...")
        
        # Flake8
        try:
            self.run_command([
                sys.executable, "-m", "flake8", 
                str(self.src_dir), str(self.test_dir),
                "--max-line-length=88", 
                "--extend-ignore=E203,W503"
            ])
            print("✓ Flake8 checks passed")
        except subprocess.CalledProcessError:
            print("✗ Flake8 checks failed")
    
    def run_type_checking(self) -> None:
        """Run type checking with mypy."""
        print("Running type checking...")
        
        try:
            self.run_command([
                sys.executable, "-m", "mypy", 
                str(self.src_dir),
                "--ignore-missing-imports"
            ])
            print("✓ Type checking passed")
        except subprocess.CalledProcessError:
            print("✗ Type checking failed")
    
    def format_code(self, check_only: bool = False) -> None:
        """Format code with black."""
        print(f"{'Checking' if check_only else 'Formatting'} code style...")
        
        command = [
            sys.executable, "-m", "black",
            str(self.src_dir), str(self.test_dir),
            "--line-length=88"
        ]
        
        if check_only:
            command.append("--check")
        
        try:
            self.run_command(command)
            print(f"✓ Code {'style check passed' if check_only else 'formatted successfully'}")
        except subprocess.CalledProcessError:
            print(f"✗ Code {'style check failed' if check_only else 'formatting failed'}")
    
    def run_security_checks(self) -> None:
        """Run security checks."""
        print("Running security checks...")
        
        try:
            # Try to run bandit
            self.run_command([
                sys.executable, "-m", "bandit", 
                "-r", str(self.src_dir),
                "-f", "json",
                "-o", "security-report.json"
            ])
            print("✓ Security checks completed - report saved to security-report.json")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("! Bandit not available, skipping security checks")
            print("  Install with: pip install bandit")
    
    def generate_coverage_report(self) -> None:
        """Generate a detailed coverage report."""
        print("Generating coverage report...")
        
        # Run tests with coverage
        self.run_tests(coverage=True)
        
        # Generate additional reports
        try:
            self.run_command([sys.executable, "-m", "coverage", "xml"])
            self.run_command([sys.executable, "-m", "coverage", "json"])
            print("✓ Coverage reports generated (HTML, XML, JSON)")
        except subprocess.CalledProcessError:
            print("✗ Failed to generate additional coverage reports")
    
    def clean_artifacts(self) -> None:
        """Clean up test artifacts and cache files."""
        print("Cleaning up artifacts...")
        
        import shutil
        
        cleanup_paths = [
            "htmlcov", ".pytest_cache", ".coverage", ".mypy_cache",
            "test-report.html", "security-report.json", "coverage.xml", "coverage.json"
        ]
        
        for path in cleanup_paths:
            full_path = self.project_root / path
            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
                print(f"  Removed {path}")
        
        # Remove __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
        
        print("✓ Cleanup completed")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Test runner for WinGet Manifest Generator Tool")
    
    parser.add_argument(
        "command",
        choices=["install", "test", "lint", "format", "typecheck", "security", "coverage", "clean", "all"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--test-type",
        choices=["all", "unit", "integration", "e2e"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--markers",
        type=str,
        help="Pytest markers to filter tests"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for test results (HTML format)"
    )
    
    parser.add_argument(
        "--format-check",
        action="store_true",
        help="Only check code formatting without making changes"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.command == "install":
            runner.install_dependencies()
        
        elif args.command == "test":
            runner.run_tests(
                test_type=args.test_type,
                verbose=not args.quiet,
                coverage=not args.no_coverage,
                parallel=args.parallel,
                markers=args.markers,
                output_file=args.output
            )
        
        elif args.command == "lint":
            runner.run_linting()
        
        elif args.command == "format":
            runner.format_code(check_only=args.format_check)
        
        elif args.command == "typecheck":
            runner.run_type_checking()
        
        elif args.command == "security":
            runner.run_security_checks()
        
        elif args.command == "coverage":
            runner.generate_coverage_report()
        
        elif args.command == "clean":
            runner.clean_artifacts()
        
        elif args.command == "all":
            print("Running complete test suite...")
            runner.install_dependencies()
            runner.format_code(check_only=True)
            runner.run_linting()
            runner.run_type_checking()
            runner.run_tests(
                test_type="all",
                verbose=not args.quiet,
                coverage=True,
                parallel=args.parallel
            )
            runner.run_security_checks()
            print("✓ All checks completed successfully!")
        
    except KeyboardInterrupt:
        print("\n! Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"! Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
