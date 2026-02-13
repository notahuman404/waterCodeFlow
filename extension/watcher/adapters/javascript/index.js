/**
 * Watcher JavaScript Adapter
 * Watches TypedArray and ArrayBuffer mutations
 */

// ============================================================================
// Constants & Flags
// ============================================================================

const FLAG_TRACK_THREADS = 1 << 0;
const FLAG_TRACK_SQL = 1 << 1;
const FLAG_TRACK_ALL = 1 << 2;
const FLAG_TRACK_LOCALS = 1 << 3;

const PAGE_SIZE = 4096;

// Lazy load native binding
let binding = null;
function getBinding() {
    if (binding === null) {
        binding = require('./build/Release/watcher_core.node');
    }
    return binding;
}

// ============================================================================
// SQL Context Manager (AsyncLocalStorage)
// ============================================================================

const { AsyncLocalStorage } = require('async_hooks');

class SQLContextManager {
    constructor() {
        this.storage = new AsyncLocalStorage();
        this.stack = [];
    }
    
    pushContext(query, params = null) {
        const context = {
            query,
            params,
            tid: process.pid,
            timestamp: Date.now()
        };
        this.stack.push(context);
        return context;
    }
    
    popContext() {
        return this.stack.pop();
    }
    
    currentContext() {
        return this.stack.length > 0 ? this.stack[this.stack.length - 1] : null;
    }
    
    clear() {
        this.stack = [];
    }
}

const sqlContext = new SQLContextManager();

// ============================================================================
// SQL Monkey-Patching
// ============================================================================

function patchPG(trackSQL = false) {
    if (!trackSQL) return;
    
    try {
        const pg = require('pg');
        const originalQuery = pg.Client.prototype.query;
        
        pg.Client.prototype.query = function(text, values, callback) {
            sqlContext.pushContext(text, values);
            
            // Handle both callback and promise styles
            if (typeof callback === 'function') {
                return originalQuery.call(this, text, values, (...args) => {
                    sqlContext.popContext();
                    callback(...args);
                });
            } else {
                const promise = originalQuery.call(this, text, values);
                return promise
                    .then(result => {
                        sqlContext.popContext();
                        return result;
                    })
                    .catch(err => {
                        sqlContext.popContext();
                        throw err;
                    });
            }
        };
    } catch (e) {
        // pg not available
    }
}

function patchMySQL2(trackSQL = false) {
    if (!trackSQL) return;
    
    try {
        const mysql2 = require('mysql2');
        const originalQuery = mysql2.Connection.prototype.query;
        
        mysql2.Connection.prototype.query = function(sql, values, callback) {
            if (typeof values === 'function') {
                callback = values;
                values = [];
            }
            
            sqlContext.pushContext(sql, values);
            
            if (callback) {
                return originalQuery.call(this, sql, values, (...args) => {
                    sqlContext.popContext();
                    callback(...args);
                });
            } else {
                return originalQuery.call(this, sql, values);
            }
        };
    } catch (e) {
        // mysql2 not available
    }
}

function patchSQLite3(trackSQL = false) {
    if (!trackSQL) return;
    
    try {
        const sqlite3 = require('sqlite3');
        const originalRun = sqlite3.Database.prototype.run;
        
        sqlite3.Database.prototype.run = function(sql, params, callback) {
            // Handle various parameter combinations
            if (typeof params === 'function') {
                callback = params;
                params = [];
            }
            
            sqlContext.pushContext(sql, params);
            
            if (callback) {
                return originalRun.call(this, sql, params, function(...args) {
                    sqlContext.popContext();
                    callback.apply(this, args);
                });
            } else {
                return originalRun.call(this, sql, params);
            }
        };
    } catch (e) {
        // sqlite3 not available
    }
}

// ============================================================================
// Watcher Core (Singleton)
// ============================================================================

class WatcherCore {
    static instance = null;
    static lock = false;
    static initialized = false;
    
