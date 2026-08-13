from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base


class AutomationHistory(Base):
    __tablename__ = "automation_history"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_name = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    consultant_name = Column(String(255), nullable=False)
    quotas_summary = Column(Text, nullable=True)
    quotas_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="running", nullable=False)
    pdf_filename = Column(String(255), nullable=True)
    pdf_path = Column(String(512), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
