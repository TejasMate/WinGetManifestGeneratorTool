#!/usr/bin/env python3
"""
WinGet Manifest Automation Tool - Get Started Script

This script provides a simple way to run the traditional three-step workflow:
1. PackageProcessor.py - Process WinGet package manifests
2. GitHub.py - Analyze GitHub repositories and apply enhanced filtering
3. KomacCommandsGenerator.py - Generate komac update commands

Usage:
    python get_started.py [--step STEP_NUMBER] [--all]
    
Examples:
    python get_started.py --all           # Run all steps sequentially
    python get_started.py --step 1        # Run only PackageProcessor
    python get_started.py --step 2        # Run only GitHub analysis
    python get_started.py --step 3        # Run only Komac generation
"""

import sys
import argparse
import logging
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_logging():
    """Configure logging for the workflow."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("workflow.log")
        ]
    )

def print_banner():
    """Print the welcome banner."""
    print("=" * 70)
    print("🚀 WinGet Manifest Automation Tool")
    print("   Enhanced Multi-Source Package Processing")
    print("=" * 70)

def print_step_header(step_num: int, step_name: str, description: str):
    """Print a formatted header for each step."""
    print(f"\n{'='*20} STEP {step_num}: {step_name} {'='*20}")
    print(f"📋 {description}")
    print("-" * 70)

def run_package_processor():
    """Run Step 1: Optimized Package Processing."""
    print_step_header(1, "PACKAGE PROCESSING", "Processing WinGet package manifests with optimized workflow")
    
    try:
        # Import and run PackageProcessor
        from PackageProcessor import main as package_processor_main
        
        start_time = time.time()
        print("🔄 Starting optimized package processing...")
        print("💡 Note: PackageNames.csv is no longer generated (package names are in AllPackageInfo.csv)")
        
        # Run the processor
        package_processor_main()
        
        end_time = time.time()
        print(f"✅ Package processing completed in {end_time - start_time:.2f} seconds")
        print("📄 Output: data/AllPackageInfo.csv (contains package names + analysis data)")
        print("📄 Output: data/OpenPRs.csv (open pull requests data)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in package processing: {str(e)}")
        logging.error(f"Package processing failed: {str(e)}")
        return False

def run_github_analysis():
    """Run Step 2: GitHub Analysis with Enhanced Filtering."""
    print_step_header(2, "GITHUB ANALYSIS", "Analyzing GitHub repositories and applying enhanced filtering")
    
    try:
        # Import and run GitHub analysis
        from GitHub import main as github_main
        
        start_time = time.time()
        print("🔄 Starting GitHub analysis and filtering...")
        
        # Run the GitHub analysis
        github_main()
        
        end_time = time.time()
        print(f"✅ GitHub analysis completed in {end_time - start_time:.2f} seconds")
        print("📄 Outputs:")
        print("   - Multiple filtered CSV files (GitHubPackageInfo_FilterX.csv)")
        print("   - Individual removed package files (FilterX_Removed.csv)")
        print("   - Combined removed packages (RemovedRows.csv)")
        print("   - Comprehensive summary (FilteringSummary.md)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in GitHub analysis: {str(e)}")
        logging.error(f"GitHub analysis failed: {str(e)}")
        return False

def run_komac_generation():
    """Run Step 3: Komac Commands Generation."""
    print_step_header(3, "KOMAC GENERATION", "Generating komac update commands for valid packages")
    
    try:
        # Import and run Komac generation
        from KomacCommandsGenerator import generate_komac_commands_github
        
        start_time = time.time()
        print("🔄 Generating komac commands...")
        
        # Run the command generation
        generate_komac_commands_github()
        
        end_time = time.time()
        print(f"✅ Komac command generation completed in {end_time - start_time:.2f} seconds")
        print("📄 Output: data/github/komac_update_commands_github.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in komac generation: {str(e)}")
        logging.error(f"Komac generation failed: {str(e)}")
        return False

def run_all_steps():
    """Run all three steps sequentially."""
    print("🚀 Running complete workflow (all 3 steps)")
    
    total_start_time = time.time()
    success_count = 0
    
    # Step 1: Package Processing
    if run_package_processor():
        success_count += 1
    else:
        print("❌ Stopping workflow due to failure in Step 1")
        return False
    
    # Step 2: GitHub Analysis
    if run_github_analysis():
        success_count += 1
    else:
        print("❌ Stopping workflow due to failure in Step 2")
        return False
    
    # Step 3: Komac Generation
    if run_komac_generation():
        success_count += 1
    else:
        print("❌ Stopping workflow due to failure in Step 3")
        return False
    
    total_end_time = time.time()
    
    # Final summary
    print(f"\n{'='*70}")
    print("🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
    print(f"✅ All {success_count}/3 steps completed")
    print(f"⏱️  Total time: {total_end_time - total_start_time:.2f} seconds")
    print("\n📊 Key Outputs:")
    print("   1. data/AllPackageInfo.csv - Complete package data (names + analysis)")
    print("   2. data/OpenPRs.csv - Open pull requests data") 
    print("   3. data/github/FilteringSummary.md - Detailed filtering report")
    print("   4. data/github/komac_update_commands_github.txt - Update commands")
    print("\n💡 Optimization Notes:")
    print("   • PackageNames.csv no longer generated (redundant with AllPackageInfo.csv)")
    print("   • Improved processing efficiency and reduced memory usage")
    print("   • Enhanced error handling and performance monitoring")
    print("\n💡 Next Steps:")
    print("   - Review FilteringSummary.md to understand filtering results")
    print("   - Check individual FilterX_Removed.csv files for analysis")
    print("   - Run the komac commands to update WinGet packages")
    print("="*70)
    
    return True

def main():
    """Main entry point for the get started script."""
    parser = argparse.ArgumentParser(
        description="WinGet Manifest Automation Tool - Sequential Workflow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python get_started.py --all           # Run all steps sequentially
    python get_started.py --step 1        # Run only PackageProcessor
    python get_started.py --step 2        # Run only GitHub analysis  
    python get_started.py --step 3        # Run only Komac generation
    
Steps:
    1. Package Processing - Extract and process WinGet manifest data
    2. GitHub Analysis - Fetch GitHub data and apply enhanced filtering
    3. Komac Generation - Generate update commands for valid packages
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run all steps sequentially")
    group.add_argument("--step", type=int, choices=[1, 2, 3], 
                      help="Run specific step (1=PackageProcessor, 2=GitHub, 3=Komac)")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Print banner
    print_banner()
    
    # Change to project directory
    project_dir = Path(__file__).parent
    sys.path.insert(0, str(project_dir / "src"))
    
    # Run the requested operation
    success = False
    
    if args.all:
        success = run_all_steps()
    elif args.step == 1:
        success = run_package_processor()
    elif args.step == 2:
        success = run_github_analysis()
    elif args.step == 3:
        success = run_komac_generation()
    
    # Exit with appropriate code
    if success:
        print("\n🎉 Operation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Operation failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
