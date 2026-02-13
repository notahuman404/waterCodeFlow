"""
Daemon mode for CodeVovle recording.

Manages background recording processes:
- Start daemon (background recording)
- Stop daemon (graceful shutdown)
- Status of running daemons
- Daemon process management
"""

import subprocess
import json
import os
import sys
import time
import signal
from pathlib import Path
from typing import Optional


class DaemonError(Exception):
    """Daemon management error."""
    pass


class DaemonManager:
    """Manages background recording daemons."""
    
    DAEMON_DIR = Path.cwd() / ".codevovle" / "daemons"
    
    @classmethod
    def _ensure_daemon_dir(cls):
        """Ensure daemon directory exists."""
        cls.DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _get_daemon_file(cls, file_path: str) -> Path:
        """Get daemon metadata file for a file."""
        cls._ensure_daemon_dir()
        normalized = Path(file_path).resolve()
        # Create a safe filename from the file path
        safe_name = str(normalized).replace("/", "_").replace(":", "_")
        return cls.DAEMON_DIR / f"{safe_name}.daemon"
    
    @classmethod
    def start(cls, file_path: str, interval: float, num_threads: int = None) -> int:
        """
        Start background recording for a file.
        
        Args:
            file_path: File to record
            interval: Sampling interval in seconds
            num_threads: Number of threads to use (optional, uses stored value if not provided)
            
        Returns:
            Process ID of daemon
            
        Raises:
            DaemonError: If daemon start fails
        """
        from codevovle.storage import ThreadConfigManager
        
        daemon_file = cls._get_daemon_file(file_path)
        
        # Use provided threads or get from config
        if num_threads is None:
            num_threads = ThreadConfigManager.get_thread_count()
        
        # Check if already running
        if daemon_file.exists():
            try:
                with open(daemon_file) as f:
                    data = json.load(f)
                    pid = data.get("pid")
                    if pid and cls._is_process_alive(pid):
                        raise DaemonError(f"Recording already running for {file_path} (PID: {pid})")
            except json.JSONDecodeError:
                pass
        
        try:
            # Start recording process in background
            process = subprocess.Popen(
                [sys.executable, "-m", "codevovle", "record", "--file", file_path, "--interval", str(interval), "--daemonized"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Create new process group for clean termination
            )
            
            pid = process.pid
            
            # Store daemon metadata
            daemon_data = {
                "pid": pid,
                "file_path": file_path,
                "interval": interval,
                "num_threads": num_threads,
                "start_time": time.time(),
                "status": "running"
            }
            
            with open(daemon_file, "w") as f:
                json.dump(daemon_data, f, indent=2)
            
            return pid
        
        except Exception as e:
            raise DaemonError(f"Failed to start daemon: {e}") from e
    
    @classmethod
    def stop(cls, file_path: str) -> bool:
        """
        Stop background recording for a file.
        
        Args:
            file_path: File to stop recording
            
        Returns:
            True if daemon was stopped, False if not found/already stopped
            
        Raises:
            DaemonError: If stop fails
        """
        daemon_file = cls._get_daemon_file(file_path)
        
        if not daemon_file.exists():
            return False
        
        try:
            with open(daemon_file) as f:
                daemon_data = json.load(f)
                pid = daemon_data.get("pid")
            
            if not pid:
                daemon_file.unlink()
                return False
            
            # Try to terminate gracefully
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                # Wait for process to die
                time.sleep(1)
            except (ProcessLookupError, OSError):
                pass
            
            # Remove daemon file
            daemon_file.unlink()
            return True
        
        except Exception as e:
            raise DaemonError(f"Failed to stop daemon: {e}") from e
    
    @classmethod
    def status(cls, file_path: str) -> Optional[dict]:
        """
        Get status of daemon for a file.
        
        Args:
            file_path: File to check
            
        Returns:
            Daemon metadata dict if running, None otherwise
        """
        daemon_file = cls._get_daemon_file(file_path)
        
        if not daemon_file.exists():
            return None
        
        try:
            with open(daemon_file) as f:
                daemon_data = json.load(f)
                pid = daemon_data.get("pid")
                
                # Check if process still alive
                if pid and cls._is_process_alive(pid):
                    elapsed = time.time() - daemon_data.get("start_time", 0)
                    daemon_data["elapsed_seconds"] = round(elapsed, 2)
                    daemon_data["status"] = "running"
                    return daemon_data
                else:
                    daemon_file.unlink()
                    return None
        
        except json.JSONDecodeError:
            daemon_file.unlink()
            return None
    
    @classmethod
    def list_all(cls) -> list[dict]:
        """
        List all running daemons.
        
        Returns:
            List of daemon metadata dicts
        """
        cls._ensure_daemon_dir()
        daemons = []
        
        for daemon_file in cls.DAEMON_DIR.glob("*.daemon"):
            try:
                with open(daemon_file) as f:
                    daemon_data = json.load(f)
                    pid = daemon_data.get("pid")
                    
                    # Check if process still alive
                    if pid and cls._is_process_alive(pid):
                        elapsed = time.time() - daemon_data.get("start_time", 0)
                        daemon_data["elapsed_seconds"] = round(elapsed, 2)
                        daemon_data["status"] = "running"
                        daemons.append(daemon_data)
                    else:
                        daemon_file.unlink()
            except json.JSONDecodeError:
                daemon_file.unlink()
        
        return daemons
    
    @classmethod
    def stop_all(cls) -> int:
        """
        Stop all running daemons.
        
        Returns:
            Number of daemons stopped
        """
        daemons = cls.list_all()
        count = 0
        
        for daemon in daemons:
            try:
                cls.stop(daemon["file_path"])
                count += 1
            except DaemonError:
                pass
        
        return count
    
    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        """Check if a process is still alive."""
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, OSError):
            return False
