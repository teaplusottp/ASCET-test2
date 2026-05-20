// src/queue/scanQueue.ts — Scan queue for batch AI review  v0.6.0
//
// Cho phép user thêm nhiều class vào queue rồi chạy tuần tự.
// Emit events để UI (TreeView, StatusBar) cập nhật realtime.

import * as vscode from "vscode";
import { v4 as uuidv4 } from "uuid";
import { runAscetCli } from "../cli/runner";
import { getOutputChannel } from "../state";
import type { ScanQueueItem, AnalyzeCodeResult } from "../cli/types";

export class ScanQueue {
  private _items: Map<string, ScanQueueItem> = new Map();
  private _running = false;

  private _onDidChange = new vscode.EventEmitter<ScanQueueItem[]>();
  readonly onDidChange = this._onDidChange.event;

  // ── Public API ──────────────────────────────────────────────────────────────

  /** Thêm một class vào queue. Trả về item ID. */
  enqueue(class_path: string): string {
    const id = uuidv4();
    const item: ScanQueueItem = {
      id,
      class_path,
      status: "pending",
      addedAt: new Date(),
    };
    this._items.set(id, item);
    this._fire();
    this._processNext();
    return id;
  }

  /** Thêm nhiều class cùng lúc. */
  enqueueMany(class_paths: string[]): string[] {
    return class_paths.map((p) => this.enqueue(p));
  }

  /** Xóa một item khỏi queue (chỉ khi pending). */
  remove(id: string): boolean {
    const item = this._items.get(id);
    if (!item || item.status === "running") { return false; }
    this._items.delete(id);
    this._fire();
    return true;
  }

  /** Xóa tất cả items đã done/error. */
  clearFinished(): void {
    for (const [id, item] of this._items) {
      if (item.status === "done" || item.status === "error") {
        this._items.delete(id);
      }
    }
    this._fire();
  }

  /** Xóa toàn bộ queue (kể cả pending). */
  clearAll(): void {
    for (const [id, item] of this._items) {
      if (item.status !== "running") {
        this._items.delete(id);
      }
    }
    this._fire();
  }

  get items(): ScanQueueItem[] {
    return Array.from(this._items.values());
  }

  get pendingCount(): number {
    return this.items.filter((i) => i.status === "pending").length;
  }

  get isRunning(): boolean {
    return this._running;
  }

  // ── Internal ────────────────────────────────────────────────────────────────

  private _fire(): void {
    this._onDidChange.fire(this.items);
  }

  private async _processNext(): Promise<void> {
    if (this._running) { return; }

    const next = this.items.find((i) => i.status === "pending");
    if (!next) { return; }

    this._running = true;
    next.status = "running";
    this._fire();

    const log = getOutputChannel();
    log.appendLine(`[Queue] Scanning: ${next.class_path}`);

    try {
      const result = await runAscetCli<AnalyzeCodeResult>("analyze_code", [
        "--path", next.class_path,
        "--mode", "direct",
      ]);

      if (result.success && result.data) {
        next.status = "done";
        next.result = result.data;
        log.appendLine(
          `[Queue] ✅ Done: ${next.class_path} — ${result.data.summary}`
        );
      } else {
        next.status = "error";
        next.error = result.error ?? "Unknown error";
        log.appendLine(
          `[Queue] ❌ Error: ${next.class_path} — ${next.error}`
        );
      }
    } catch (e: any) {
      next.status = "error";
      next.error = e.message;
      log.appendLine(`[Queue] ❌ Exception: ${next.class_path} — ${e.message}`);
    } finally {
      next.finishedAt = new Date();
      this._running = false;
      this._fire();
      this._processNext();
    }
  }
}

// Singleton
let _instance: ScanQueue | undefined;
export function getScanQueue(): ScanQueue {
  if (!_instance) { _instance = new ScanQueue(); }
  return _instance;
}