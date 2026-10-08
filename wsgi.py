from app import create_app, db
from app.models.models import (
    User,
    Table,
    Category,
    MenuItem,
    Order,
    OrderItem,
    OrderStatusHistory,
    Notification
)

app = create_app()

with app.app_context():
    db.create_all()
    print("DATABASE TABLES CREATED SUCCESSFULLY")
