from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# Log file path
log_file = log_dir / "my_agent.log"

logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,  # Thread-safe logging
)

# Export logger for use in other modules
__all__ = ["logger"]
