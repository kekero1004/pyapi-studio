"""Database Manager for PyAPI Studio"""

from pathlib import Path
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from .models import Base


class DatabaseManager:
    """데이터베이스 관리자"""

    _instance: Optional['DatabaseManager'] = None

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # 기본 경로: 사용자 홈 디렉토리
            db_path = Path.home() / ".pyapi-studio" / "data.db"
        
        self._db_path = db_path
        self._engine = None
        self._session_factory = None

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> 'DatabaseManager':
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = cls(db_path)
            cls._instance.initialize()
        return cls._instance

    def initialize(self) -> None:
        """데이터베이스 초기화"""
        # 디렉토리 생성
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # 엔진 생성
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            echo=False,
            future=True
        )

        # WAL 모드 활성화 (성능 향상)
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        # 테이블 생성
        Base.metadata.create_all(self._engine)

        # 세션 팩토리
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False
        )

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """세션 컨텍스트 매니저"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """새 세션 반환 (수동 관리)"""
        return self._session_factory()

    def close(self) -> None:
        """연결 종료"""
        if self._engine:
            self._engine.dispose()
