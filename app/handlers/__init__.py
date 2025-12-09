from . import user, admin, payment, support, style_management, batch_processing

def get_routers():
    # Order matters! batch_processing should be before user to handle albums
    return [
        batch_processing.router,
        style_management.router,
        user.router,
        admin.router,
        payment.router,
        support.router
    ]