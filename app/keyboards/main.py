"""
Main menu keyboard - compatibility wrapper
"""
from app.keyboards.user_kb import get_main_menu

# Alias for compatibility
def get_main_keyboard():
    """Get main keyboard - alias for get_main_menu"""
    return get_main_menu()
