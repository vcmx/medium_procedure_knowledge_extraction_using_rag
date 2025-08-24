import logging
from datetime import datetime
from pathlib import Path


def setup_logging(log_level=logging.INFO, app_name="app"):
    """
    Sets up logging to file and console with a timestamped log file.

    This configuration is forced, overriding any existing handlers to ensure
    consistency, which is especially useful when running in environments like
    Streamlit that might pre-configure logging.

    Args:
        log_level (int): The logging level (e.g., logging.DEBUG, logging.INFO).
        app_name (str): A name for the application, used in the log filename.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create a log file with a timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{app_name}_{timestamp}.log"

    # Configure logging to both file and console
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        force=True,  # Override any existing logger configuration
    )

    # Log the path to the log file for easy access
    logging.info(f"Logging configured. Log file: {log_file}")
