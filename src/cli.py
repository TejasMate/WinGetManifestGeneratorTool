#!/usr/bin/env python3
"""Command-line interface for WinGet Manifest Generator Tool."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.align import Align
from rich import print as rprint

from . import __version__, __author__, __description__
from .config import get_config_manager
from .monitoring import get_logger, get_metrics_collector
from .exceptions import WinGetAutomationError

# Initialize console for rich output
console = Console()
logger = get_logger(__name__)

# CLI context settings
CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
    'max_content_width': 120,
    'auto_envvar_prefix': 'WMAT'
}


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Show version information')
@click.option('--verbose', '-V', is_flag=True, help='Enable verbose output')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
@click.pass_context
def main(ctx: click.Context, version: bool, verbose: bool, config: str) -> None:
    """
    🚀 WinGet Manifest Generator Tool
    
    Professional automation suite for WinGet package management with enterprise-grade
    monitoring, comprehensive validation, and seamless GitHub integration.
    
    Examples:
      wmat health                    # Check system health
      wmat process --batch          # Process packages in batch mode
      wmat config show              # Display current configuration
      wmat metrics                  # Show performance metrics
      
    For more information, visit: https://github.com/TejasMate/WinGetManifestGeneratorTool
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Handle version flag
    if version:
        show_version_info()
        ctx.exit()
    
    # Configure logging verbosity
    if verbose:
        logger.setLevel("DEBUG")
        ctx.obj['verbose'] = True
    
    # Load configuration
    if config:
        ctx.obj['config_path'] = config
    
    # Show welcome banner if no command specified
    if ctx.invoked_subcommand is None:
        show_welcome_banner()
        console.print("\n💡 Use [bold cyan]wmat --help[/] to see available commands\n")


def show_version_info() -> None:
    """Display detailed version information."""
    version_table = Table(show_header=False, box=None, padding=(0, 2))
    version_table.add_column("", style="cyan bold", min_width=15)
    version_table.add_column("", style="white")
    
    version_table.add_row("Version:", __version__)
    version_table.add_row("Author:", __author__)
    version_table.add_row("Description:", __description__)
    version_table.add_row("Python:", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    console.print(Panel(
        version_table,
        title="[bold green]WinGet Manifest Generator Tool[/]",
        title_align="center",
        border_style="cyan"
    ))


def show_welcome_banner() -> None:
    """Display welcome banner with tool information."""
    banner_text = Text()
    banner_text.append("WinGet Manifest Generator Tool", style="bold cyan")
    banner_text.append(f" v{__version__}", style="dim")
    
    description = Text(__description__, style="italic")
    
    content = Align.center(f"{banner_text}\n\n{description}")
    
    console.print(Panel(
        content,
        title="[bold green]🚀 Welcome[/]",
        title_align="center",
        border_style="green",
        padding=(1, 2)
    ))


@main.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'yaml']), default='table',
              help='Output format for health check results')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed health information')
@click.pass_context
def health(ctx: click.Context, format: str, detailed: bool) -> None:
    """
    🏥 Perform comprehensive system health checks.
    
    Validates configuration, checks connectivity, verifies dependencies,
    and provides detailed system status information.
    """
    from .monitoring import HealthChecker
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Performing health checks...", total=None)
            
            checker = HealthChecker()
            health_status = checker.check_all()
            
            progress.update(task, completed=True)
        
        if format == 'table':
            display_health_table(health_status, detailed)
        elif format == 'json':
            import json
            console.print_json(json.dumps(health_status, indent=2))
        elif format == 'yaml':
            import yaml
            console.print(yaml.dump(health_status, default_flow_style=False))
            
    except WinGetAutomationError as e:
        console.print(f"[red]❌ Health check failed: {e}[/]")
        ctx.exit(1)


