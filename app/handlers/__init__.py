from . import user, admin, payment, support, style_management, batch_processing, custom_styles

def get_routers():
    # Order matters! batch_processing should be before user to handle albums
    # custom_styles should be before user to handle custom style callbacks first
    return [
        batch_processing.router,
        style_management.router,
        custom_styles.router,
        user.router,
        admin.router,
        payment.router,
        support.router
    ]