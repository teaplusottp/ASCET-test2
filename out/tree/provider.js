"use strict";
// src/tree/provider.ts — TreeDataProvider for the ASCET class tree  v0.6.0
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
exports.AscetClassTreeProvider = void 0;
const vscode = __importStar(require("vscode"));
const runner_1 = require("../cli/runner");
const item_1 = require("./item");
const logger_1 = require("../ui/logger");
class AscetClassTreeProvider {
    constructor() {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.treeRoot = null;
        this.loading = false;
    }
    getTreeItem(element) { return element; }
    getChildren(element) {
        if (this.loading) {
            return [new item_1.AscetClassItem("$(sync~spin)  Đang quét database...", true)];
        }
        if (this.errorMsg) {
            return [new item_1.AscetClassItem(`$(error)  ${this.errorMsg}`, true)];
        }
        if (!this.treeRoot) {
            return [
                new item_1.AscetClassItem("$(refresh)  Nhấn Refresh để tải danh sách class", true),
            ];
        }
        const childrenMap = element?.nodeChildren ?? this.treeRoot.children;
        return Object.values(childrenMap)
            .sort((a, b) => {
            if (a.type !== b.type) {
                return a.type === "folder" ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        })
            .map((node) => new item_1.AscetClassItem(node));
    }
    async refresh(token) {
        this.loading = true;
        this.errorMsg = undefined;
        this._onDidChangeTreeData.fire(undefined);
        (0, logger_1.log)("[Tree] Refreshing class tree...");
        const result = await (0, runner_1.runAscetCli)("list_tree", [], token);
        this.loading = false;
        if (result.success && result.data) {
            this.treeRoot = result.data;
            const count = this._countClasses(result.data.children);
            (0, logger_1.log)(`[Tree] Loaded ${count} ASCET classes.`);
        }
        else {
            this.errorMsg = result.error;
            (0, logger_1.log)(`[Tree] Error: ${result.error}`);
            if (result.detail) {
                (0, logger_1.log)(`[Tree] Detail:\n${result.detail}`);
            }
        }
        this._onDidChangeTreeData.fire(undefined);
    }
    /** Flat sorted list of all class paths — used by QuickPick search */
    getClassList() {
        if (!this.treeRoot) {
            return [];
        }
        const out = [];
        this._collectClasses(this.treeRoot.children, out);
        return out.sort();
    }
    _countClasses(children) {
        let n = 0;
        for (const node of Object.values(children)) {
            if (node.type === "class") {
                n++;
            }
            else if (node.children) {
                n += this._countClasses(node.children);
            }
        }
        return n;
    }
    _collectClasses(children, out) {
        for (const node of Object.values(children)) {
            if (node.type === "class" && node.path) {
                out.push(node.path);
            }
            else if (node.children) {
                this._collectClasses(node.children, out);
            }
        }
    }
}
exports.AscetClassTreeProvider = AscetClassTreeProvider;
//# sourceMappingURL=provider.js.map