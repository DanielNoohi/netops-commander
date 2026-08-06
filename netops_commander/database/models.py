"""
SQLAlchemy models for NetOps Commander.
Tables: devices, scan_history, monitor_results, alerts, settings, notes, notes_tags
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(20), index=True, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_ports: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON serialized list
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False)
    monitor_interval: Mapped[int] = mapped_column(Integer, default=60)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    scan_history: Mapped[list["ScanHistory"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    monitor_results: Mapped[list["MonitorResult"]] = relationship(back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_devices_ip_mac", "ip_address", "mac_address"),
    )

    def __repr__(self):
        return f"<Device(id={self.id}, ip='{self.ip_address}', mac='{self.mac_address}', online={self.online})>"


class ScanHistory(Base):
    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    scan_type: Mapped[str] = mapped_column(String(50))  # ping, arp, tcp, nmap, snmp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ports_found: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="scan_history")

    def __repr__(self):
        return f"<ScanHistory(id={self.id}, device_id={self.device_id}, type='{self.scan_type}', online={self.online})>"


class MonitorResult(Base):
    __tablename__ = "monitor_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    packet_loss_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="monitor_results")

    def __repr__(self):
        return f"<MonitorResult(id={self.id}, device_id={self.device_id}, online={self.online}, latency={self.latency_ms})>"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), index=True, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info, warning, critical
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    device_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    def __repr__(self):
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50]}...')>"
