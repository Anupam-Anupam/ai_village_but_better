#!/usr/bin/env python3
"""
Real-time trajectory file organizer.

This script watches a directory for new trajectory files and organizes them into:
- trajectory_progress_<number>.json - Agent's progress updates
- trajectory_screenshot_<number>.json - Screenshot updates
- trajectory_other_<number>.json - Other logs
"""

import json
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, Set
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class TrajectoryOrganizer(FileSystemEventHandler):
    def __init__(self, watch_dir: Path, output_dir: Optional[Path] = None):
        self.watch_dir = watch_dir
        # Set default output directory to CUA/organized_traj if not specified
        default_output = Path(__file__).parent / 'organized_traj'
        self.output_dir = output_dir or default_output
        self.processed_files: Set[str] = set()
        self.counters = {
            'progress': 0,
            'screenshot': 0,
            'other': 0
        }
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process any existing files
        self._process_existing_files()
    
    def _get_next_filename(self, file_type: str) -> Path:
        """Generate the next filename for the given type."""
        self.counters[file_type] += 1
        return self.output_dir / f"trajectory_{file_type}_{self.counters[file_type]}.json"
    
    def _classify_file(self, file_path: Path) -> Optional[str]:
        """Classify a file into one of the categories."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check for screenshot-like files
            if any(k in str(file_path).lower() for k in ["screenshot", "computer_call_result", "annotated"]):
                return "screenshot"
                
            if isinstance(data, dict):
                # Check for agent progress (agent responses)
                if "output" in data and isinstance(data["output"], list):
                    for item in data["output"]:
                        if isinstance(item, dict) and item.get("type") == "message":
                            if item.get("content"):
                                return "progress"
                
                # Check for screenshots in content
                if any(k in data for k in ["screenshot", "image", "image_path", "screenshot_path"]):
                    return "screenshot"
                
                # Check for role-based messages
                if data.get("role") == "assistant":
                    return "progress"
            
            return "other"
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Could not parse {file_path}: {e}")
            return "other"
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            return None
    
    def _process_file(self, file_path: Path):
        """Process a single file."""
        if not file_path.is_file() or file_path.suffix.lower() != '.json':
            return
            
        if str(file_path.absolute()) in self.processed_files:
            return
            
        file_type = self._classify_file(file_path)
        if not file_type:
            return
            
        # Get the next filename for this type
        dest_path = self._get_next_filename(file_type)
        
        try:
            # Move the file to its new location
            shutil.move(str(file_path), str(dest_path))
            self.processed_files.add(str(file_path.absolute()))
            logger.info(f"Moved {file_path.name} to {dest_path.name}")
        except Exception as e:
            logger.error(f"Failed to move {file_path}: {e}")
    
    def _process_existing_files(self):
        """Process any existing files in the watch directory."""
        for file_path in self.watch_dir.glob("*.json"):
            self._process_file(file_path)
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self._process_file(Path(event.src_path))

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Organize trajectory files in real-time')
    parser.add_argument('--watch-dir', type=Path, default='./trajectories',
                       help='Directory to watch for new trajectory files (default: ./trajectories)')
    parser.add_argument('--output-dir', type=Path, 
                       help='Directory to output organized files (default: CUA/organized_traj)')
    
    args = parser.parse_args()
    
    # Set up the event handler
    event_handler = TrajectoryOrganizer(
        watch_dir=args.watch_dir,
        output_dir=args.output_dir or args.watch_dir
    )
    
    # Set up the observer
    observer = Observer()
    observer.schedule(event_handler, str(args.watch_dir), recursive=False)
    
    try:
        logger.info(f"Watching directory: {args.watch_dir}")
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Stopped watching directory")
    
    observer.join()

if __name__ == "__main__":
    main()
