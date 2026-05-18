// src/tree/item.ts — TreeItem for ASCET classes and folders

import * as vscode from 'vscode';
import { AscetTreeNode } from '../cli/types';

const CLASS_TYPE_ICONS: Record<string, string> = {
    esdl:      'symbol-class',
    diagram:   'type-hierarchy',
    parameter: 'symbol-constant',
};

export class AscetClassItem extends vscode.TreeItem {
    /** Forward-slash class path — set for class nodes only */
    public readonly classpath: string | undefined;
    /** Children map — set for folder nodes only */
    public readonly nodeChildren: Record<string, AscetTreeNode> | undefined;

    /** Build from a tree node (folder or class) */
    constructor(node: AscetTreeNode);
    /** Build a plain-text status / message row */
    constructor(message: string, isMessage: true);
    constructor(nodeOrMsg: AscetTreeNode | string, isMessage?: true) {
        if (isMessage || typeof nodeOrMsg === 'string') {
            super(nodeOrMsg as string, vscode.TreeItemCollapsibleState.None);
            return;
        }

        const node = nodeOrMsg as AscetTreeNode;
        super(
            node.name,
            node.type === 'folder'
                ? vscode.TreeItemCollapsibleState.Collapsed
                : vscode.TreeItemCollapsibleState.None
        );

        if (node.type === 'folder') {
            this.nodeChildren = node.children;
            this.iconPath     = new vscode.ThemeIcon('folder');
            this.contextValue = 'ascetFolder';
        } else {
            this.classpath    = node.path;
            this.tooltip      = node.path;
            this.description  = node.path?.includes('/')
                ? node.path.substring(0, node.path.lastIndexOf('/'))
                : '';
            this.contextValue = 'ascetClass';
            const iconName    = CLASS_TYPE_ICONS[node.class_type ?? 'esdl'] ?? 'symbol-class';
            this.iconPath     = new vscode.ThemeIcon(iconName);
            this.command = {
                command:   'ascet.analyzeSelected',
                title:     'Analyze',
                arguments: [node.path],
            };
        }
    }
}
