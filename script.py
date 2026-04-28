import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_EXECUTE_READWRITE = 0x40

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.VirtualAlloc.argtypes = [
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.VirtualAlloc.restype = wintypes.LPVOID

kernel32.RtlMoveMemory.argtypes = [
    wintypes.LPVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
]
kernel32.RtlMoveMemory.restype = None

kernel32.CreateThread.argtypes = [
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CreateThread.restype = wintypes.HANDLE

kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

INFINITE = 0xFFFFFFFF


def main() -> None:
    parser = argparse.ArgumentParser(description="Load a file's bytes into RWX memory.")
    parser.add_argument("file", help="Path to the file to load (absolute or relative).")
    args = parser.parse_args()

    path = Path(args.file).expanduser().resolve()
    payload = path.read_bytes()
    size = len(payload)
    if size == 0:
        raise SystemExit(f"File is empty: {path}")

    address = kernel32.VirtualAlloc(None, size, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not address:
        raise ctypes.WinError(ctypes.get_last_error())

    print(f"Loaded {size} bytes from {path}")
    print(f"Allocated RWX memory at 0x{address:016X}")

    buffer = (ctypes.c_ubyte * size).from_buffer_copy(payload)
    kernel32.RtlMoveMemory(address, buffer, size)

    written = (ctypes.c_ubyte * size).from_address(address)
    preview = min(16, size)
    print(f"First {preview} bytes in memory:", " ".join(f"{b:02X}" for b in written[:preview]))

    thread_id = wintypes.DWORD(0)
    thread = kernel32.CreateThread(None, 0, address, None, 0, ctypes.byref(thread_id))
    if not thread:
        raise ctypes.WinError(ctypes.get_last_error())

    print(f"Executing in thread id {thread_id.value} (handle 0x{thread:X})")
    kernel32.WaitForSingleObject(thread, INFINITE)
    print(f"Executed @ {datetime.now():%Y-%m-%d %H:%M:%S}")
    input("Press Enter to exit and tear down...")


if __name__ == "__main__":
    main()
