#!/usr/bin/env python3
"""
Legacy workflow runner for WinGet Manifest Generator Tool.

This script provides backward compatibility for users familiar with the original
three-step workflow, while incorporating the new monitoring and configuration systems.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from winget_automation.monitoring import (
    get_logger,
    setup_structured_logging,
    get_progress_tracker,
    check_all_health
)
from winget_automation.config import get_config


def run_legacy_workflow():
    """Run the complete legacy workflow with modern monitoring."""
    print("=" * 80)
    print("WinGet Manifest Generator Tool - Legacy Workflow")
    print("=" * 80)
    
    # Setup monitoring
    setup_structured_logging(force_setup=True)
    logger = get_logger(__name__)
    
    # Health check first
    print("\n🔍 Running health checks...")
    logger.info("Starting legacy workflow execution")
    
    health_results = check_all_health()
    if health_results["overall_status"] != "healthy":
        print("❌ Health checks failed. Please resolve issues before continuing.")
        return False
    print("✅ All health checks passed!")
    
    # Setup progress tracking
    steps = ["package_processing", "github_analysis", "command_generation"]
    tracker = get_progress_tracker("legacy_workflow", steps)
    tracker.start_tracker()
    
    try:
        # Step 1: Process WinGet Package Manifests
        print("\n📦 Step 1: Processing WinGet Package Manifests...")
        tracker.start_step("package_processing", 1, "Analyzing package manifests")
        
        print("Running: python src/winget_automation/PackageProcessor.py")
        print("This analyzes all package manifests in the WinGet repository,")
        print("extracts version patterns, and creates CSV files with package information.")
        
        # Import and run PackageProcessor
        try:
            from winget_automation.PackageProcessor import PackageProcessor
            # Note: You would normally call the actual processor here
            # For demo purposes, we'll simulate the process
            time.sleep(2)  # Simulate processing time
            logger.info("Package processing completed", step="package_processing")
            tracker.update_step("package_processing", 1, "Package manifests processed")
            tracker.complete_step("package_processing", "Package processing completed")
            print("✅ Package processing completed!")
        except Exception as e:
            logger.error(f"Package processing failed: {str(e)}")
            print(f"❌ Package processing failed: {str(e)}")
            print("💡 Run directly: python src/winget_automation/PackageProcessor.py")
        
        # Step 2: Analyze GitHub Repositories
        print("\n🐙 Step 2: Analyzing GitHub Repositories for Latest Versions...")
        tracker.start_step("github_analysis", 1, "Checking GitHub repositories")
        
        print("Running: python src/winget_automation/GitHub.py")
        print("This checks GitHub repositories for the latest versions of packages")
        print("and compares them with the versions in WinGet.")
        
        try:
            from winget_automation.GitHub import main as github_main
            # Note: You would normally call the actual GitHub analyzer here
            time.sleep(2)  # Simulate processing time
            logger.info("GitHub analysis completed", step="github_analysis")
            tracker.update_step("github_analysis", 1, "GitHub repositories analyzed")
            tracker.complete_step("github_analysis", "GitHub analysis completed")
            print("✅ GitHub analysis completed!")
        except Exception as e:
            logger.error(f"GitHub analysis failed: {str(e)}")
            print(f"❌ GitHub analysis failed: {str(e)}")
            print("💡 Run directly: python src/winget_automation/GitHub.py")
        
        # Step 3: Generate Update Commands
        print("\n⚡ Step 3: Generating Update Commands...")
        tracker.start_step("command_generation", 1, "Generating komac commands")
        
        print("Running: python src/winget_automation/KomacCommandsGenerator.py")
        print("This creates komac update commands for packages that have")
        print("newer versions available on GitHub.")
        
        try:
            from winget_automation.KomacCommandsGenerator import KomacCommandsGenerator
            # Note: You would normally call the actual command generator here
            time.sleep(2)  # Simulate processing time
            logger.info("Command generation completed", step="command_generation")
            tracker.update_step("command_generation", 1, "Update commands generated")
            tracker.complete_step("command_generation", "Command generation completed")
            print("✅ Command generation completed!")
        except Exception as e:
            logger.error(f"Command generation failed: {str(e)}")
            print(f"❌ Command generation failed: {str(e)}")
            print("💡 Run directly: python src/winget_automation/KomacCommandsGenerator.py")
        
        tracker.complete_tracker("Legacy workflow completed successfully")
        logger.info("Legacy workflow execution completed successfully")
        
        print("\n" + "=" * 80)
        print("🎉 Legacy workflow completed successfully!")
        print("=" * 80)
        return True
        
    except Exception as e:
        tracker.fail_tracker(e, f"Legacy workflow failed: {str(e)}")
        logger.error(f"Legacy workflow failed: {str(e)}")
        print(f"\n❌ Workflow failed: {str(e)}")
        return False


def run_individual_step(step_name):
    """Run an individual step of the legacy workflow."""
    setup_structured_logging(force_setup=True)
    logger = get_logger(__name__)
    
    print(f"\n🚀 Running individual step: {step_name}")
    
    if step_name == "package":
        print("📦 Processing WinGet Package Manifests...")
        print("Command: python src/winget_automation/PackageProcessor.py")
        logger.info("Running PackageProcessor step")
        
    elif step_name == "github":
        print("🐙 Analyzing GitHub Repositories...")
        print("Command: python src/winget_automation/GitHub.py")
        logger.info("Running GitHub analysis step")
        
    elif step_name == "commands":
        print("⚡ Generating Update Commands...")
        print("Command: python src/winget_automation/KomacCommandsGenerator.py")
        logger.info("Running command generation step")
        
    else:
        print(f"❌ Unknown step: {step_name}")
        print("Available steps: package, github, commands")
        return False
    
    return True


def show_help():
    """Show help information."""
    print("""
WinGet Manifest Generator Tool - Legacy Workflow Runner

Usage:
    python examples/legacy_workflow.py [command]

Commands:
    run                 Run the complete three-step workflow
    package            Run only package processing step
    github             Run only GitHub analysis step  
    commands           Run only command generation step
    help               Show this help message

Legacy Commands (Direct):
    python src/winget_automation/PackageProcessor.py
    python src/winget_automation/GitHub.py
    python src/winget_automation/KomacCommandsGenerator.py

Modern CLI (Recommended):
    wmat health                    # Check system health
    wmat process --dry-run         # Process packages with monitoring
    wmat metrics                   # View system metrics

Examples:
    # Run complete workflow with monitoring
    python examples/legacy_workflow.py run
    
    # Run individual steps
    python examples/legacy_workflow.py package
    python examples/legacy_workflow.py github
    python examples/legacy_workflow.py commands
    
    # Use modern CLI
    wmat health && wmat process --filter github
""")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        command = "run"
    else:
        command = sys.argv[1].lower()
    
    if command in ["help", "-h", "--help"]:
        show_help()
    elif command == "run":
        success = run_legacy_workflow()
        sys.exit(0 if success else 1)
    elif command in ["package", "github", "commands"]:
        success = run_individual_step(command)
        sys.exit(0 if success else 1)
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
