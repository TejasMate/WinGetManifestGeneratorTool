#!/usr/bin/env python3
"""Test and demonstration of the monitoring and observability system."""

import sys
import time
import random
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from winget_automation.monitoring import (
    get_logger, setup_structured_logging,
    get_metrics_collector, timer, increment_counter, set_gauge,
    get_health_checker, check_all_health,
    get_progress_tracker, ProgressContext, track_progress
)
from winget_automation.monitoring.logging import set_correlation_id, CorrelationContext, log_operation
from winget_automation.monitoring.metrics import timed
from winget_automation.config import get_config


def test_structured_logging():
    """Test structured logging functionality."""
    print("=== Testing Structured Logging ===")
    
    # Setup structured logging
    setup_structured_logging(force_setup=True)
    
    # Get logger
    logger = get_logger(__name__)
    
    # Test basic logging with structured data
    logger.info("Application started", 
                version="1.0.0", 
                environment="test",
                user_count=100)
    
    # Test logging with correlation ID
    with CorrelationContext():
        logger.info("Processing user request", 
                   user_id="user123", 
                   action="data_processing")
        
        logger.warning("Rate limit approaching",
                      remaining_requests=50,
                      limit=1000)
    
    # Test operation logging
    logger.log_operation_start("data_processing", package_count=500)
    time.sleep(0.1)  # Simulate work
    logger.log_operation_success("data_processing", duration=0.1, packages_processed=500)
    
    # Test API request logging
    logger.log_api_request("GET", "https://api.github.com/repos/test/test", 
                          status_code=200, duration=0.5)
    
    # Test performance metric logging
    logger.log_performance_metric("processing_rate", 150.5, "packages/second",
                                 worker_id="worker-1")
    
    # Test error logging
    try:
        raise ValueError("Test error for logging")
    except Exception as e:
        logger.log_operation_failure("data_processing", error=e, duration=0.1)
    
    print("✓ Structured logging tests completed")


def test_metrics_collection():
    """Test metrics collection functionality."""
    print("\n=== Testing Metrics Collection ===")
    
    metrics = get_metrics_collector()
    
    # Test counters
    metrics.increment_counter("test.requests.total", tags={"endpoint": "/api/test"})
    metrics.increment_counter("test.requests.success", tags={"endpoint": "/api/test"})
    
    # Test gauges
    metrics.set_gauge("test.active_connections", 25, tags={"server": "web-1"})
    metrics.set_gauge("test.memory_usage_mb", 512.5)
    
    # Test histograms
    for _ in range(10):
        metrics.observe_histogram("test.response_time", random.uniform(0.1, 2.0))
    
    # Test timer context manager
    with timer("test.processing_time", tags={"operation": "test"}):
        time.sleep(0.1)  # Simulate work
    
    # Test API call recording
    metrics.record_api_call("GET", "/api/packages", 200, 0.5, success=True)
    metrics.record_api_call("POST", "/api/packages", 429, 1.2, success=False)
    
    # Test package processing recording
    metrics.record_package_processing("test.package", True, 2.5)
    metrics.record_package_processing("another.package", False, 5.0, "validation_error")
    
    # Test GitHub metrics
    metrics.record_github_metrics("microsoft/winget-pkgs", 5, 10, 3.2)
    
    # Get metrics summary
    summary = metrics.get_summary_stats()
    print(f"✓ Metrics collected:")
    print(f"  - Packages processed: {summary['summary']['packages_processed']}")
    print(f"  - Package success rate: {summary['summary']['package_success_rate']}%")
    print(f"  - API requests: {summary['summary']['api_requests']}")
    print(f"  - API success rate: {summary['summary']['api_success_rate']}%")
    
    print("✓ Metrics collection tests completed")


def test_health_checks():
    """Test health check functionality."""
    print("\n=== Testing Health Checks ===")
    
    health_checker = get_health_checker()
    
    # Run all health checks
    health_status = check_all_health()
    
    print(f"✓ Overall health status: {health_status['overall_status']}")
    print(f"  - Total checks: {health_status['summary']['total_checks']}")
    print(f"  - Healthy: {health_status['summary']['healthy']}")
    print(f"  - Warning: {health_status['summary']['warning']}")
    print(f"  - Critical: {health_status['summary']['critical']}")
    
    # Show individual check results
    for check_name, check_result in health_status['checks'].items():
        status_icon = "✓" if check_result['status'] == 'healthy' else "⚠️" if check_result['status'] == 'warning' else "❌"
        print(f"  {status_icon} {check_name}: {check_result['message']}")
    
    print("✓ Health checks completed")


def test_progress_tracking():
    """Test progress tracking functionality."""
    print("\n=== Testing Progress Tracking ===")
    
    # Create progress tracker
    tracker = get_progress_tracker("test_processing", ["initialization", "processing", "cleanup"])
    
    # Start overall tracking
    tracker.start_tracker()
    
    # Step 1: Initialization
    with ProgressContext("test_processing", "initialization", 3, "Setting up environment"):
        for i in range(3):
            time.sleep(0.1)
            tracker.update_step("initialization", increment=1, message=f"Init step {i+1}")
    
    # Step 2: Processing with progress bar
    tracker.start_step("processing", 10, "Processing packages")
    for i in range(10):
        time.sleep(0.05)
        tracker.update_step("processing", increment=1, 
                          message=f"Processing package {i+1}/10",
                          metadata={"package_id": f"pkg-{i+1}"})
    
    tracker.complete_step("processing", "All packages processed successfully")
    
    # Step 3: Cleanup
    with ProgressContext("test_processing", "cleanup", 2, "Cleaning up resources"):
        for i in range(2):
            time.sleep(0.1)
            tracker.update_step("cleanup", increment=1, message=f"Cleanup step {i+1}")
    
    # Complete overall tracking
    tracker.complete_tracker("Test processing completed successfully")
    
    # Show progress summary
    progress = tracker.get_overall_progress()
    print(f"✓ Progress tracking completed:")
    print(f"  - Status: {progress['status']}")
    print(f"  - Duration: {progress['duration']}")
    print(f"  - Steps completed: {progress['steps']['completed']}/{progress['steps']['total']}")
    print(f"  - Items processed: {progress['items']['completed']}/{progress['items']['total']}")
    
    print("✓ Progress tracking tests completed")