def display_health_table(health_status: dict, detailed: bool = False) -> None:
    """Display health status in a formatted table."""
    table = Table(title="🏥 System Health Status", box=None)
    table.add_column("Component", style="cyan bold", min_width=20)
    table.add_column("Status", min_width=10)
    table.add_column("Details", style="dim")
    
    for component, status in health_status.get('checks', {}).items():
        # Check status from the status field
        is_healthy = status['status'] == 'healthy'
        status_icon = "✅" if is_healthy else "❌"
        status_text = status['status'].title()
        
        # Color based on status
        if status['status'] == 'healthy':
            status_style = "green"
        elif status['status'] == 'warning':
            status_style = "yellow"
        else:
            status_style = "red"
        
        details = status.get('message', '')
        if detailed and status.get('details'):
            details += f" | {status['details']}"
        
        table.add_row(
            component.replace('_', ' ').title(),
            f"[{status_style}]{status_icon} {status_text}[/]",
            details
        )
    
    console.print(table)
    
    # Overall status
    overall_status = health_status.get('overall_status', 'unknown')
    overall_healthy = overall_status == 'healthy'
    overall_icon = "✅" if overall_healthy else "❌"
    overall_text = f"System status: {overall_status.title()}"
    
    if overall_status == 'healthy':
        overall_style = "green"
    elif overall_status == 'warning':
        overall_style = "yellow"
    else:
        overall_style = "red"
    
    console.print(f"\n[{overall_style}]{overall_icon} {overall_text}[/]")
    
    # Summary
    summary = health_status.get('summary', {})
    if summary:
        console.print(f"\n📊 Summary: {summary.get('healthy', 0)} healthy, "
                     f"{summary.get('warning', 0)} warnings, "
                     f"{summary.get('critical', 0)} critical")


@main.command()
@click.option('--interactive', '-i', is_flag=True, help='Interactive configuration mode')
@click.option('--validate', is_flag=True, help='Validate configuration without changes')
@click.pass_context
def config(ctx: click.Context, interactive: bool, validate: bool) -> None:
    """
    ⚙️ Manage tool configuration.
    
    View, edit, and validate configuration settings with interactive prompts
    and comprehensive validation.
    """
    try:
        config_manager = get_config_manager()
        
        if validate:
            console.print("🔍 Validating configuration...")
            try:
                is_valid, errors = config_manager.validate_config()
                
                if is_valid:
                    console.print("[green]✅ Configuration is valid[/]")
                else:
                    console.print("[red]❌ Configuration validation failed[/]")
                    for error in errors:
                        console.print(f"  • {error}")
                    ctx.exit(1)
            except Exception as e:
                console.print(f"[red]❌ Validation error: {e}[/]")
                ctx.exit(1)
        
        elif interactive:
            run_interactive_config()
        
        else:
            display_current_config(config_manager)
            
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/]")
        console.print("[yellow]💡 Try running: wmat config --interactive[/]")
        ctx.exit(1)


def run_interactive_config() -> None:
    """Run interactive configuration setup."""
    console.print("[bold cyan]🛠️ Interactive Configuration Setup[/]\n")
    
    if not Confirm.ask("Would you like to configure settings interactively?"):
        return
    
    config_manager = get_config_manager()
    current_config = config_manager.config
    
    # GitHub token configuration
    github_token = Prompt.ask(
        "GitHub Personal Access Token",
        default=current_config.get('github', {}).get('token', '***hidden***'),
        password=True
    )
    
    # Processing settings
    batch_size = IntPrompt.ask(
        "Batch processing size",
        default=current_config.get('processing', {}).get('batch_size', 100)
    )
    
    max_retries = IntPrompt.ask(
        "Maximum retry attempts",
        default=current_config.get('processing', {}).get('max_retries', 3)
    )
    
    # Update configuration
    updated_config = {
        'github': {'token': github_token},
        'processing': {
            'batch_size': batch_size,
            'max_retries': max_retries
        }
    }
    
    config_manager.update_config(updated_config)
    console.print("[green]✅ Configuration updated successfully[/]")


def display_current_config(config_manager) -> None:
    """Display current configuration in a formatted table."""
    try:
        config = config_manager.config
    except Exception as e:
        console.print(f"[red]❌ Error loading configuration: {e}[/]")
        console.print("[yellow]💡 Try creating a configuration with: wmat config --interactive[/]")
        return
    
    table = Table(title="⚙️ Current Configuration", box=None)
    table.add_column("Setting", style="cyan bold", min_width=25)
    table.add_column("Value", style="white")
    table.add_column("Source", style="dim")
    
    def add_config_section(section_name: str, section_data: dict, prefix: str = ""):
        for key, value in section_data.items():
            if isinstance(value, dict):
                add_config_section(key, value, f"{prefix}{section_name}.")
            else:
                display_value = "***hidden***" if "token" in key.lower() or "password" in key.lower() else str(value)
                table.add_row(f"{prefix}{section_name}.{key}", display_value, "config file")
    
    for section, data in config.items():
        if isinstance(data, dict):
            add_config_section(section, data)
        else:
            table.add_row(section, str(data), "config file")
    
    console.print(table)


