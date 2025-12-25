from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Index, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Balance in PHOTOSHOOTS (not single images)
    # 1 photoshoot = 4 images
    images_remaining: Mapped[int] = mapped_column(Integer, default=2)  # Default from config
    total_images_processed: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # UTM tracking fields
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Yandex Metrika
    metrika_client_id: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True, index=True)

    # Referral program
    referred_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    processed_images: Mapped[List["ProcessedImage"]] = relationship("ProcessedImage", back_populates="user")
    support_tickets: Mapped[List["SupportTicket"]] = relationship("SupportTicket", back_populates="user")
    utm_events: Mapped[List["UTMEvent"]] = relationship("UTMEvent", back_populates="user", cascade="all, delete-orphan")
    style_presets: Mapped[List["StylePreset"]] = relationship("StylePreset", back_populates="user")

    # Referral relationships
    referrer: Mapped[Optional["User"]] = relationship("User", remote_side=[id], foreign_keys=[referred_by_id], back_populates="referrals")
    referrals: Mapped[List["User"]] = relationship("User", foreign_keys=[referred_by_id], back_populates="referrer", cascade="all, delete-orphan")
    referral_rewards: Mapped[List["ReferralReward"]] = relationship("ReferralReward", foreign_keys="[ReferralReward.user_id]", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    photoshoots_count: Mapped[int] = mapped_column(Integer, nullable=False) # Changed from images_count
    price_rub: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="package")

    def __repr__(self):
        return f"<Package(id={self.id}, name={self.name}, photoshoots={self.photoshoots_count}, price={self.price_rub})>"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Performance indices for common order queries
        Index('idx_orders_created', 'created_at'),
        Index('idx_orders_paid', 'paid_at'),
        Index('idx_orders_status_created', 'status', 'created_at'),
        Index('idx_orders_user_status', 'user_id', 'status'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    package_id: Mapped[int] = mapped_column(Integer, ForeignKey("packages.id"))
    invoice_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    package: Mapped["Package"] = relationship("Package", back_populates="orders")
    processed_images: Mapped[List["ProcessedImage"]] = relationship("ProcessedImage", back_populates="order")
    support_tickets: Mapped[List["SupportTicket"]] = relationship("SupportTicket", back_populates="order")
    referral_rewards: Mapped[List["ReferralReward"]] = relationship("ReferralReward", back_populates="order")

    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status}, amount={self.amount})>"


class ProcessedImage(Base):
    __tablename__ = "processed_images"
    __table_args__ = (
        # Performance indices for common queries
        Index('idx_processed_images_created', 'created_at'),
        Index('idx_processed_images_user_created', 'user_id', 'created_at'),
        Index('idx_processed_images_style', 'style_name'),
        Index('idx_processed_images_user_style', 'user_id', 'style_name'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)

    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    original_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    processed_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Style info
    style_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="processed_images")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="processed_images")

    def __repr__(self):
        return f"<ProcessedImage(id={self.id}, user_id={self.user_id}, style={self.style_name})>"


class StylePreset(Base):
    """Saved user style presets"""
    __tablename__ = "style_presets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    style_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="style_presets")

    def __repr__(self):
        return f"<StylePreset(id={self.id}, name={self.name})>"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")
    admin_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="support_tickets")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="support_tickets")
    messages: Mapped[List["SupportMessage"]] = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("support_tickets.id"))
    sender_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UTMEvent(Base):
    __tablename__ = "utm_events"
    __table_args__ = (
        Index('idx_utm_events_user_type', 'user_id', 'event_type'),
        Index('idx_utm_events_created', 'created_at'),
        Index('idx_utm_events_sent', 'sent_to_metrika'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metrika_client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    event_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True, default="RUB")
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sent_to_metrika: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metrika_upload_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="utm_events")


class ReferralReward(Base):
    __tablename__ = "referral_rewards"
    __table_args__ = (
        Index('idx_referral_rewards_user_type', 'user_id', 'reward_type'),
        Index('idx_referral_rewards_created', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    referred_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    reward_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    images_rewarded: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="referral_rewards")
    referred_user: Mapped["User"] = relationship("User", foreign_keys=[referred_user_id])
    order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys=[order_id], back_populates="referral_rewards")