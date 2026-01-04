"""Data loader - loads all datasets on startup."""
from app.data.usda_handler import usda_handler
from app.data.dishes_handler import dishes_handler


def load_all_data():
    """Load all datasets."""
    print("Loading USDA data...")
    usda_handler.load_data()
    
    print("Loading dishes data...")
    dishes_handler.load_data()
    
    print("All data loaded successfully!")


def get_usda_handler():
    """Get USDA handler instance."""
    return usda_handler


def get_dishes_handler():
    """Get dishes handler instance."""
    return dishes_handler
