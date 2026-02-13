/**
 * GlueClient: subprocess bridge to glue adapter (Python).
 * Manages JSON RPC-style communication with glue/adapter.py
 */
import { spawn, ChildProcess } from "child_process";
import { randomUUID } from "crypto";
import * as path from "path";
import { GlueCommand, GlueResponse } from "./types";

type ResponseCallback = (response: GlueResponse) => void;

export class GlueClient {
  private subprocess: ChildProcess | null = null;
  private pendingRequests: Map<string, ResponseCallback> = new Map();
  private ready: Promise<void>;
  private readyResolve: (() => void) | null = null;
  private lines: string[] = [];

  constructor() {
    this.ready = new Promise((resolve) => {
      this.readyResolve = resolve;
    });
  }

  /**
   * Spawn Python subprocess running glue adapter.
   * extensionPath is the editor/ directory.
   * We need to traverse up one level to reach the project root where glue/ is located.
   */
  async spawn(extensionPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // extensionPath = /workspaces/WaterCodeFlow/editor
        // We need to run from project root: /workspaces/WaterCodeFlow
        const projectRoot = path.dirname(extensionPath);

        this.subprocess = spawn("python3", ["-m", "glue.adapter"], {
          cwd: projectRoot,
          stdio: ["pipe", "pipe", "pipe"],
          env: { ...process.env },
        });

        this.subprocess.on("error", (err) => {
          console.error("[GlueClient] subprocess error:", err);
          reject(err);
        });

        this.subprocess.stdout!.on("data", (data) => {
          this.handleData(data.toString());
        });

        this.subprocess.stderr!.on("data", (data) => {
          console.error("[GlueClient] stderr:", data.toString());
        });

        // Wait a moment for subprocess to initialize
        setTimeout(() => {
          if (this.readyResolve) {
            this.readyResolve();
          }
          resolve();
        }, 500);
      } catch (err) {
        reject(err);
      }
    });
  }

  /**
   * Send a command to glue and wait for response.
   */
  async send<T = any>(command: Omit<GlueCommand, "id">): Promise<T> {
    await this.ready;

    if (!this.subprocess || !this.subprocess.stdin) {
      throw new Error("GlueClient not initialized. Call spawn() first.");
    }

    const id = randomUUID();
    const fullCommand: GlueCommand = { ...command, id } as GlueCommand;

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, (response: GlueResponse) => {
        if (response.success) {
          resolve(response.result as T);
        } else {
          reject(
            new Error(
              `[${response.errorType || "GlueError"}] ${response.error}`
            )
          );
        }
      });

      const cmdJson = JSON.stringify(fullCommand) + "\n";
      this.subprocess!.stdin!.write(cmdJson);
    });
  }

  /**
   * Handle incoming data from subprocess.
   * Accumulates lines and processes complete JSON objects.
   */
  private handleData(chunk: string): void {
    const allLines = (this.lines.join("") + chunk).split("\n");

    // Last element may be incomplete, keep it in this.lines
    this.lines = [allLines[allLines.length - 1]];

    for (let i = 0; i < allLines.length - 1; i++) {
      const line = allLines[i].trim();
      if (!line) continue;

      try {
        const response: GlueResponse = JSON.parse(line);
        const callback = this.pendingRequests.get(response.id);

        if (callback) {
          this.pendingRequests.delete(response.id);
          callback(response);
        } else {
          console.warn(
            "[GlueClient] received response for unknown request:",
            response.id
          );
        }
      } catch (err) {
        console.error("[GlueClient] failed to parse JSON:", line, err);
      }
    }
  }

  /**
   * Kill subprocess.
   */
  kill(): void {
    if (this.subprocess && !this.subprocess.killed) {
      this.subprocess.kill();
      this.subprocess = null;
    }
  }

  /**
   * Check if subprocess is alive.
   */
  isAlive(): boolean {
    return this.subprocess !== null && !this.subprocess.killed;
  }
}

// Singleton instance
let instance: GlueClient | null = null;

export function getGlueClient(): GlueClient {
  if (!instance) {
    instance = new GlueClient();
  }
  return instance;
}
