// src/tree/provider.ts — TreeDataProvider for the ASCET class tree

import * as vscode from 'vscode';
import { AscetTreeNode, AscetTreeRoot } from '../cli/types';
import { runAscetCli } from '../cli/runner';
import { AscetClassItem } from './item';
import { log } from '../ui/logger';

export class AscetClassTreeProvider implements vscode.TreeDataProvider<AscetClassItem> {
    private _onDidChangeTreeData =
        new vscode.EventEmitter<AscetClassItem | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private treeRoot: AscetTreeRoot | null = null;
    private loading                         = false;
    private errorMsg: string | undefined;

    getTreeItem(element: AscetClassItem): vscode.TreeItem { return element; }

    getChildren(element?: AscetClassItem): AscetClassItem[] {
        if (this.loading) {
            return [new AscetClassItem('$(sync~spin)  Đang quét database...', true)];
        }
        if (this.errorMsg) {
            return [new AscetClassItem(`$(error)  ${this.errorMsg}`, true)];
        }
        if (!this.treeRoot) {
            return [new AscetClassItem('$(refresh)  Nhấn Refresh để tải danh sách class', true)];
        }

        const childrenMap: Record<string, AscetTreeNode> =
            element?.nodeChildren ?? this.treeRoot.children;

        return Object.values(childrenMap)
            .sort((a, b) => {
                if (a.type !== b.type) { return a.type === 'folder' ? -1 : 1; }
                return a.name.localeCompare(b.name);
            })
            .map(node => new AscetClassItem(node));
    }

    async refresh(token?: vscode.CancellationToken): Promise<void> {
        this.loading  = true;
        this.errorMsg = undefined;
        this._onDidChangeTreeData.fire(undefined);

        log('[Tree] Refreshing class tree...');
        const result = await runAscetCli<AscetTreeRoot>('list_tree', [], token);

        this.loading = false;
        if (result.success) {
            this.treeRoot = result.data;
            const count   = this._countClasses(result.data.children);
            log(`[Tree] Loaded ${count} ESDL classes.`);
        } else {
            this.errorMsg = result.error;
            log(`[Tree] Error: ${result.error}`);
            if (result.detail) { log(`[Tree] Detail:\n${result.detail}`); }
        }
        this._onDidChangeTreeData.fire(undefined);
    }

    /** Flat sorted list of all class paths — used by QuickPick search */
    getClassList(): string[] {
        if (!this.treeRoot) { return []; }
        const out: string[] = [];
        this._collectClasses(this.treeRoot.children, out);
        return out.sort();
    }

    private _countClasses(children: Record<string, AscetTreeNode>): number {
        let n = 0;
        for (const node of Object.values(children)) {
            if (node.type === 'class') { n++; }
            else if (node.children)   { n += this._countClasses(node.children); }
        }
        return n;
    }

    private _collectClasses(children: Record<string, AscetTreeNode>, out: string[]): void {
        for (const node of Object.values(children)) {
            if (node.type === 'class' && node.path) { out.push(node.path); }
            else if (node.children)                 { this._collectClasses(node.children, out); }
        }
    }
}
