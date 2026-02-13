/**
 * TypeScript types for WaterCodeFlow extension integration.
 */

export interface Recording {
  tick_id: number;
  lines_added: number;
  lines_removed: number;
  size_bytes: number;
  diff?: string;
}

export interface Run {
  run_id: number;
  start_tick: number;
  end_tick: number;
  tick_count: number;
  estimated_duration_seconds: number;
}

export interface Branch {
  name: string;
  label: string;
  parent: string | null;
  head_tick: number;
  forked_at_tick: number | null;
}

export interface Cursor {
  branch: string;
  tick: number | null;
}

export interface Status {
  ready: boolean;
  recordings_count: number;
  tick_counter: number;
  branches: Branch[];
  [key: string]: any;
}

export interface Variable {
  name: string;
  scope: string;
  line_no?: number;
}

export interface VariableTimelineEntry {
  tick: string;
  line_no: number;
  snippet: string;
  context: string;
  match_count: number;
}

export interface Insights {
  model: string;
  from_tick: number;
  to_tick: number;
  diff_summary: string;
  change_type: string;
  affected_lines: number[];
  severity: string;
}

export interface WatchProxy {
  id: string;
  name: string | null;
  scope: string | null;
  file_path: string | null;
  value_repr: string;
}

export interface GlueCommand {
  id: string;
  command: string;
  [key: string]: any;
}

export interface GlueResponse {
  id: string;
  success: boolean;
  result?: any;
  error?: string;
  errorType?: string;
  traceback?: string;
}

export interface WebviewMessage {
  command: string;
  [key: string]: any;
}

export interface BroadcastMessage {
  type: string;
  [key: string]: any;
}
