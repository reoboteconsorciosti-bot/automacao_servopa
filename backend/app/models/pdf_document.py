from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
)

from app.database import Base


class PdfDocument(Base):
    """PDF de comprovante de lance, salvo diretamente no Postgres (bytea).

    Cada linha corresponde a um PDF gerado com sucesso por `run_automation_for_cota`.
    Ligado (opcionalmente) ao registro de `AutomationHistory` que disparou a execução.
    """

    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    automation_history_id = Column(
        Integer,
        ForeignKey("automation_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    consultant_name = Column(String(255), nullable=False)
    quota = Column(String(64), nullable=True)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False, default="application/pdf")
    size_bytes = Column(Integer, nullable=False, default=0)
    content = Column(LargeBinary, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
