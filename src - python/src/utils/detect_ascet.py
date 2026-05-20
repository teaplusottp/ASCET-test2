# demo_detect_current_ascet.py
# 依赖：pywin32（win32com / win32api）
# 作用：识别“当前正在使用”的 ASCET 版本（从正在运行的进程中判定）

import os
import re
from typing import Optional, Tuple

def _normalize_version(s: str) -> Optional[str]:
    """把 '6_1_4' / 'v6.1' / '6..1.4' -> '6.1.4'；不匹配返回 None"""
    if not s:
        return None
    s = s.strip().lstrip("vV").replace("_", ".")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"\.+", ".", s)
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", s)
    if not m:
        return None
    major, minor, patch = m.group(1), m.group(2), m.group(3) or "0"
    return f"{int(major)}.{int(minor)}.{int(patch)}"

def _extract_version_from_text(text: str) -> Optional[str]:
    """从任意文本（路径/命令行/标题）提取版本"""
    if not text:
        return None
    m = re.search(r"(\d+)[._](\d+)[._](\d+)", text)
    if m:
        return _normalize_version(".".join(m.groups()))
    m = re.search(r"(\d+)[._](\d+)(?!\d)", text)
    if m:
        return _normalize_version(".".join(m.groups()))
    return None

def _get_file_version_triplet(exe_path: str) -> Optional[str]:
    """读取 EXE 的文件版本，取前三段为 x.y.z"""
    try:
        import win32api
        info = win32api.GetFileVersionInfo(exe_path, "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        # 拼成 a.b.c.d，只取前三段
        ver4 = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
        ver3 = ".".join(ver4.split(".")[:3])
        return _normalize_version(ver3) or _normalize_version(ver4)
    except Exception:
        return None

def detect_current_ascet() -> Optional[Tuple[str, int, str]]:
    """
    返回 (version, pid, exe_path)；未找到则返回 None
    策略：WMI 找出 ascet 主进程 -> 按 CreationDate 最新排序 -> 读文件版本 / 路径提取
    """
    try:
        from win32com.client import GetObject
        wmi = GetObject(r"winmgmts:\\.\root\cimv2")
        rows = wmi.ExecQuery(
            'SELECT ProcessId, Name, ExecutablePath, CommandLine, CreationDate '
            'FROM Win32_Process WHERE Name LIKE "ASCET%" OR Name LIKE "Ascet%"'
        )
    except Exception as e:
        print(f"WMI 访问失败：{e}")
        return None

    # 仅保留主进程（避免把插件/服务当成 ASCET）
    MAIN_NAMES = ("ascet.exe", "ascet64.exe")

    candidates = []
    for p in rows:
        exe = (p.ExecutablePath or "").strip()
        if not exe or not os.path.exists(exe):
            continue
        low = exe.lower()
        if not any(n in low for n in MAIN_NAMES):
            continue
        candidates.append({
            "pid": int(p.ProcessId),
            "exe": exe,
            "cmd": (p.CommandLine or ""),
            "creation": str(p.CreationDate or ""),
        })

    if not candidates:
        return None

    # 按创建时间倒序（最新启动的优先）
    candidates.sort(key=lambda x: x["creation"], reverse=True)

    for c in candidates:
        ver = _get_file_version_triplet(c["exe"]) \
              + "" if False else None  # 只为结构清晰，占位
        if not ver:
            # 从命令行或路径兜底提取 6_1_4 / 6.1.4
            ver = _extract_version_from_text(c["cmd"] + " " + c["exe"])
        if ver:
            return ver, c["pid"], c["exe"]

    # 如果都没有版本信息，仍返回最新的可执行信息（版本为 unknown）
    top = candidates[0]
    return ("unknown", top["pid"], top["exe"])

if __name__ == "__main__":
    info = detect_current_ascet()
    if info is None:
        print("未发现正在运行的 ASCET 主进程（ascet.exe / ascet64.exe / ascetstudio.exe）。")
    else:
        ver, pid, exe = info
        print("✅ 当前正在使用的 ASCET：")
        print(f"  版本       : {ver}")
        print(f"  进程 PID   : {pid}")
        print(f"  可执行文件 : {exe}")