    constructor() {
        if (WatcherCore.initialized) return;
        
        this.core = getBinding();
        this.variables = new Map();
        this.trackSQL = false;
        this.trackThreads = false;
        this.trackLocals = false;
        
        WatcherCore.initialized = true;
    }
    
    static getInstance() {
        if (WatcherCore.instance === null) {
            if (!WatcherCore.lock) {
                WatcherCore.lock = true;
                WatcherCore.instance = new WatcherCore();
            }
        }
        return WatcherCore.instance;
    }
    
    initialize(outputDir = './watcher_output', options = {}) {
        const {
            trackThreads = false,
            trackLocals = false,
            trackSQL = false
        } = options;
        
        this.trackThreads = trackThreads;
        this.trackLocals = trackLocals;
        this.trackSQL = trackSQL;
        
        // Create output directory if needed
        const fs = require('fs');
        const path = require('path');
        const fullPath = path.resolve(outputDir);
        if (!fs.existsSync(fullPath)) {
            fs.mkdirSync(fullPath, { recursive: true });
        }
        
        // Initialize C++ core
        try {
            this.core.initialize(fullPath);
        } catch (e) {
            throw new Error(`Failed to initialize watcher: ${e.message}`);
        }
        
        // Patch SQL libraries if enabled
        if (trackSQL) {
            patchPG(true);
            patchMySQL2(true);
            patchSQLite3(true);
        }
        
        return this.core.start();
    }
    
    watch(buffer, options = {}) {
        const {
            name = 'var',
            trackThreads = null,
            trackLocals = null,
            trackSQL = null,
            mutationDepth = 'FULL'
        } = options;
        
        if (!(buffer instanceof ArrayBuffer) && !(buffer instanceof SharedArrayBuffer) &&
            !ArrayBuffer.isView(buffer)) {
            throw new TypeError('watch() only accepts TypedArray/ArrayBuffer. Pass buffer-backed values only.');
        }
        
        // Get buffer from TypedArray view if needed
        let actualBuffer = buffer;
        if (ArrayBuffer.isView(buffer)) {
            actualBuffer = buffer.buffer;
        }
        
        // Get backing store pointer (simplified - in real impl use WeakMap to track)
        // Note: This is a simplified stub - actual implementation would need
        // to extract the backing store address from V8 internals
        const pageBase = actualBuffer;
        const pageSize = Math.min(actualBuffer.byteLength, PAGE_SIZE);
        
        // Prepare flags
        let flags = 0;
        if (trackThreads === null ? this.trackThreads : trackThreads) {
            flags |= FLAG_TRACK_THREADS;
        }
        if (trackLocals === null ? this.trackLocals : trackLocals) {
            flags |= FLAG_TRACK_LOCALS;
        }
        if (trackSQL === null ? this.trackSQL : trackSQL) {
            flags |= FLAG_TRACK_SQL;
        }
        
        // Register with C++ core
        const varID = this.core.registerPage(
            pageBase,
            pageSize,
            name,
            flags
        );
        
        if (!varID || varID.startsWith('Error')) {
            throw new Error(`Failed to register variable: ${varID}`);
        }
        
        // Store registration
        this.variables.set(varID, {
            buffer: actualBuffer,
            name: name,
            registered: Date.now()
        });
        
        return buffer;  // Return original buffer for direct access
    }
    
    unwatch(varID) {
        return this.core.unregisterPage(varID);
    }
    
    stop() {
        // Unregister all variables
        for (const varID of this.variables.keys()) {
            this.core.unregisterPage(varID);
        }
        this.variables.clear();
        
        // Stop core
        return this.core.stop();
    }
    
    getState() {
        const stateCodes = [
            'UNINITIALIZED',
            'INITIALIZED',
            'RUNNING',
            'PAUSED',
            'STOPPED',
            'ERROR'
        ];
        return stateCodes[this.core.getState()] || 'UNKNOWN';
    }
}

// ============================================================================
// Public API
// ============================================================================

function watch(buffer, options) {
    return WatcherCore.getInstance().watch(buffer, options);
}

module.exports = {
    watch,
    WatcherCore,
    SQLContextManager: sqlContext,
};
