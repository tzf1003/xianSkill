from __future__ import annotations

import uuid

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.schemas import ApiResponse, ProjectCreate, ProjectOut, ProjectUpdate, SKUCreate, SKUOut, SKUUpdate, SkillCreate, SkillOut, SkillUpdate
from app.core.deps import DbSession
from app.domain.models import DeliveryMode, Project, SKU, Skill, SkillType

from .common import router


@router.get("/projects")
async def list_projects(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset))
    projects = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Project))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [ProjectOut.model_validate(project).model_dump(mode="json") for project in projects],
    })


@router.post("/projects")
async def create_project(body: ProjectCreate, db: DbSession) -> ApiResponse:
    existing = (await db.execute(select(Project).where(Project.slug == body.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already exists")
    project = Project(
        name=body.name,
        slug=body.slug,
        description=body.description,
        cover_url=body.cover_url,
        type=body.type,
        options=body.options.model_dump(exclude_none=True) if body.options else None,
        skill_id=body.skill_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.get("/projects/{project_id}")
async def get_project(project_id: uuid.UUID, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.patch("/projects/{project_id}")
async def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "options" and isinstance(value, BaseModel):
            value = value.model_dump(exclude_none=True)
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return ApiResponse(data=ProjectOut.model_validate(project).model_dump(mode="json"))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: uuid.UUID, db: DbSession) -> ApiResponse:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return ApiResponse(data={"deleted": str(project_id)})


@router.get("/skills")
async def list_skills(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    result = await db.execute(select(Skill).order_by(Skill.created_at.desc()).limit(limit).offset(offset))
    skills = result.scalars().all()
    total = (await db.execute(select(func.count()).select_from(Skill))).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [SkillOut.model_validate(skill).model_dump(mode="json") for skill in skills],
    })


@router.post("/skills")
async def create_skill(body: SkillCreate, db: DbSession) -> ApiResponse:
    skill = Skill(
        name=body.name,
        description=body.description,
        type=SkillType(body.type),
        version=body.version,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        prompt_template=body.prompt_template,
        runner_config=body.runner_config,
    )
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: uuid.UUID, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.put("/skills/{skill_id}")
async def update_skill(skill_id: uuid.UUID, body: SkillUpdate, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(skill, key, value)
    await db.commit()
    await db.refresh(skill)
    return ApiResponse(data=SkillOut.model_validate(skill).model_dump(mode="json"))


@router.delete("/skills/{skill_id}")
async def disable_skill(skill_id: uuid.UUID, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.enabled = False
    await db.commit()
    return ApiResponse(data={"id": str(skill_id), "enabled": False})


@router.get("/skus")
async def list_skus(
    db: DbSession,
    skill_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse:
    stmt = select(SKU).order_by(SKU.created_at.desc())
    if skill_id:
        stmt = stmt.where(SKU.skill_id == skill_id)
    if project_id:
        stmt = stmt.where(SKU.project_id == project_id)
    result = await db.execute(stmt.limit(limit).offset(offset))
    skus = result.scalars().all()
    count_stmt = select(func.count()).select_from(SKU)
    if skill_id:
        count_stmt = count_stmt.where(SKU.skill_id == skill_id)
    if project_id:
        count_stmt = count_stmt.where(SKU.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar_one()
    return ApiResponse(data={
        "total": total,
        "items": [SKUOut.model_validate(sku).model_dump(mode="json") for sku in skus],
    })


@router.post("/skus")
async def create_sku(body: SKUCreate, db: DbSession) -> ApiResponse:
    skill = await db.get(Skill, body.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    sku = SKU(
        skill_id=body.skill_id,
        name=body.name,
        price_cents=body.price_cents,
        delivery_mode=DeliveryMode(body.delivery_mode),
        total_uses=body.total_uses,
        human_sla_hours=body.human_sla_hours,
        human_price_cents=body.human_price_cents,
        project_id=body.project_id,
    )
    db.add(sku)
    await db.commit()
    await db.refresh(sku)
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


@router.get("/skus/{sku_id}")
async def get_sku(sku_id: uuid.UUID, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))


@router.put("/skus/{sku_id}")
async def update_sku(sku_id: uuid.UUID, body: SKUUpdate, db: DbSession) -> ApiResponse:
    sku = await db.get(SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    updates = body.model_dump(exclude_none=True)
    if "delivery_mode" in updates:
        updates["delivery_mode"] = DeliveryMode(updates["delivery_mode"])
    for key, value in updates.items():
        setattr(sku, key, value)
    await db.commit()
    await db.refresh(sku)
    return ApiResponse(data=SKUOut.model_validate(sku).model_dump(mode="json"))