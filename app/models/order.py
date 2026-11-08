from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("dining_tables.id"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True)
    waiter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="open") # open, paid, cancelled
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False) # Giá tại thời điểm gọi
    status = Column(String(20), default="pending") # pending, cooking, done, served, cancelled
    note = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="items")
    options = relationship("OrderItemOption", back_populates="order_item", cascade="all, delete")

class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("menu_item_options.id"), nullable=False)
    extra_price = Column(Numeric(10, 2), nullable=False)

    order_item = relationship("OrderItem", back_populates="options")
