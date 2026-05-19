"use strict";
// src/tree/item.ts — TreeItem for ASCET classes and folders
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
exports.AscetClassItem = void 0;
const vscode = __importStar(require("vscode"));
const CLASS_TYPE_ICONS = {
    esdl: 'symbol-class',
    diagram: 'type-hierarchy',
    parameter: 'symbol-constant',
};
class AscetClassItem extends vscode.TreeItem {
    constructor(nodeOrMsg, isMessage) {
        if (isMessage || typeof nodeOrMsg === 'string') {
            super(nodeOrMsg, vscode.TreeItemCollapsibleState.None);
            return;
        }
        const node = nodeOrMsg;
        super(node.name, node.type === 'folder'
            ? vscode.TreeItemCollapsibleState.Collapsed
            : vscode.TreeItemCollapsibleState.None);
        if (node.type === 'folder') {
            this.nodeChildren = node.children;
            this.iconPath = new vscode.ThemeIcon('folder');
            this.contextValue = 'ascetFolder';
        }
        else {
            this.classpath = node.path;
            this.tooltip = node.path;
            this.description = node.path?.includes('/')
                ? node.path.substring(0, node.path.lastIndexOf('/'))
                : '';
            this.contextValue = 'ascetClass';
            const iconName = CLASS_TYPE_ICONS[node.class_type ?? 'esdl'] ?? 'symbol-class';
            this.iconPath = new vscode.ThemeIcon(iconName);
            this.command = {
                command: 'ascet.analyzeSelected',
                title: 'Analyze',
                arguments: [node.path],
            };
        }
    }
}
exports.AscetClassItem = AscetClassItem;
//# sourceMappingURL=item.js.map