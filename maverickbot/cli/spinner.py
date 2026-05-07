"""CLI animations: Spinner, Process bar, and Progress bar."""

import asyncio
import sys
import threading
import time
from typing import Optional
from functools import wraps

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

COLORS = {
    'cyan': '\033[36m',
    'green': '\033[32m',
    'magenta': '\033[35m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'light_magenta': '\033[95m',
    'reset': '\033[0m'
}

COLOR_NAMES = ['cyan', 'green', 'magenta', 'yellow', 'blue', 'light_magenta']
_color_index = 0


def get_next_color() -> str:
    """Get next color in rotation."""
    global _color_index
    color = COLOR_NAMES[_color_index]
    _color_index = (_color_index + 1) % len(COLOR_NAMES)
    return color


def reset_color_cycle():
    """Reset color cycle to start."""
    global _color_index
    _color_index = 0


class Spinner:
    """Spinning cursor animation for 'thinking' state."""

    FRAMES = ['|', '/', '-', '\\']

    def __init__(self, message: str = "Thinking", color: str = None):
        self.message = message
        self.color = color or get_next_color()
        self.color_code = COLORS.get(self.color, COLORS['cyan'])
        self.reset = COLORS['reset']
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame = 0

    def _spin(self):
        """Run spinner in background thread."""
        while not self._stop_event.is_set():
            frame = self.FRAMES[self._frame % len(self.FRAMES)]
            sys.stdout.write(f'\r{self.color_code}{self.message}... {frame}{self.reset}')
            sys.stdout.flush()
            self._frame += 1
            time.sleep(0.1)

    def start(self):
        """Start the spinner."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message: str = None):
        """Stop the spinner and optionally show final message."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        
        # Clear the spinner line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()
        
        if final_message:
            print(f"{self.color_code}{final_message}{self.reset}")


class ProcessBar:
    """Animated process bar for tool execution."""

    FRAMES = ['    ', '=>  ', '===>', '====', '===>', '=>> ']

    def __init__(self, message: str = "Processing", color: str = None):
        self.message = message
        self.color = color or get_next_color()
        self.color_code = COLORS.get(self.color, COLORS['cyan'])
        self.reset = COLORS['reset']
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frame = 0
        self._lock = threading.Lock()

    def _animate(self):
        """Run process bar animation in background thread."""
        while not self._stop_event.is_set():
            with self._lock:
                frame = self.FRAMES[self._frame % len(self.FRAMES)]
            sys.stdout.write(f'\r{self.color_code}{self.message}: [{frame}]{self.reset}')
            sys.stdout.flush()
            self._frame += 1
            time.sleep(0.15)

    def start(self):
        """Start the process bar."""
        self._stop_event.clear()
        self._frame = 0
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self, final_message: str = None):
        """Stop the process bar."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        
        sys.stdout.write('\r' + ' ' * (len(self.message) + 15) + '\r')
        sys.stdout.flush()
        
        if final_message:
            print(f"{self.color_code}{final_message}{self.reset}")


class ProgressBar:
    """Progress bar for multi-step operations."""

    def __init__(self, total: int, message: str = "Progress", color: str = None):
        self.total = total
        self.current = 0
        self.message = message
        self.color = color or get_next_color()
        self.color_code = COLORS.get(self.color, COLORS['cyan'])
        self.reset = COLORS['reset']
        self._lock = threading.Lock()

    def update(self, current: int = None):
        """Update progress."""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        with self._lock:
            self._display()

    def _display(self):
        """Display the progress bar."""
        if self.total == 0:
            percent = 100
        else:
            percent = int((self.current / self.total) * 100)
        
        filled = int(percent / 5)
        bar = '=' * filled + '-' * (20 - filled)
        
        sys.stdout.write(f'\r{self.color_code}{self.message}: [{bar}] {self.current}/{self.total} ({percent}%){self.reset}')
        sys.stdout.flush()

    def finish(self, final_message: str = None):
        """Finish the progress bar."""
        self.current = self.total
        self._display()
        
        sys.stdout.write('\n')
        sys.stdout.flush()
        
        if final_message:
            print(f"{self.color_code}{final_message}{self.reset}")


class MultiToolProgress:
    """Progress tracker for multiple tool executions."""

    def __init__(self, tool_names: list, color: str = None):
        self.tools = tool_names
        self.total = len(tool_names)
        self.current = 0
        self.color = color or get_next_color()
        self.color_code = COLORS.get(self.color, COLORS['cyan'])
        self.reset = COLORS['reset']

    def update(self, tool_name: str = None):
        """Update progress after each tool."""
        self.current += 1
        self._display(tool_name)

    def _display(self, current_tool: str = None):
        """Display multi-tool progress."""
        if current_tool is None:
            current_tool = self.tools[self.current - 1] if self.current > 0 else "..."

        percent = int((self.current / self.total) * 100) if self.total > 0 else 100
        filled = int(percent / 5)
        bar = '=' * filled + '-' * (20 - filled)
        
        sys.stdout.write(f'\r{self.color_code}[{self.current}/{self.total}] [{bar}] {percent}% Running: {current_tool}{self.reset}')
        sys.stdout.flush()

    def finish(self):
        """Finish progress display."""
        sys.stdout.write('\n')
        sys.stdout.flush()


async def spinner_async(coro, message: str = "Thinking"):
    """Wrapper to run coroutine with spinner."""
    spinner = Spinner(message)
    spinner.start()
    try:
        result = await coro
        return result
    finally:
        spinner.stop()


async def process_bar_async(coro, message: str = "Processing"):
    """Wrapper to run coroutine with process bar."""
    bar = ProcessBar(message)
    bar.start()
    try:
        result = await coro
        return result
    finally:
        bar.stop()


def spin_on_thread(coro):
    """Decorator to add spinner to async function."""
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        return await spinner_async(coro(*args, **kwargs))
    return wrapper


def process_on_thread(coro):
    """Decorator to add process bar to async function."""
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        return await process_bar_async(coro(*args, **kwargs))
    return wrapper


if __name__ == "__main__":
    import colorama
    colorama.init()
    
    print("=== Spinner Demo ===")
    s = Spinner("Loading")
    s.start()
    time.sleep(2)
    s.stop("Loaded!")
    
    print("\n=== Process Bar Demo ===")
    p = ProcessBar("Running task")
    p.start()
    time.sleep(2)
    p.stop("Done!")
    
    print("\n=== Progress Bar Demo ===")
    pg = ProgressBar(10, "Uploading")
    for i in range(10):
        pg.update(i + 1)
        time.sleep(0.2)
    pg.finish("Complete!")
    
    print("\n=== Multi-Tool Progress Demo ===")
    mp = MultiToolProgress(["read_file", "git_status", "search"])
    for tool in ["read_file", "git_status", "search"]:
        mp.update(tool)
        time.sleep(0.5)
    mp.finish()
    
    print("\nDone!")