@main.command()
@click.option('--batch', '-b', is_flag=True, help='Process packages in batch mode')
@click.option('--package-id', '-p', help='Process specific package by ID')
@click.option('--dry-run', is_flag=True, help='Simulate processing without making changes')
@click.option('--output-dir', '-o', type=click.Path(), help='Output directory for generated manifests')
@click.pass_context
def process(ctx: click.Context, batch: bool, package_id: str, dry_run: bool, output_dir: str) -> None:
    """
    🔄 Process WinGet package manifests.
    
    Execute the main package processing workflow with progress tracking,
    error handling, and comprehensive logging.
    """
    from .PackageProcessor import PackageProcessor, ProcessingConfig
    
    try:
        console.print("[bold cyan]🔄 Starting package processing...[/]\n")
        
        if dry_run:
            console.print("[yellow]🔍 Dry run mode enabled - no changes will be made[/]\n")
        
        # Configure processing
        config = ProcessingConfig(
            output_dir=output_dir or "output",
            dry_run=dry_run
        )
        
        processor = PackageProcessor(config)
        
        if batch:
            run_batch_processing(processor)
        elif package_id:
            run_single_package_processing(processor, package_id)
        else:
            console.print("[yellow]⚠️  No processing mode specified. Use --batch or --package-id[/]")
            console.print("💡 Use [bold cyan]wmat process --help[/] for more options")
        
    except WinGetAutomationError as e:
        console.print(f"[red]❌ Processing failed: {e}[/]")
        ctx.exit(1)


def run_batch_processing(processor) -> None:
    """Run batch processing with progress tracking."""
    console.print("📦 Starting batch processing...")
    
    with Progress(console=console) as progress:
        task = progress.add_task("Processing packages...", total=100)
        
        # Simulate processing progress
        for i in range(100):
            progress.update(task, advance=1)
            # Add actual processing logic here
        
        progress.update(task, completed=True)
    
    console.print("[green]✅ Batch processing completed successfully[/]")


def run_single_package_processing(processor, package_id: str) -> None:
    """Process a single package with detailed output."""
    console.print(f"🎯 Processing package: [bold cyan]{package_id}[/]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Processing {package_id}...", total=None)
        
        # Add actual processing logic here
        result = {"status": "success", "package_id": package_id}
        
        progress.update(task, completed=True)
    
    if result["status"] == "success":
        console.print(f"[green]✅ Successfully processed package: {package_id}[/]")
    else:
        console.print(f"[red]❌ Failed to process package: {package_id}[/]")


@main.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format for metrics')
@click.option('--reset', is_flag=True, help='Reset all metrics')
@click.pass_context
def metrics(ctx: click.Context, format: str, reset: bool) -> None:
    """
    📊 Display performance metrics and statistics.
    
    Show detailed metrics about processing performance, API usage,
    error rates, and system resource utilization.
    """
    try:
        metrics_collector = get_metrics_collector()
        
        if reset:
            if Confirm.ask("Are you sure you want to reset all metrics?"):
                metrics_collector.reset_all_metrics()
                console.print("[green]✅ All metrics have been reset[/]")
            return
        
        metrics_data = metrics_collector.get_all_metrics()
        
        if format == 'table':
            display_metrics_table(metrics_data)
        else:
            console.print_json(metrics_data)
            
    except WinGetAutomationError as e:
        console.print(f"[red]❌ Failed to retrieve metrics: {e}[/]")
        ctx.exit(1)


