"""
ダッシュボードAPI
"""
from __future__ import annotations
from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()


def create_dashboard_router(templates: dict) -> APIRouter:
    """ダッシュボードルーターを生成（複数テンプレート対応）"""

    def get_template(template_key: str):
        return templates.get(template_key, templates["it_company"])

    @router.get("/api/dashboard/summary")
    async def get_summary(
        month: int = Query(default=0, ge=0, le=11),
        template: str = Query(default="it_company"),
    ):
        tmpl = get_template(template)
        summary = tmpl.summary(month)
        views = summary["three_views"]
        return JSONResponse({
            "future": asdict(views.future),
            "now": asdict(views.now),
            "cash": asdict(views.cash),
            "gap": summary["gap"],
            "achievement_rate": round(summary["achievement_rate"] * 100, 1),
            "total_revenue": summary["total_revenue"],
            "total_cost": summary["total_cost"],
            "gross_profit": summary["total_gross_profit"],
            "gross_margin": round(summary["gross_margin"] * 100, 1),
            "month": summary["month_label"],
            "company_name": tmpl.config.name,
            "fixed_cost_monthly": tmpl.config.fixed_cost_monthly,
            "tax_rate": tmpl.config.tax_rate,
            "annual_target": tmpl.config.annual_target,
        })

    @router.get("/api/dashboard/projects")
    async def get_projects(
        month: int = Query(default=0, ge=0, le=11),
        template: str = Query(default="it_company"),
    ):
        tmpl = get_template(template)
        engine = tmpl.profit_engine
        projects = []
        for p in tmpl.projects:
            labor = engine.labor_cost(p)
            gross = p.revenue - p.cost - labor
            margin = round((gross / p.revenue) * 100) if p.revenue else 0
            status = engine.project_status(p, month)
            prog = min(100, p.progress + month * 5) if month >= p.contract_month else 0
            projects.append({
                "id": p.id,
                "name": p.name,
                "full_name": p.full_name,
                "project_name": p.project_name,
                "revenue": p.revenue,
                "cost": p.cost,
                "labor_cost": labor,
                "gross_profit": gross,
                "margin": margin,
                "status": status,
                "progress": prog,
                "contact": p.contact,
                "contract_month": p.contract_month,
                "invoice_month": p.invoice_month,
                "payment_month": p.payment_month,
                "staff": [
                    {"name": s.name, "hours": s.hours, "rate": s.hourly_rate}
                    for s in p.staff
                ],
            })
        return JSONResponse(projects)

    @router.get("/api/dashboard/staff")
    async def get_staff_report(
        month: int = Query(default=0, ge=0, le=11),
        template: str = Query(default="it_company"),
    ):
        tmpl = get_template(template)
        report = tmpl.staff_report(month)
        return JSONResponse(report)

    @router.get("/api/dashboard/cashflow")
    async def get_cash_flows(template: str = Query(default="it_company")):
        tmpl = get_template(template)
        flows = tmpl.cash_flows()
        return JSONResponse([asdict(f) for f in flows])

    @router.get("/api/dashboard/templates")
    async def list_templates():
        """利用可能なテンプレート一覧"""
        return JSONResponse([
            {"key": k, "label": t.label, "company_name": t.config.name}
            for k, t in templates.items()
        ])

    return router
