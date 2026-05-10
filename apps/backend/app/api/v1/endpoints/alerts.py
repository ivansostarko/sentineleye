"""Alert rule endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import alert_repo, get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.models.alert_rule import AlertRule
from app.models.user import User, UserRole
from app.schemas.alert import AlertRuleCreate, AlertRulePublic, AlertRuleUpdate

router = APIRouter(prefix="/alert-rules", tags=["alerts"])


def _to_public(rule: AlertRule) -> AlertRulePublic:
    return AlertRulePublic.model_validate(rule, from_attributes=True)


@router.get("", response_model=list[AlertRulePublic])
async def list_rules(
    repo: Annotated[..., Depends(alert_repo)],  # type: ignore[valid-type]
    _user: Annotated[User, Depends(get_current_user)],
) -> list[AlertRulePublic]:
    items = await repo.list(limit=200)
    return [_to_public(r) for r in items]


@router.post(
    "",
    response_model=AlertRulePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def create_rule(
    payload: AlertRuleCreate,
    repo: Annotated[..., Depends(alert_repo)],  # type: ignore[valid-type]
) -> AlertRulePublic:
    data = payload.model_dump()
    data["channels"] = [c.value if hasattr(c, "value") else c for c in data["channels"]]
    rule = AlertRule(**data)
    return _to_public(await repo.add(rule))


@router.patch(
    "/{rule_id}",
    response_model=AlertRulePublic,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
)
async def update_rule(
    rule_id: UUID,
    payload: AlertRuleUpdate,
    repo: Annotated[..., Depends(alert_repo)],  # type: ignore[valid-type]
) -> AlertRulePublic:
    rule = await repo.get(rule_id)
    if rule is None:
        raise NotFoundError(f"Alert rule {rule_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "channels" and value is not None:
            value = [c.value if hasattr(c, "value") else c for c in value]
        setattr(rule, field, value)
    await repo.session.flush()
    return _to_public(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_rule(
    rule_id: UUID,
    repo: Annotated[..., Depends(alert_repo)],  # type: ignore[valid-type]
) -> None:
    rule = await repo.get(rule_id)
    if rule is None:
        raise NotFoundError(f"Alert rule {rule_id} not found.")
    await repo.delete(rule)
