"use strict";
// src/queue/scanQueue.ts — Scan queue for batch AI review  v0.6.0
//
// Cho phép user thêm nhiều class vào queue rồi chạy tuần tự.
// Emit events để UI (TreeView, StatusBar) cập nhật realtime.
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ScanQueue = void 0;
exports.getScanQueue = getScanQueue;
const vscode = __importStar(require("vscode"));
const uuid_1 = require("uuid");
const runner_1 = require("../cli/runner");
const state_1 = require("../state");
class ScanQueue {
    constructor() {
        this._items = new Map();
        this._running = false;
        this._onDidChange = new vscode.EventEmitter();
        this.onDidChange = this._onDidChange.event;
    }
    // ── Public API ──────────────────────────────────────────────────────────────
    /** Thêm một class vào queue. Trả về item ID. */
    enqueue(class_path) {
        const id = (0, uuid_1.v4)();
        const item = {
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
    enqueueMany(class_paths) {
        return class_paths.map((p) => this.enqueue(p));
    }
    /** Xóa một item khỏi queue (chỉ khi pending). */
    remove(id) {
        const item = this._items.get(id);
        if (!item || item.status === "running") {
            return false;
        }
        this._items.delete(id);
        this._fire();
        return true;
    }
    /** Xóa tất cả items đã done/error. */
    clearFinished() {
        for (const [id, item] of this._items) {
            if (item.status === "done" || item.status === "error") {
                this._items.delete(id);
            }
        }
        this._fire();
    }
    /** Xóa toàn bộ queue (kể cả pending). */
    clearAll() {
        for (const [id, item] of this._items) {
            if (item.status !== "running") {
                this._items.delete(id);
            }
        }
        this._fire();
    }
    get items() {
        return Array.from(this._items.values());
    }
    get pendingCount() {
        return this.items.filter((i) => i.status === "pending").length;
    }
    get isRunning() {
        return this._running;
    }
    // ── Internal ────────────────────────────────────────────────────────────────
    _fire() {
        this._onDidChange.fire(this.items);
    }
    async _processNext() {
        if (this._running) {
            return;
        }
        const next = this.items.find((i) => i.status === "pending");
        if (!next) {
            return;
        }
        this._running = true;
        next.status = "running";
        this._fire();
        const log = (0, state_1.getOutputChannel)();
        log.appendLine(`[Queue] Scanning: ${next.class_path}`);
        try {
            const result = await (0, runner_1.runAscetCli)("ai_review", [
                next.class_path,
                "--mode", "severity",
            ]);
            if (result.success && result.data) {
                next.status = "done";
                next.result = result.data;
                log.appendLine(`[Queue] ✅ Done: ${next.class_path} — ${result.data.summary}`);
            }
            else {
                next.status = "error";
                next.error = result.error ?? "Unknown error";
                log.appendLine(`[Queue] ❌ Error: ${next.class_path} — ${next.error}`);
            }
        }
        catch (e) {
            next.status = "error";
            next.error = e.message;
            log.appendLine(`[Queue] ❌ Exception: ${next.class_path} — ${e.message}`);
        }
        finally {
            next.finishedAt = new Date();
            this._running = false;
            this._fire();
            this._processNext();
        }
    }
}
exports.ScanQueue = ScanQueue;
// Singleton
let _instance;
function getScanQueue() {
    if (!_instance) {
        _instance = new ScanQueue();
    }
    return _instance;
}
//# sourceMappingURL=scanQueue.js.map