"""SQLAlchemy ORM Models for PyAPI Studio"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, DateTime, Float,
    ForeignKey, JSON, create_engine
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    relationship
)


class Base(DeclarativeBase):
    pass


class Collection(Base):
    """컬렉션 (폴더) 모델"""
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("collections.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    parent: Mapped[Optional["Collection"]] = relationship(
        "Collection", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Collection"]] = relationship(
        "Collection", back_populates="parent"
    )
    requests: Mapped[List["Request"]] = relationship(
        "Request", back_populates="collection", cascade="all, delete-orphan"
    )


class Request(Base):
    """요청 모델"""
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("collections.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(10), default="GET")
    url: Mapped[str] = mapped_column(Text, default="")

    # Body
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_type: Mapped[str] = mapped_column(String(20), default="none")

    # Scripts
    pre_request_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Settings
    timeout: Mapped[float] = mapped_column(Float, default=30.0)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    follow_redirects: Mapped[bool] = mapped_column(Boolean, default=True)

    # Auth
    auth_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auth_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Metadata
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped[Optional["Collection"]] = relationship(
        "Collection", back_populates="requests"
    )
    headers: Mapped[List["Header"]] = relationship(
        "Header", back_populates="request", cascade="all, delete-orphan"
    )
    parameters: Mapped[List["Parameter"]] = relationship(
        "Parameter", back_populates="request", cascade="all, delete-orphan"
    )


class Header(Base):
    """헤더 모델"""
    __tablename__ = "headers"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    request: Mapped["Request"] = relationship("Request", back_populates="headers")


class Parameter(Base):
    """쿼리 파라미터 모델"""
    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    request: Mapped["Request"] = relationship("Request", back_populates="parameters")


class Environment(Base):
    """환경 모델"""
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    variables: Mapped[List["EnvironmentVariable"]] = relationship(
        "EnvironmentVariable", back_populates="environment",
        cascade="all, delete-orphan"
    )


class EnvironmentVariable(Base):
    """환경 변수 모델"""
    __tablename__ = "environment_variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"))
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    environment: Mapped["Environment"] = relationship(
        "Environment", back_populates="variables"
    )


class GlobalVariable(Base):
    """글로벌 변수 모델"""
    __tablename__ = "global_variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True)
    value: Mapped[str] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class History(Base):
    """요청 히스토리 모델"""
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(Text)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    response_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 전체 요청/응답 데이터 (JSON)
    request_data: Mapped[dict] = mapped_column(JSON)
    response_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )


class Settings(Base):
    """애플리케이션 설정"""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
