"""
企業登録API
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.models.company import Company, CompanyStore
from backend.models.industry import INDUSTRIES

router = APIRouter()
store = CompanyStore()


class RegisterRequest(BaseModel):
    name: str
    industry: str
    fixed_cost_monthly: int
    staff_count: int
    tax_rate: float = 0.30
    annual_target: int = 0
    target_margin: float = 0.0
    categories: list[dict] = []
    staff: list[dict] = []


def create_register_router() -> APIRouter:

    @router.get("/api/industries")
    async def list_industries():
        """利用可能な業種一覧（フォーム定義付き）"""
        result = []
        for key, ind in INDUSTRIES.items():
            d = {
                "key": ind.key,
                "label": ind.label,
                "icon": ind.icon,
                "description": ind.description,
                "available": ind.available,
                "default_fixed_cost": ind.default_fixed_cost,
                "default_tax_rate": ind.default_tax_rate,
                "default_target_margin": ind.default_target_margin,
                "sample_categories": ind.sample_categories,
            }
            if ind.form_fields:
                d["form_fields"] = [asdict(f) for f in ind.form_fields]
            result.append(d)
        return JSONResponse(result)

    @router.post("/api/companies")
    async def register_company(req: RegisterRequest):
        """企業を登録"""
        if req.industry not in INDUSTRIES:
            return JSONResponse(
                {"error": f"Unknown industry: {req.industry}"},
                status_code=400,
            )
        ind = INDUSTRIES[req.industry]
        if not ind.available:
            return JSONResponse(
                {"error": f"{ind.label}は準備中です"},
                status_code=400,
            )

        company = Company(
            id=CompanyStore.generate_id(),
            name=req.name,
            industry=req.industry,
            fixed_cost_monthly=req.fixed_cost_monthly,
            staff_count=req.staff_count,
            tax_rate=req.tax_rate,
            annual_target=req.annual_target or _calc_annual_target(req),
            target_margin=req.target_margin or ind.default_target_margin,
            categories=req.categories,
            staff=req.staff,
            created_at=datetime.now().isoformat(),
        )
        store.create(company)

        return JSONResponse({
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "message": f"{company.name}を登録しました",
        }, status_code=201)

    @router.get("/api/companies")
    async def list_companies():
        """登録済み企業一覧"""
        companies = store.list_all()
        result = []
        for c in companies:
            ind = INDUSTRIES.get(c.industry)
            result.append({
                "id": c.id,
                "name": c.name,
                "industry": c.industry,
                "industry_label": ind.label if ind else c.industry,
                "industry_icon": ind.icon if ind else "🏢",
                "staff_count": c.staff_count,
                "fixed_cost_monthly": c.fixed_cost_monthly,
                "created_at": c.created_at,
            })
        return JSONResponse(result)

    @router.get("/api/companies/{company_id}")
    async def get_company(company_id: str):
        """企業詳細"""
        company = store.get(company_id)
        if not company:
            return JSONResponse({"error": "Not found"}, status_code=404)
        ind = INDUSTRIES.get(company.industry)
        return JSONResponse({
            **company.to_dict(),
            "industry_label": ind.label if ind else company.industry,
            "industry_icon": ind.icon if ind else "🏢",
        })

    @router.delete("/api/companies/{company_id}")
    async def delete_company(company_id: str):
        if store.delete(company_id):
            return JSONResponse({"message": "Deleted"})
        return JSONResponse({"error": "Not found"}, status_code=404)

    return router


def _calc_annual_target(req: RegisterRequest) -> int:
    """カテゴリデータから年間目標を自動算出"""
    if req.industry == "retail":
        monthly = sum(c.get("monthly_revenue", 0) for c in req.categories)
        return monthly * 12
    elif req.industry == "it":
        return sum(c.get("revenue", 0) for c in req.categories)
    return 0
