#!/usr/bin/env python3
"""
Script to organize removed rows by filter reason.
This is now a wrapper around the Filter.py functionality.
"""
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from winget_automation.github.Filter import organize_removed_rows_by_filter

def main():
    """
    Main function to organize removed rows.
    """
    try:
        workspace_dir = Path("/workspaces/WinGetManifestAutomationTool")
        removed_rows_path = workspace_dir / "data" / "RemovedRows.csv"
        output_dir = workspace_dir / "data"
        
        if not removed_rows_path.exists():
            print(f"❌ RemovedRows.csv not found at: {removed_rows_path}")
            print("Please run the filter process first to generate RemovedRows.csv")
            return
        
        print("🔄 Organizing removed rows by filter reason...")
        organize_removed_rows_by_filter(str(removed_rows_path), str(output_dir))
        print("✅ Organization completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
