import sys

def print_intro():
    """Display the welcome screen with ASCII art."""
    # ANSI color codes
    LIGHT_BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Detect if we can use Unicode box-drawing characters
    # Use ASCII fallback for Windows console if UTF-8 isn't available
    try:
        # Test if we can encode Unicode characters
        test_char = '═'
        test_char.encode(sys.stdout.encoding or 'utf-8')
        use_unicode = True
        h_line = '═'
        v_line = '║'
    except (UnicodeEncodeError, AttributeError, TypeError):
        use_unicode = False
        h_line = '='
        v_line = '|'
    
    # Clear screen effect with some spacing
    print("\n" * 2)
    
    # Welcome box with light blue border
    box_width = 50
    welcome_text = "Welcome to Phineas"
    padding = (box_width - len(welcome_text) - 2) // 2
    
    print(f"{LIGHT_BLUE}{h_line * box_width}{RESET}")
    print(f"{LIGHT_BLUE}{v_line}{' ' * padding}{BOLD}{welcome_text}{RESET}{LIGHT_BLUE}{' ' * (box_width - len(welcome_text) - padding - 2)}{v_line}{RESET}")
    print(f"{LIGHT_BLUE}{h_line * box_width}{RESET}")
    print()
    
    # ASCII art for PHINEAS in block letters (financial terminal style)
    phineas_art = f"""{BOLD}{LIGHT_BLUE}
██████╗ ██╗  ██╗██╗███╗   ██╗███████╗ █████╗ ███████╗
██╔══██╗██║  ██║██║████╗  ██║██╔════╝██╔══██╗██╔════╝
██████╔╝███████║██║██╔██╗ ██║█████╗  ███████║███████╗
██╔═══╝ ██╔══██║██║██║╚██╗██║██╔══╝  ██╔══██║╚════██║
██║     ██║  ██║██║██║ ╚████║███████╗██║  ██║███████║
╚═╝     ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚══════╝
{RESET}"""
    print(phineas_art)
    print()
    print("Your AI assistant for financial analysis.")
    print("Ask me any questions. Type 'exit' or 'quit' to end.")
    print()

