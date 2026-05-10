"""Cloud-provider integration credentials.

Stores credentials needed to talk to external clouds (Tuya for now).
Secret fields are Fernet-encrypted at rest — see `app.services.crypto`.
"""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CloudProvider(str, enum.Enum):
    TUYA = "tuya"


class CloudIntegration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cloud_integrations"

    provider: Mapped[CloudProvider] = mapped_column(
        Enum(
            CloudProvider,
            name="cloud_provider",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    access_id_enc: Mapped[str] = mapped_column(Text, nullable=False)
    access_secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