@timed("test_function_timing")
def simulated_work():
    """Simulate some work for timing tests."""
    time.sleep(0.2)
    return "work completed"


@log_operation("test_operation")
def simulated_operation():
    """Simulate an operation for logging tests."""
    time.sleep(0.1)
    return {"status": "success", "items_processed": 42}


@track_progress("decorator_test", "processing", 5)
def simulated_progress_work():
    """Simulate work with automatic progress tracking."""
    tracker = get_progress_tracker("decorator_test")
    for i in range(5):
        time.sleep(0.1)
        tracker.update_step("processing", increment=1, message=f"Item {i+1}")
    return "processing complete"


def test_decorators():
    """Test monitoring decorators."""
    print("\n=== Testing Monitoring Decorators ===")
    
    # Test timing decorator
    result = simulated_work()
    print(f"✓ Timed function result: {result}")
    
    # Test operation logging decorator
    result = simulated_operation()
    print(f"✓ Operation logged result: {result}")
    
    # Test progress tracking decorator
    result = simulated_progress_work()
    print(f"✓ Progress tracked result: {result}")
    
    print("✓ Decorator tests completed")


def test_integration_example():
    """Test integration with existing code patterns."""
    print("\n=== Testing Integration Example ===")
    
    logger = get_logger(__name__)
    metrics = get_metrics_collector()
    
    # Simulate package processing workflow
    with CorrelationContext("package-proc-123"):
        logger.info("Starting package processing workflow",
                   packages=["pkg1", "pkg2", "pkg3"])
        
        tracker = get_progress_tracker("package_processing", 
                                     ["validation", "processing", "output"])
        tracker.start_tracker()
        
        # Validation step
        with timer("validation.duration"):
            tracker.start_step("validation", 3, "Validating packages")
            for i, pkg in enumerate(["pkg1", "pkg2", "pkg3"]):
                time.sleep(0.05)
                logger.debug("Validating package", package=pkg, step=i+1)
                tracker.update_step("validation", increment=1, 
                                  message=f"Validating {pkg}")
                metrics.increment_counter("packages.validated")
            
            tracker.complete_step("validation", "All packages validated")
        
        # Processing step
        with timer("processing.duration"):
            tracker.start_step("processing", 3, "Processing packages")
            for i, pkg in enumerate(["pkg1", "pkg2", "pkg3"]):
                process_start = time.time()
                time.sleep(0.1)
                process_duration = time.time() - process_start
                
                logger.info("Package processed", 
                           package=pkg, 
                           duration=process_duration,
                           status="success")
                
                tracker.update_step("processing", increment=1,
                                  message=f"Processed {pkg}")
                
                metrics.record_package_processing(pkg, True, process_duration)
            
            tracker.complete_step("processing", "All packages processed")
        
        # Output step
        tracker.start_step("output", 1, "Generating output")
        time.sleep(0.1)
        logger.info("Output generated", file="packages.csv", size_mb=2.5)
        tracker.update_step("output", increment=1, message="Output file created")
        tracker.complete_step("output", "Output generated successfully")
        
        tracker.complete_tracker("Package processing workflow completed")
        
        logger.info("Package processing workflow completed",
                   total_packages=3,
                   total_duration=tracker.get_overall_progress()["duration"])
    
    print("✓ Integration example completed")


def test_export_functionality():
    """Test data export functionality."""
    print("\n=== Testing Export Functionality ===")
    
    # Export metrics
    metrics = get_metrics_collector()
    metrics_file = Path("test_metrics.json")
    metrics.export_metrics(metrics_file)
    print(f"✓ Metrics exported to {metrics_file}")
    
    # Export health report
    health_checker = get_health_checker()
    health_file = Path("test_health.json")
    health_checker.export_health_report(health_file)
    print(f"✓ Health report exported to {health_file}")
    
    # Export progress data
    tracker = get_progress_tracker("test_processing")
    if tracker:
        progress_file = Path("test_progress.json")
        tracker.export_progress(progress_file)
        print(f"✓ Progress data exported to {progress_file}")
    
    # Cleanup test files
    for file in [metrics_file, health_file, progress_file]:
        if file.exists():
            file.unlink()
    
    print("✓ Export functionality tests completed")


def main():
    """Run all monitoring system tests."""
    print("WinGetManifestAutomationTool Monitoring & Observability System Test")
    print("=" * 75)
    
    try:
        test_structured_logging()
        test_metrics_collection()
        test_health_checks()
        test_progress_tracking()
        test_decorators()
        test_integration_example()
        test_export_functionality()
        
        print("\n" + "=" * 75)
        print("🎉 All monitoring system tests completed successfully!")
        print("\nMonitoring capabilities available:")
        print("• Structured JSON logging with correlation IDs")
        print("• Comprehensive metrics collection (counters, gauges, histograms)")
        print("• Automated health checks for system components")
        print("• Real-time progress tracking with ETA calculation")
        print("• Performance monitoring with decorators")
        print("• Export functionality for metrics and reports")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
