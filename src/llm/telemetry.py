import os
from typing import Any, Dict, Optional

import psutil


class TelemetryTracker:
    """Tracks system telemetry during model execution, such as RAM usage."""
    
    def __init__(self, process_name: Optional[str] = None):
        self.process_name = process_name
        self.target_pids = self._find_target_pids()
        self.start_memory = 0.0
        self.peak_memory = 0.0

    def _find_target_pids(self) -> list[int]:
        if not self.process_name:
            return [os.getpid()] # Fallback to current process if not specified
        
        pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info.get('name', '').lower()
                cmd = ' '.join(proc.info.get('cmdline', []) or []).lower()
                if self.process_name.lower() in name or self.process_name.lower() in cmd:
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return pids

    def _get_current_memory_mb(self) -> float:
        total_rss = 0
        for pid in self.target_pids:
            try:
                proc = psutil.Process(pid)
                total_rss += proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total_rss / (1024 * 1024)

    def start(self):
        self.target_pids = self._find_target_pids()
        self.start_memory = self._get_current_memory_mb()
        self.peak_memory = self.start_memory

    def poll(self):
        current = self._get_current_memory_mb()
        if current > self.peak_memory:
            self.peak_memory = current

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "start_memory_mb": round(self.start_memory, 2),
            "peak_memory_mb": round(self.peak_memory, 2),
            "memory_delta_mb": round(self.peak_memory - self.start_memory, 2),
            "tracked_processes": len(self.target_pids)
        }

def calculate_token_rate(completion_tokens: Optional[int], total_latency_ms: Optional[float], ttft_ms: Optional[float]) -> Optional[float]:
    """Calculate token generation rate."""
    if not completion_tokens or not total_latency_ms or ttft_ms is None:
        return None
        
    generation_time_ms = total_latency_ms - ttft_ms
    if generation_time_ms <= 0:
        return None
        
    return completion_tokens / (generation_time_ms / 1000.0)
