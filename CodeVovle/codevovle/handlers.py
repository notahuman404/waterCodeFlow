"""
Command handlers for CodeVovle CLI.

Implements execution logic for all CLI commands:
- record: Start interval-based file change tracking
- revert: Restore file to a specific tick
- branch: List, rename, or switch branches
- status: Display tracking state
- insights: Generate AI-powered code analysis
- daemon: Manage background recording
"""

import os
import sys
import time
import json
import signal
from pathlib import Path
from typing import Optional
from argparse import Namespace

from codevovle.engine import RecordingEngine, RecordingError, TickCursor
from codevovle.storage import StateManager, BranchManager, ConfigManager, ThreadConfigManager, StorageError
from codevovle.insights import InsightsEngine, InsightsError
from codevovle.profiler import Profiler
from codevovle.daemon import DaemonManager, DaemonError
from codevovle.env_manager import EnvManager
import storage_utility as su

# Global flag for graceful shutdown
_shutdown_requested = False

def _signal_handler(signum, frame):
    """Handle Ctrl+C and shutdown signals."""
    global _shutdown_requested
    _shutdown_requested = True
    print("\n\n⏹️  Shutting down gracefully...", file=sys.stderr)
    sys.exit(0)


class HandlerError(Exception):
    """Handler execution error."""
    pass


