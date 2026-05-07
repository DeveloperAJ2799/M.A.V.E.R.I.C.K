"""Maverick CLI Banner with gradient color cycling."""
import sys

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

MAVERICK_ASCII = """███╗   ███╗    █████╗   ██╗   ██╗  ███████╗   ██████╗    ██╗    ██████╗   ██╗  ██╗
████╗ ████║   ██╔══██╗  ██║   ██║  ██╔════╝   ██╔══██╗   ██║   ██╔════╝   ██║ ██╔╝
██╔████╔██║   ███████║  ██║   ██║  █████╗     ██████╔╝   ██║   ██║        █████╔╝ 
██║╚██╔╝██║   ██╔══██║  ╚██╗ ██╔╝  ██╔══╝     ██╔══██╗   ██║   ██║        ██╔═██╗ 
██║ ╚═╝ ██║██╗██║  ██║██╗╚████╔╝██╗███████╗██╗██║  ██║██╗██║██╗╚██████╗██╗██║  ██╗
╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝ ╚═══╝ ╚═╝╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚═╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝"""

COLORS = {
    'white': '\033[97m',
    'cyan': '\033[36m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'magenta': '\033[35m',
    'blue': '\033[34m',
    'light_magenta': '\033[95m',
    'reset': '\033[0m'
}

COLOR_SEQUENCE = ['white']
_color_index = 0


def get_next_color() -> str:
    """Get next color in gradient sequence."""
    global _color_index
    color = COLOR_SEQUENCE[_color_index]
    _color_index = (_color_index + 1) % len(COLOR_SEQUENCE)
    return color


def reset_color_cycle():
    """Reset color cycle to start."""
    global _color_index
    _color_index = 0


def print_banner(color: str = None):
    """Print the Maverick banner with gradient cycling color."""
    if color is None:
        color = get_next_color()
    
    color_code = COLORS.get(color, COLORS['cyan'])
    reset = COLORS['reset']
    
    print(f"{color_code}{MAVERICK_ASCII}{reset}")


def get_banner_text(color: str = None) -> str:
    """Get banner text with gradient color."""
    if color is None:
        color = get_next_color()
    
    color_code = COLORS.get(color, COLORS['cyan'])
    reset = COLORS['reset']
    
    return f"{color_code}{MAVERICK_ASCII}{reset}"


if __name__ == "__main__":
    reset_color_cycle()
    print("=== Maverick Banner Gradient Preview ===\n")
    print("Cycling through colors:\n")
    for _ in range(6):
        print_banner()
        print()
    print("Color cycle complete!")