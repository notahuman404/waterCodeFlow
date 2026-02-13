"""
Daemon command handlers (appended to handlers.py).

These functions are added to the handlers module to support daemon commands.
"""

# Add this to the end of codevovle/handlers.py


def handle_daemon_start(args) -> int:
    """Start background recording daemon."""
    try:
        file_path = str(Path(args.file).resolve())
        interval = float(args.interval)
        
        if interval <= 0:
            print(f"❌ Error: Interval must be positive", file=sys.stderr)
            return 1
        
        from codevovle.storage import ThreadConfigManager
        num_threads = ThreadConfigManager.get_thread_count()
        
        print(f"🚀 Starting background recording daemon")
        print(f"   File: {args.file}")
        print(f"   Interval: {interval}s")
        print(f"   Threads: {num_threads}")
        
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


def handle_daemon_stop(args) -> int:
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


def handle_daemon_status(args) -> int:
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


def handle_daemon_list(args) -> int:
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


def handle_daemon_stop_all(args) -> int:
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

def handle_daemon_set_threads(args) -> int:
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


def handle_daemon_get_threads(args) -> int:
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