def handle_record(args: Namespace) -> int:
    """
    Handle 'record' command - start continuous interval-based tracking.
    
    Runs a sampling loop that monitors the file at regular intervals,
    computes diffs, and persists changes. Can be run in foreground or
    backgrounded with & or in a separate terminal.
    
    Graceful shutdown on Ctrl+C (SIGINT) or SIGTERM.
    
    Args:
        args: Parsed arguments with 'file' and 'interval'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        interval = float(args.interval)
        enable_profiling = getattr(args, 'profile', False)
        
        if interval <= 0:
            print(f"❌ Error: Interval must be positive (got {interval})", file=sys.stderr)
            return 1
        
        print(f"📝 Recording file: {args.file}")
        print(f"⏱️  Interval: {interval}s")
        if enable_profiling:
            print(f"📊 Performance profiling: ENABLED")
        print(f"💾 Data dir: .codevovle/")
        print()
        
        # Create profiler if requested
        profiler = Profiler(enable=enable_profiling)

        # Determine thread configuration: prefer explicit arg, otherwise stored value
        from codevovle.storage import ThreadConfigManager
        num_threads = None
        if hasattr(args, 'threads') and args.threads is not None:
            try:
                num_threads = int(args.threads)
            except Exception:
                num_threads = None

        engine = RecordingEngine(file_path, interval, profiler=profiler, num_threads=num_threads)
        engine.initialize_tracking()
        
        print(f"✅ Recording initialized")
        print(f"📍 Base snapshot created")
        print(f"🌿 Main branch created")
        print(f"🔄 Starting sampling loop (Ctrl+C to stop)...\n")
        print(f"🔧 Threads: {engine.num_threads}")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
        
        tick_count = 0
        sample_count = 0
        last_file_size = os.path.getsize(file_path)
        
        # Continuous sampling loop
        while True:
            try:
                tick_id = engine.sample()
                sample_count += 1
                
                if tick_id is not None:
                    tick_count += 1
                    current_file_size = os.path.getsize(file_path)
                    size_change = current_file_size - last_file_size
                    last_file_size = current_file_size
                    
                    print(f"[{time.strftime('%H:%M:%S')}] ✨ Tick {tick_id} recorded ({size_change:+d} bytes)")
                else:
                    # No change detected this cycle - still print progress
                    print(f"[{time.strftime('%H:%M:%S')}] 📊 Sampled (no changes)", end="\r")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                # Allow graceful shutdown from within the loop
                raise
            except Exception as e:
                print(f"\n⚠️  Warning during sampling: {e}", file=sys.stderr)
                time.sleep(interval)
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n✋ Recording stopped", file=sys.stderr)
        print(f"📊 Summary: {tick_count} ticks recorded across {sample_count} samples", file=sys.stderr)
        
        # Export profiling data if enabled
        if enable_profiling and 'profiler' in locals():
            stats = profiler.get_summary()
            if stats:
                print(f"\n📈 Performance Stats:", file=sys.stderr)
                print(f"   Avg sample time: {stats.get('avg_sample_time_ms', 0):.2f}ms", file=sys.stderr)
                print(f"   Peak memory: {stats.get('peak_memory_mb', 0):.2f}MB", file=sys.stderr)
                print(f"   Sampling rate: {stats.get('sampling_rate', 0):.2f} samples/sec", file=sys.stderr)
        # Shutdown engine resources
        try:
            engine.shutdown()
        except Exception:
            pass

        return 0
        
    except RecordingError as e:
        print(f"❌ Recording error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_revert(args: Namespace) -> int:
    """
    Handle 'revert' command - restore file to a specific tick.
    
    Args:
        args: Parsed arguments with 'file' and 'at'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        tick_id = int(args.at)
        
        print(f"⏮️  Reverting to tick: {tick_id}")
        
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)  # Interval not used for revert
        old_content = su.read_text(file_path)
        
        engine.revert_to_tick(tick_id)
        new_content = su.read_text(file_path)
        
        print(f"✅ File reverted to tick {tick_id}")
        print(f"📄 File: {args.file}")
        print(f"📊 Bytes changed: {abs(len(new_content) - len(old_content))}")
        
        return 0
        
    except RecordingError as e:
        print(f"❌ Revert error: {e}", file=sys.stderr)
        return 1
    except ValueError:
        print(f"❌ Error: Tick must be an integer", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_branch_list(args: Namespace) -> int:
    """
    Handle 'branch list' command - show all branches for a file (hierarchical).
    
    Args:
        args: Parsed arguments with 'file' and optional 'parent'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)
        
        parent = getattr(args, 'parent', None)
        branches = engine.list_branches()
        
        if parent:
            # Filter children of specified parent
            branches = [b for b in branches if b.startswith(parent + "/") and "/" not in b[len(parent)+1:]]
        
        cursor = StateManager.get_cursor(file_path)
        active_branch = cursor.get("active_branch", "main") if cursor else "main"
        
        if not branches:
            if parent:
                print(f"📭 No child branches found under {parent}")
            else:
                print(f"📭 No branches found for {args.file}")
            return 0
        
        title = f"Branches under {parent}" if parent else f"Branches for {args.file}"
        print(f"\n📋 {title}:")
        print(f"{'Branch':<40} {'Head Tick':<12} {'Children':<10} {'Status':<10}")
        print("=" * 75)
        
        for branch_name in sorted(branches):
            branch_data = BranchManager.read(branch_name)
            if branch_data is None:
                continue
            head_tick = branch_data.get("head_tick") or 0
            children = BranchManager.get_children(branch_name)
            status = "✓ ACTIVE" if branch_name == active_branch else "  "
            
            print(f"{branch_name:<40} {int(head_tick):<12} {len(children):<10} {status:<10}")
        
        print(f"\n🌿 Active branch: {active_branch}")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def handle_branch_create(args: Namespace) -> int:
    """
    Handle 'branch create' command - create a new branch at any level.
    
    Examples:
        codevovle branch create --file src/main.py main/feature
        codevovle branch create --file src/main.py main/feature/sub-feature
    
    Args:
        args: Parsed arguments with 'file' and 'branch'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        branch_name = args.branch
        
        if not BranchManager.exists(branch_name):
            BranchManager.create(branch_name)
        
        branch_data = BranchManager.read(branch_name)
        parent = branch_data.get("parent", "N/A")
        
        print(f"✅ Branch created successfully")
        print(f"🌿 Name: {branch_name}")
        print(f"👨‍👩‍👧 Parent: {parent if parent else 'None (root)'}")
        print(f"📍 Path: main/{'/'.join(branch_name.split('/')[1:])}")
        
        return 0
        
    except StorageError as e:
        print(f"❌ Creation error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_branch_delete(args: Namespace) -> int:
    """
    Handle 'branch delete' command - delete a branch and all its children.
    
    Args:
        args: Parsed arguments with 'file' and 'branch'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        branch_name = args.branch
        
        if branch_name == "main":
            print(f"❌ Error: Cannot delete main branch", file=sys.stderr)
            return 1
        
        if not BranchManager.exists(branch_name):
            print(f"❌ Error: Branch does not exist: {branch_name}", file=sys.stderr)
            return 1
        
        children = BranchManager.get_descendants(branch_name)
        
        BranchManager.delete(branch_name)
        
        print(f"✅ Branch deleted")
        print(f"🗑️  Deleted: {branch_name}")
        if children:
            print(f"👶 Also deleted {len(children)} child branch(es)")
        
        return 0
        
    except RecordingError as e:
        print(f"❌ Delete error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_branch_rename(args: Namespace) -> int:
    """
    Handle 'branch rename' command - rename a branch.
    
    Args:
        args: Parsed arguments with 'file', 'branch', and 'new_name'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)
        
        engine.rename_branch(args.branch, args.new_name)
        
        print(f"✅ Branch renamed")
        print(f"📝 From: {args.branch}")
        print(f"📝 To: {args.new_name}")
        
        return 0
        
    except RecordingError as e:
        print(f"❌ Rename error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_branch_jump(args: Namespace) -> int:
    """
    Handle 'branch jump' command - switch to a different branch.
    
    Args:
        args: Parsed arguments with 'file' and 'branch'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)
        
        old_cursor = StateManager.get_cursor(file_path)
        old_branch = old_cursor.get("active_branch", "main")
        
        engine.jump_to_branch(args.branch)
        
        new_cursor = StateManager.get_cursor(file_path)
        new_tick = new_cursor.get("tick_id", 0)
        
        print(f"✅ Branch switched")
        print(f"🔄 From: {old_branch}")
        print(f"🔄 To: {args.branch}")
        print(f"📍 File reconstructed to tick {new_tick}")
        
        return 0
        
    except RecordingError as e:
        print(f"❌ Jump error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_status(args: Namespace) -> int:
    """
    Handle 'status' command - display tracking state.
    
    Args:
        args: Parsed arguments with 'file'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        num_threads = ThreadConfigManager.get_thread_count()
        engine = RecordingEngine(file_path, 1.0, num_threads=num_threads)
        
        status = engine.get_status()
        
        print(f"\n📊 CodeVovle Status: {args.file}")
        print("=" * 50)
        print(f"🌿 Active Branch:    {status['active_branch']}")
        print(f"📍 Current Tick:     {status.get('cursor_tick', 'N/A')}")
        print(f"🔝 Branch Head:      {status.get('branch_head_tick', 'N/A')}")
        print(f"📈 Last Tick ID:     {status.get('last_tick_id', 0)}")
        print(f"🧾 Branch Tick Count: {status.get('branch_tick_count', 0)}")
        print(f"⏱️  Interval:         {status.get('interval', 'unknown')}s")
        print("=" * 50)
        
        return 0
        
    except RecordingError as e:
        print(f"❌ Status error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_insights(args: Namespace) -> int:
    """
    Handle 'insights' command - generate AI code analysis.
    
    Supports multiple AI models: Gemini (default), ChatGPT, Claude
    
    Args:
        args: Parsed arguments with 'file', 'from', 'to', and optional 'model'
        
    Returns:
        Exit code (0 = success, non-zero = error)
    """
    try:
        file_path = str(Path(args.file).resolve())
        model = getattr(args, 'model', 'gemini').lower()
        
        # Check for available models
        available_models = InsightsEngine.get_available_models()
        if not available_models:
            print("❌ Error: No AI API keys configured", file=sys.stderr)
            print("   Add API keys to .env file:", file=sys.stderr)
            print("   - gemini=<YOUR_GEMINI_API_KEY>", file=sys.stderr)
            print("   - chatgpt=<YOUR_CHATGPT_API_KEY>", file=sys.stderr)
            print("   - claude=<YOUR_CLAUDE_API_KEY>", file=sys.stderr)
            return 1
        
        if model not in available_models:
            print(f"❌ Error: API key not configured for {model}", file=sys.stderr)
            print(f"   Available models: {', '.join(available_models)}", file=sys.stderr)
            return 1
        
        print(f"🤖 Generating insights for {args.file}")
        print(f"   Model: {model.upper()}")
        print(f"   From: {args.from_spec}")
        print(f"   To: {args.to_spec}")
        print(f"   Calling {model.upper()} API...")
        
        engine = InsightsEngine(file_path, model=model)
        insights = engine.generate_insights(args.from_spec, args.to_spec)
        
        print(f"\n✅ Insights generated")
        print("=" * 50)
        print(f"🔍 Analysis:")
        analysis = insights.get('insights', {}).get('analysis', 'No analysis available')
        print(analysis)
        print("=" * 50)
        changes = insights.get("key_changes", [])
        if changes:
            for i, change in enumerate(changes[:5], 1):
                print(f"  {i}. {change}")
        else:
            print("  No key changes identified")
        print()
        print(f"⚠️  Risks:")
        risks = insights.get("risks", [])
        if risks:
            for i, risk in enumerate(risks[:3], 1):
                print(f"  {i}. {risk}")
        else:
            print("  No risks identified")
        
        return 0
        
    except InsightsError as e:
        print(f"❌ Insights error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_daemon_start(args: Namespace) -> int:
    """Start background recording daemon."""
    try:
        file_path = str(Path(args.file).resolve())
        interval = float(args.interval)
        
        if interval <= 0:
            print(f"❌ Error: Interval must be positive", file=sys.stderr)
            return 1
        
        print(f"🚀 Starting background recording daemon")
        print(f"   File: {args.file}")
        print(f"   Interval: {interval}s")
        
        pid = DaemonManager.start(file_path, interval)
        
        print(f"✅ Daemon started (PID: {pid})")
        print(f"   Use 'codevovle daemon stop --file {args.file}' to stop")
        
        return 0
        
    except DaemonError as e:
        print(f"❌ Daemon error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_daemon_stop(args: Namespace) -> int:
    """Stop background recording daemon."""
    try:
        file_path = str(Path(args.file).resolve())
        
        print(f"⏹️  Stopping recording daemon")
        print(f"   File: {args.file}")
        
        success = DaemonManager.stop(file_path)
        
        if success:
            print(f"✅ Daemon stopped")
        else:
            print(f"⚠️  No daemon running for {args.file}")
        
        return 0
        
    except DaemonError as e:
        print(f"❌ Daemon error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_daemon_status(args: Namespace) -> int:
    """Show daemon status."""
    try:
        if hasattr(args, 'file') and args.file:
            file_path = str(Path(args.file).resolve())
            status = DaemonManager.status(file_path)
            
            if status:
                print(f"✅ Daemon running for {args.file}")
                print(f"   PID: {status.get('pid')}")
                print(f"   Interval: {status.get('interval')}s")
                print(f"   Running for: {status.get('elapsed_seconds')}s")
            else:
                print(f"⚠️  No daemon running for {args.file}")
        else:
            daemons = DaemonManager.list_all()
            if daemons:
                print(f"✅ {len(daemons)} daemon(s) running:")
                for daemon in daemons:
                    print(f"   • {daemon['file_path']}")
                    print(f"     PID: {daemon['pid']}, Interval: {daemon['interval']}s")
            else:
                print(f"⚠️  No daemons running")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def handle_daemon_list(args: Namespace) -> int:
    """List all running daemons."""
    try:
        daemons = DaemonManager.list_all()
        
        if daemons:
            print(f"📋 Running daemons ({len(daemons)}):")
            print()
            for i, daemon in enumerate(daemons, 1):
                print(f"{i}. {daemon['file_path']}")
                print(f"   PID: {daemon['pid']}")
                print(f"   Interval: {daemon['interval']}s")
                print(f"   Running for: {daemon['elapsed_seconds']}s")
                print()
        else:
            print(f"ℹ️  No daemons running")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def handle_daemon_stop_all(args: Namespace) -> int:
    """Stop all running daemons."""
    try:
        daemons = DaemonManager.list_all()
        
        if not daemons:
            print(f"ℹ️  No daemons to stop")
            return 0
        
        print(f"⏹️  Stopping {len(daemons)} daemon(s)...")
        
        count = DaemonManager.stop_all()
        
        print(f"✅ Stopped {count} daemon(s)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def handle_daemon_set_threads(args: Namespace) -> int:
    """Set number of threads for daemon processing."""
    try:
        num_threads = int(args.count)
        
        from codevovle.storage import ThreadConfigManager
        
        if num_threads < 1 or num_threads > 32:
            print(f"❌ Error: Thread count must be between 1 and 32, got {num_threads}", file=sys.stderr)
            return 1
        
        print(f"⚙️  Setting daemon thread count")
        print(f"   Threads: {num_threads}")
        
        ThreadConfigManager.set_thread_count(num_threads)
        
        print(f"✅ Thread configuration saved")
        print(f"   New daemons will use {num_threads} thread(s)")
        
        return 0
        
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 2


def handle_daemon_get_threads(args: Namespace) -> int:
    """Get current thread configuration."""
    try:
        from codevovle.storage import ThreadConfigManager
        
        num_threads = ThreadConfigManager.get_thread_count()
        
        print(f"📊 Current daemon thread configuration")
        print(f"   Threads: {num_threads}")
        print()
        print(f"To change this setting, use:")
        print(f"   codevovle daemon set-threads --count <number>")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