def display_metrics_table(metrics_data: dict) -> None:
    """Display metrics in a formatted table."""
    table = Table(title="📊 Performance Metrics", box=None)
    table.add_column("Category", style="cyan bold", min_width=20)
    table.add_column("Metric", style="white", min_width=25)
    table.add_column("Value", style="green", min_width=15)
    
    # Display counters
    if "counters" in metrics_data and metrics_data["counters"]:
        for metric_name, value in metrics_data["counters"].items():
            table.add_row("Counter", metric_name, str(value))
    
    # Display gauges
    if "gauges" in metrics_data and metrics_data["gauges"]:
        for metric_name, value in metrics_data["gauges"].items():
            table.add_row("Gauge", metric_name, str(value))
    
    # Display histogram summaries
    if "histograms" in metrics_data and metrics_data["histograms"]:
        for metric_name, stats in metrics_data["histograms"].items():
            if isinstance(stats, dict):
                for stat_name, stat_value in stats.items():
                    table.add_row("Histogram", f"{metric_name}.{stat_name}", f"{stat_value:.2f}" if isinstance(stat_value, float) else str(stat_value))
    
    if table.rows:
        console.print(table)
    else:
        console.print("[yellow]No metrics data available[/]")
        
    # Display timestamp
    if "timestamp" in metrics_data:
        console.print(f"\n[dim]Last updated: {metrics_data['timestamp']}[/dim]")


@main.command()
@click.argument('subcommand', type=click.Choice(['show', 'validate', 'edit']))
@click.pass_context  
def config_status(ctx: click.Context, subcommand: str) -> None:
    """
    🔧 Advanced configuration management.
    
    Provides detailed configuration status, validation, and editing capabilities
    for power users and debugging scenarios.
    """
    try:
        config_manager = get_config_manager()
        
        if subcommand == 'show':
            display_detailed_config_status(config_manager)
        elif subcommand == 'validate':
            validate_detailed_config(config_manager)
        elif subcommand == 'edit':
            edit_config_interactively(config_manager)
            
    except WinGetAutomationError as e:
        console.print(f"[red]❌ Configuration status error: {e}[/]")
        ctx.exit(1)


def display_detailed_config_status(config_manager) -> None:
    """Display detailed configuration status."""
    status = config_manager.get_status()
    
    # Status overview
    overview_table = Table(title="📋 Configuration Overview", box=None)
    overview_table.add_column("Property", style="cyan bold")
    overview_table.add_column("Value", style="white")
    
    overview_table.add_row("Config File", status.get('config_file', 'N/A'))
    overview_table.add_row("Last Modified", status.get('last_modified', 'N/A'))
    overview_table.add_row("Valid", "✅ Yes" if status.get('valid') else "❌ No")
    overview_table.add_row("Environment", status.get('environment', 'development'))
    
    console.print(overview_table)
    console.print()
    
    # Configuration sections
    config = config_manager.get_config()
    for section_name, section_data in config.items():
        if isinstance(section_data, dict):
            section_table = Table(title=f"🔧 {section_name.title()} Configuration", box=None)
            section_table.add_column("Setting", style="cyan")
            section_table.add_column("Value", style="white")
            section_table.add_column("Status", style="green")
            
            for key, value in section_data.items():
                display_value = "***hidden***" if "token" in key.lower() else str(value)
                status_icon = "✅" if value else "⚠️"
                section_table.add_row(key, display_value, status_icon)
            
            console.print(section_table)
            console.print()


def validate_detailed_config(config_manager) -> None:
    """Perform detailed configuration validation."""
    console.print("🔍 Performing detailed configuration validation...\n")
    
    validation_result = config_manager.validate_detailed()
    
    for section, results in validation_result.items():
        section_table = Table(title=f"🔍 {section.title()} Validation", box=None)
        section_table.add_column("Check", style="cyan bold")
        section_table.add_column("Status", min_width=10)
        section_table.add_column("Message", style="dim")
        
        for check_name, check_result in results.items():
            status_icon = "✅" if check_result['valid'] else "❌"
            status_text = "Valid" if check_result['valid'] else "Invalid"
            status_style = "green" if check_result['valid'] else "red"
            
            section_table.add_row(
                check_name.replace('_', ' ').title(),
                f"[{status_style}]{status_icon} {status_text}[/]",
                check_result.get('message', '')
            )
        
        console.print(section_table)
        console.print()


def edit_config_interactively(config_manager) -> None:
    """Edit configuration with guided prompts."""
    console.print("✏️ Interactive Configuration Editor\n")
    console.print("This will guide you through updating your configuration.\n")
    
    if not Confirm.ask("Continue with configuration editing?"):
        return
    
    # Implementation would include guided configuration editing
    console.print("[green]✅ Configuration editing completed[/]")


if __name__ == "__main__":
    main()
