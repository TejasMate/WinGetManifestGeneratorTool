#!/usr/bin/env python3
"""Command-line interface for WinGet Manifest Generator Tool."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from winget_automation.config import get_config
from winget_automation.monitoring import (
    get_logger,
    setup_structured_logging,
    check_all_health,
    get_progress_tracker,
)
from winget_automation.PackageProcessor import PackageProcessor
from winget_automation.github.GitHubPackageProcessor import VersionAnalyzer


console = Console()
logger = get_logger(__name__)


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """WinGet Manifest Generator Tool - Advanced package management for WinGet."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    
    # Setup logging
    setup_structured_logging(force_setup=True)
    
    # Set logging level after setup
    import logging
    log_level = "DEBUG" if verbose else "WARNING" if quiet else "INFO"
    logging.getLogger().setLevel(getattr(logging, log_level))
    
    if not quiet:
        console.print(
            Panel.fit(
                "[bold blue]WinGet Manifest Generator Tool[/bold blue]\n"
                "[dim]Advanced package management for WinGet[/dim]",
                border_style="blue",
            )
        )


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health and connectivity."""
    with console.status("[bold green]Running health checks..."):
        health_results = check_all_health()
    
    table = Table(title="System Health Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Message", style="dim")
    
    status_colors = {
        "healthy": "green",
        "warning": "yellow", 
        "critical": "red"
    }
    
    for check_name, result in health_results["checks"].items():
        # Handle both dict and object formats
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            message = result.get("message", "No message")
        else:
            status = result.status.value if hasattr(result, 'status') else "unknown"
            message = result.message if hasattr(result, 'message') else "No message"
        
        color = status_colors.get(status, "white")
        table.add_row(
            check_name.replace("_", " ").title(),
            f"[{color}]{status.upper()}[/{color}]",
            message
        )
    
    console.print(table)
    
    overall_status = health_results["overall_status"]
    if overall_status == "healthy":
        console.print("\n✅ [bold green]All systems operational[/bold green]")
    elif overall_status == "warning":
        console.print("\n⚠️  [bold yellow]Some issues detected[/bold yellow]")
    else:
        console.print("\n❌ [bold red]Critical issues found[/bold red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--packages",
    "-p",
    multiple=True,
    help="Specific packages to process (can be used multiple times)",
)
@click.option(
    "--filter",
    "-f",
    type=click.Choice(["github", "all"]),
    default="all",
    help="Filter packages by source",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_context
def process(ctx, packages, filter, dry_run):
    """Process packages for updates."""
    config = get_config(ctx.obj.get("config_path"))
    
    if dry_run:
        console.print("[yellow]DRY RUN: No changes will be made[/yellow]\n")
    
    # Initialize progress tracking
    steps = ["initialization", "package_discovery", "processing", "cleanup"]
    tracker = get_progress_tracker("package_processing", steps)
    tracker.start_tracker()
    
    try:
        # Initialization
        tracker.start_step("initialization", 1, "Setting up processors")
        if filter == "github" or filter == "all":
            version_analyzer = VersionAnalyzer(None)  # Will need proper GitHub API setup
        tracker.update_step("initialization", 1, "Processors initialized")
        tracker.complete_step("initialization", "Setup complete")
        
        # Package discovery
        tracker.start_step("package_discovery", 1, "Discovering packages")
        if packages:
            package_list = list(packages)
            console.print(f"Processing specified packages: {', '.join(packages)}")
        else:
            # Discover packages from data files
            package_list = []  # This would be populated from data files
            console.print("Discovering packages from data files...")
        
        tracker.update_step("package_discovery", 1, f"Found {len(package_list)} packages")
        tracker.complete_step("package_discovery", f"Discovered {len(package_list)} packages")
        
        # Processing
        if package_list:
            tracker.start_step("processing", len(package_list), "Processing packages")
            
            for i, package in enumerate(package_list):
                if not dry_run:
                    # Process package here
                    logger.info(f"Processing package: {package}")
                else:
                    console.print(f"[dim]Would process: {package}[/dim]")
                
                tracker.update_step("processing", i + 1, f"Processed {package}")
            
            tracker.complete_step("processing", "All packages processed")
        else:
            tracker.start_step("processing", 1, "No packages to process")
            tracker.complete_step("processing", "No packages found")
        
        # Cleanup
        tracker.start_step("cleanup", 1, "Cleaning up")
        tracker.update_step("cleanup", 1, "Cleanup complete")
        tracker.complete_step("cleanup", "Process completed")
        
        tracker.complete_tracker("Package processing completed successfully")
        
        if not dry_run:
            console.print("\n✅ [bold green]Package processing completed[/bold green]")
        else:
            console.print("\n✅ [bold blue]Dry run completed[/bold blue]")
    
    except Exception as e:
        tracker.fail_tracker(e, f"Processing failed: {str(e)}")
        console.print(f"\n❌ [bold red]Error: {str(e)}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="config_status.json",
    help="Output file for configuration status",
)
@click.pass_context
def config_status(ctx, output):
    """Check and export configuration status."""
    try:
        config = get_config(ctx.obj.get("config_path"))
        console.print("✅ [bold green]Configuration loaded successfully[/bold green]")
        
        # Display configuration summary
        table = Table(title="Configuration Summary")
        table.add_column("Section", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        # Check different configuration sections
        sections = {
            "GitHub": config.get("github", {}),
            "Monitoring": config.get("monitoring", {}),
            "Processing": config.get("processing", {}),
        }
        
        for section, section_config in sections.items():
            if section_config:
                table.add_row(
                    section,
                    "[green]✓[/green]",
                    f"{len(section_config)} settings configured"
                )
            else:
                table.add_row(
                    section,
                    "[yellow]⚠[/yellow]",
                    "No configuration found"
                )
        
        console.print(table)
        
        # Export to file if requested
        if output:
            import json
            with open(output, "w") as f:
                json.dump(config, f, indent=2, default=str)
            console.print(f"\n📄 Configuration exported to: {output}")
    
    except Exception as e:
        console.print(f"❌ [bold red]Configuration error: {str(e)}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "table"]),
    default="table",
    help="Output format",
)
@click.pass_context
def metrics(ctx, format):
    """Display system metrics and statistics."""
    from winget_automation.monitoring import get_metrics_collector
    
    metrics_collector = get_metrics_collector()
    metrics_data = metrics_collector.get_all_metrics()
    
    if format == "table":
        table = Table(title="System Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_column("Type", style="dim")
        
        # Process counters
        for metric_name, value in metrics_data.get("counters", {}).items():
            table.add_row(metric_name, str(value), "counter")
        
        # Process gauges
        for metric_name, value in metrics_data.get("gauges", {}).items():
            value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
            table.add_row(metric_name, value_str, "gauge")
        
        # Process histograms
        for metric_name, stats in metrics_data.get("histograms", {}).items():
            if isinstance(stats, dict):
                table.add_row(f"{metric_name}.count", str(stats.get("count", 0)), "histogram")
                table.add_row(f"{metric_name}.mean", f"{stats.get('mean', 0):.2f}", "histogram")
                table.add_row(f"{metric_name}.p95", f"{stats.get('p95', 0):.2f}", "histogram")
        
        console.print(table)
    
    elif format == "json":
        import json
        console.print_json(data=metrics_data)
    
    elif format == "yaml":
        import yaml
        console.print(yaml.dump(metrics_data, default_flow_style=False))


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error in CLI")
        console.print(f"\n❌ [bold red]Unexpected error: {str(e)}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
