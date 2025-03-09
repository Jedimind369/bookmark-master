#!/usr/bin/env python3
"""
Thread-safe UI updates manager for the bookmark processor.
Ensures that UI updates are processed without race conditions.
"""

import queue
import threading
import time
import logging
from typing import Callable, Dict, Any, Optional, List, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/ui_updates.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ui_updates")

class UpdateType(Enum):
    """Types of UI updates that can be queued"""
    PROGRESS = "progress"
    STATUS = "status"
    ERROR = "error"
    COMPLETE = "complete"
    STATS = "stats"
    CUSTOM = "custom"

class UIUpdateManager:
    """
    Thread-safe manager for UI updates.
    Ensures that UI updates are processed in a controlled manner without race conditions.
    """
    
    def __init__(self, update_interval: float = 0.1):
        """
        Initialize the UI update manager.
        
        Args:
            update_interval: Time in seconds between processing updates
        """
        self.update_queue = queue.Queue()
        self.update_handlers: Dict[UpdateType, List[Callable]] = {
            update_type: [] for update_type in UpdateType
        }
        self.update_interval = update_interval
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.last_progress: Dict[str, float] = {}
        self.throttle_settings: Dict[UpdateType, float] = {
            UpdateType.PROGRESS: 0.5,  # Update progress at most every 0.5 seconds
            UpdateType.STATUS: 0.0,    # No throttling for status updates
            UpdateType.ERROR: 0.0,     # No throttling for errors
            UpdateType.COMPLETE: 0.0,  # No throttling for completion
            UpdateType.STATS: 1.0,     # Update stats at most every 1 second
            UpdateType.CUSTOM: 0.2     # Update custom at most every 0.2 seconds
        }
        self.last_update_time: Dict[Tuple[UpdateType, str], float] = {}
        logger.info("UI Update Manager initialized")
    
    def start(self):
        """Start the update processing thread"""
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._process_updates, daemon=True)
        self.update_thread.start()
        logger.info("UI Update Manager started")
    
    def stop(self):
        """Stop the update processing thread"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
            self.update_thread = None
        logger.info("UI Update Manager stopped")
    
    def register_handler(self, update_type: UpdateType, handler: Callable):
        """
        Register a handler for a specific update type.
        
        Args:
            update_type: The type of update to handle
            handler: The callback function to call when an update of this type occurs
        """
        self.update_handlers[update_type].append(handler)
        logger.debug(f"Registered handler for {update_type.value}")
    
    def set_throttle(self, update_type: UpdateType, interval: float):
        """
        Set the throttle interval for a specific update type.
        
        Args:
            update_type: The type of update to throttle
            interval: The minimum time in seconds between updates of this type
        """
        self.throttle_settings[update_type] = interval
        logger.debug(f"Set throttle for {update_type.value} to {interval}s")
    
    def queue_update(self, update_type: UpdateType, key: str, data: Any):
        """
        Queue an update to be processed by the update thread.
        
        Args:
            update_type: The type of update
            key: A key to identify this update (used for throttling)
            data: The data associated with the update
        """
        # Check if this update should be throttled
        current_time = time.time()
        update_key = (update_type, key)
        
        if update_key in self.last_update_time:
            time_since_last = current_time - self.last_update_time[update_key]
            if time_since_last < self.throttle_settings[update_type]:
                # Skip this update due to throttling
                return
        
        # Queue the update and record the time
        self.update_queue.put((update_type, key, data))
        self.last_update_time[update_key] = current_time
    
    def queue_progress(self, task_id: str, progress: float, total: Optional[float] = None):
        """
        Queue a progress update.
        
        Args:
            task_id: Identifier for the task
            progress: Current progress value
            total: Optional total value
        """
        self.queue_update(UpdateType.PROGRESS, task_id, {
            'progress': progress,
            'total': total,
            'percentage': (progress / total * 100) if total else None
        })
    
    def queue_status(self, task_id: str, status: str):
        """
        Queue a status update.
        
        Args:
            task_id: Identifier for the task
            status: Status message
        """
        self.queue_update(UpdateType.STATUS, task_id, {'status': status})
    
    def queue_error(self, task_id: str, error: str, details: Optional[Dict[str, Any]] = None):
        """
        Queue an error update.
        
        Args:
            task_id: Identifier for the task
            error: Error message
            details: Optional error details
        """
        self.queue_update(UpdateType.ERROR, task_id, {
            'error': error,
            'details': details or {}
        })
    
    def queue_complete(self, task_id: str, result: Any):
        """
        Queue a completion update.
        
        Args:
            task_id: Identifier for the task
            result: Result of the completed task
        """
        self.queue_update(UpdateType.COMPLETE, task_id, {'result': result})
    
    def queue_stats(self, task_id: str, stats: Dict[str, Any]):
        """
        Queue a stats update.
        
        Args:
            task_id: Identifier for the task
            stats: Statistics to report
        """
        self.queue_update(UpdateType.STATS, task_id, {'stats': stats})
    
    def queue_custom(self, task_id: str, event_type: str, data: Any):
        """
        Queue a custom update.
        
        Args:
            task_id: Identifier for the task
            event_type: Type of custom event
            data: Custom event data
        """
        self.queue_update(UpdateType.CUSTOM, task_id, {
            'event_type': event_type,
            'data': data
        })
    
    def _process_updates(self):
        """Process updates from the queue in a separate thread"""
        logger.info("Update processing thread started")
        
        while self.running:
            try:
                # Try to get an update from the queue with a timeout
                try:
                    update_type, key, data = self.update_queue.get(timeout=self.update_interval)
                except queue.Empty:
                    # No updates in queue, continue the loop
                    continue
                
                # Process the update
                handlers = self.update_handlers[update_type]
                for handler in handlers:
                    try:
                        handler(key, data)
                    except Exception as e:
                        logger.error(f"Error in update handler: {str(e)}", exc_info=True)
                
                # Mark the task as done
                self.update_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in update processing thread: {str(e)}", exc_info=True)
        
        logger.info("Update processing thread stopped")


# Example usage
if __name__ == "__main__":
    # Example of how to use the UI Update Manager
    
    # Create handlers for different update types
    def progress_handler(key, data):
        print(f"Progress update for {key}: {data['progress']}/{data['total']} ({data['percentage']:.1f}%)")
    
    def status_handler(key, data):
        print(f"Status update for {key}: {data['status']}")
    
    def error_handler(key, data):
        print(f"Error in {key}: {data['error']}")
    
    def complete_handler(key, data):
        print(f"Task {key} completed with result: {data['result']}")
    
    # Create and start the UI Update Manager
    ui_manager = UIUpdateManager()
    
    # Register handlers
    ui_manager.register_handler(UpdateType.PROGRESS, progress_handler)
    ui_manager.register_handler(UpdateType.STATUS, status_handler)
    ui_manager.register_handler(UpdateType.ERROR, error_handler)
    ui_manager.register_handler(UpdateType.COMPLETE, complete_handler)
    
    # Start the manager
    ui_manager.start()
    
    # Simulate some task updates
    try:
        ui_manager.queue_status("task1", "Starting task")
        
        for i in range(10):
            ui_manager.queue_progress("task1", i, 10)
            time.sleep(0.2)
            
            # Simulate an error
            if i == 5:
                ui_manager.queue_error("task1", "Something went wrong", {"step": i})
        
        ui_manager.queue_complete("task1", {"success": True, "items_processed": 10})
        
        # Wait for all updates to be processed
        time.sleep(1)
    finally:
        # Stop the manager
        ui_manager.stop() 