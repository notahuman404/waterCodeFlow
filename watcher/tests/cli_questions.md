# Questions for implementing CLI and integrating with Watcher architecture

Please answer these questions in a separate file named `answers.md` at repository root.

**Watcher Core Behavior & Lifecycle**

1. What exact lifecycle states must the Watcher core expose (e.g., `init`, `running`, `paused`, `stopping`, `stopped`, `error`), and what transitions between states are allowed and atomic?  

2. On startup, which initialization steps are mandatory and must be completed before accepting CLI requests (e.g., config load, permission checks, file system watches, persistent queue initialization)? Specify ordering requirements and which steps may fail non-fatally.

3. Is there a required graceful shutdown procedure (timeout, drain buffers, run callbacks to completion)? If so, what timeout(s) and what shutdown guarantees (e.g., flush-to-disk, best-effort only) must the implementation provide?

**Data Flow, Format, and Ownership**

4. What is the canonical schema for a single tracked data item sent from core → CLI or core → callback (fields, types, required vs optional, timestamp format/timezone, monotonic vs wall-clock timestamps)?

5. When forwarding tracked data to a custom callback `main`, must the Watcher hand over ownership (zero-copy) or provide an immutable copy/serialized payload? If serialized, which formats are allowed (JSON, newline-delimited JSON, MessagePack, pickle)?

6. For batched deliveries, what batching semantics are required (max batch size, max latency window, event ordering inside a batch)? Are partial batches allowed on flush/shutdown?

**--file-to-track and file selection semantics**

7. For `--file-to-track`, what are the exact accepted forms (single file path, glob pattern, directory, recursive flag)? How should newly created files matching the pattern be handled at runtime?

8. How must the Watcher treat symlinks, mount points, and files moved/renamed while being tracked? Should tracking follow inode, path, or stop tracking on rename?

9. Are exclusions required (ignore patterns)? If so, how should precedence be resolved between include and exclude patterns?

**Variable Selection Flags**

10. What is the precise syntax for specifying variables to track (e.g., `module.var`, `regex`, JSONPath, dotted names)? Are wildcards and namespaces allowed and how are they matched?  

11. What variable scopes are supported (global/module-level, local stack frame, instance attributes)? If local or stack-frame-level tracking is supported, how will the CLI identify the target execution context/frames to inspect?

12. How should naming collisions be resolved when two tracked variables share the same visible name from different modules/instances? Is an opaque identifier required in payloads to disambiguate?

**Custom Callback Integration**

13. For the custom callback flag (path to file with `main`), what is the required `main` function signature (sync vs async, parameters, return type)? Provide an exact prototype expected by the core.

14. What are the accepted behaviors of `main` return values and exceptions? Must exceptions be caught and logged, retried, or cause Watcher to exit? Define retry/backoff policy if any.

15. Should custom callbacks be executed in-process (same process) or out-of-process (child process, container)? If in-process, what reentrancy and safety guarantees are required? If out-of-process, what IPC protocol and serialization is mandated?

16. What execution resource constraints must be enforced on custom callbacks (CPU timeouts, memory limits, execution timeouts)? Should the Watcher forcibly terminate callbacks that exceed limits?

17. Are callbacks allowed network/file/OS access? If restrictions are required, what sandboxing level is expected (none, import whitelist, seccomp, chroot, separate user)?

**Threading, Concurrency & Execution Model**

18. What concurrency model must the Watcher core use for monitoring and delivery (single-threaded event loop, threadpool, per-callback worker threads, async tasks)? Specify concurrency constraints and maximum parallel callback invocations.

19. If multiple variables/events arrive concurrently, what ordering guarantees must core provide per-file, per-variable, and global? Are concurrent deliveries allowed to different callbacks?

20. Describe required synchronization behavior: which data structures require locking, and are there hard real-time constraints preventing blocking of watcher loops (i.e., must callback execution never block watcher I/O)?

**Performance, Memory, and Persistence**

21. What throughput and latency targets must the Watcher meet (events/sec and max end-to-end latency from capture→callback under nominal and peak load)?

22. What in-memory buffering limits are acceptable before backpressure or data-drop policies must trigger? Define default buffer sizes and max retention in memory.

23. Is persistent on-disk buffering required as a fallback when callbacks are slow or fail? If yes, define file format, max on-disk size, eviction policy, and recovery semantics on restart.

**Failure Modes, Error Handling & Observability**

24. For transient callback failures, define an exact retry policy (number of retries, exponential backoff parameters, when to move to a dead-letter queue) and observable signals that must be emitted.

25. In case of unrecoverable core errors (internal panic, memory exhaustion), what minimum diagnostics/logging must be written, and are crash dumps or core files required/allowed?

26. What observability endpoints/metrics must be implemented for testing and operations (e.g., `metrics`: events_received, events_sent, events_dropped, callbacks_failed, latency_histogram)? Define name and unit for each required metric.

**Security, Sandboxing & Data Sensitivity**

27. Will the Watcher ever handle sensitive data (secrets, PII)? If yes, what redaction, encryption-at-rest, and access-control requirements must the implementation and CLI enforce?

28. For executing user-supplied callbacks, must the system provide an opt-in security policy (allowed imports, disabled syscalls)? If so, provide a policy model (deny-by-default whitelist or allow-by-default blacklist) and enforcement mechanism.

**CLI Integration & UX**

29. For the new flags (`--file-to-track`, variable selection flags, custom callback path) and existing flags, define precedence and validation rules (which flag overrides which, what combination is invalid, and priority of config file vs CLI vs env vars).

30. Define required CLI exit codes for common outcomes (success, validation error, runtime error, callback error, partial-failure with data persisted). Provide numeric codes and mapping to human-readable reasons.
