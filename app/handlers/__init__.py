from . import user, admin, payment, support, style_management

def get_routers():
    return [
        user.router,
        style_management.router,
        admin.router,
        payment.router,
        support.router
    ]
