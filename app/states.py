"""FSM states for photoshoot workflow"""
from aiogram.fsm.state import State, StatesGroup

class PhotoshootStates(StatesGroup):
    """States for photoshoot creation workflow"""
    
    # Waiting for product photo upload
    waiting_for_product_photo = State()
    
    # Selecting aspect ratio
    selecting_aspect_ratio = State()
    
    # Selecting style method (analyze/random/saved/custom)
    selecting_styles_method = State()
    
    # Reviewing suggested/generated styles (with option to edit product name)
    reviewing_suggested_styles = State()
    
    # Editing product name
    editing_product_name = State()
    
    # Creating custom style - waiting for product description
    custom_style_product = State()
    
    # Creating custom style - waiting for style description
    custom_style_description = State()
    
    # Creating custom style - waiting for image count
    custom_style_count = State()
    
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

    # Editing aspect ratio
    editing_aspect_ratio = State()
