"""FSM states for photoshoot workflow"""
from aiogram.fsm.state import State, StatesGroup

class PhotoshootStates(StatesGroup):
    """States for photoshoot creation workflow"""
    
    # Waiting for product photo upload
    waiting_for_product_photo = State()
    
    # Selecting aspect ratio
    selecting_aspect_ratio = State()
    
    # Selecting style method (analyze/random/saved)
    selecting_styles_method = State()
    
    # Reviewing suggested/generated styles
    reviewing_suggested_styles = State()
    
    # Generating photoshoot (processing)
    generating_photoshoot = State()
    
    # Saving a style preset name
    saving_style_name = State()

class StyleManagementStates(StatesGroup):
    """States for style management"""
    
    # Viewing saved styles list
    viewing_saved_styles = State()
    
    # Editing style name
    editing_style_name = State()
