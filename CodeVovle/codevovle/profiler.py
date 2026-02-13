"""
Performance profiling for CodeVovle recording.

Tracks:
- Sampling performance (time per sample)
- Diff computation time
- File I/O performance
- Memory usage
- File change frequency
"""

import time
import psutil
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class SampleMetrics:
    """Metrics for a single sample operation."""
    timestamp: float
    file_size_bytes: int
    diff_computed: bool
    tick_created: bool
    sample_time_ms: float
    memory_usage_mb: float


@dataclass
class PerformanceProfile:
    """Overall performance profile for a recording session."""
    start_time: float
    samples: list[SampleMetrics] = field(default_factory=list)
    total_ticks: int = 0
    
    def add_sample(self, metrics: SampleMetrics):
        """Add sample metrics."""
        self.samples.append(metrics)
        if metrics.tick_created:
            self.total_ticks += 1
    
    def get_summary(self) -> dict:
        """Get performance summary."""
        if not self.samples:
            return {
                "total_samples": 0,
                "total_ticks": 0,
                "duration_seconds": 0,
                "avg_sample_time_ms": 0,
                "peak_memory_mb": 0
            }
        
        elapsed = time.time() - self.start_time
        sample_times = [s.sample_time_ms for s in self.samples]
        memory_usage = [s.memory_usage_mb for s in self.samples]
        
        return {
            "total_samples": len(self.samples),
            "total_ticks": self.total_ticks,
            "duration_seconds": round(elapsed, 2),
            "avg_sample_time_ms": round(sum(sample_times) / len(sample_times), 2),
            "min_sample_time_ms": round(min(sample_times), 2),
            "max_sample_time_ms": round(max(sample_times), 2),
            "peak_memory_mb": round(max(memory_usage), 2),
            "avg_memory_mb": round(sum(memory_usage) / len(memory_usage), 2),
            "sampling_rate": round(len(self.samples) / elapsed, 2) if elapsed > 0 else 0,
            "tick_rate": round(self.total_ticks / elapsed, 2) if elapsed > 0 else 0
        }
    
    def export_json(self, filepath: str):
        """Export detailed metrics to JSON."""
        data = {
            "summary": self.get_summary(),
            "samples": [
                {
                    "timestamp": s.timestamp,
                    "file_size_bytes": s.file_size_bytes,
                    "diff_computed": s.diff_computed,
                    "tick_created": s.tick_created,
                    "sample_time_ms": s.sample_time_ms,
                    "memory_usage_mb": s.memory_usage_mb
                }
                for s in self.samples
            ]
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


class Profiler:
    """Simple performance profiler."""
    
    def __init__(self, enable: bool = False):
        """
        Initialize profiler.
        
        Args:
            enable: Whether profiling is enabled
        """
        self.enabled = enable
        self.profile = None
        self.process = psutil.Process(os.getpid())
        
        if enable:
            self.profile = PerformanceProfile(start_time=time.time())
    
    def start_sample(self) -> Optional[float]:
        """Start measuring a sample. Returns start time."""
        if not self.enabled or not self.profile:
            return None
        return time.time()
    
    def record_sample(
        self,
        start_time: float,
        file_path: str,
        diff_computed: bool,
        tick_created: bool
    ):
        """
        Record metrics for a sample.
        
        Args:
            start_time: When sample started
            file_path: File being sampled
            diff_computed: Whether diff was computed
            tick_created: Whether tick was created
        """
        if not self.enabled or not self.profile or not start_time:
            return
        
        elapsed_ms = (time.time() - start_time) * 1000
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        
        metrics = SampleMetrics(
            timestamp=time.time(),
            file_size_bytes=file_size,
            diff_computed=diff_computed,
            tick_created=tick_created,
            sample_time_ms=elapsed_ms,
            memory_usage_mb=memory_mb
        )
        
        self.profile.add_sample(metrics)
    
    def get_summary(self) -> dict:
        """Get performance summary."""
        if not self.enabled or not self.profile:
            return {}
        return self.profile.get_summary()
    
    def export(self, filepath: str):
        """Export detailed metrics."""
        if not self.enabled or not self.profile:
            return
        self.profile.export_json(filepath)
