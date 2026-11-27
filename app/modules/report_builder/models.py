from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy.sql import func
from app.core.models import Report, ReportType, ReportFormat, ReportStatus

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

FUNDER_DISCLAIMER = "Indicative only, checked November 2026. Banks price at CBR 8.75% + customer-specific premium. SACCO and MFI rates are reducing-balance unless stated. Government funds may charge admin fees. This is not a loan offer or approval. Confirm your written offer, APR, all fees, total cost, and repayment schedule with the provider before signing. EvidLens is not a lender."

class ReportTemplate(SQLModel, table=True):
    __tablename__ = "report_templates"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=150, unique=True)
    report_type: str = Field(max_length=50, unique=True, index=True)
    series: str = Field(default="EvidLens Market Intelligence", max_length=100)
    pages: str = Field(default="10-15", max_length=20)
    audience: str = Field(default="Strategy / Investment teams", max_length=100)
    sections: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    is_premium: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})

class ReportShare(SQLModel, table=True):
    __tablename__ = "report_shares"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id", index=True)
    shared_by_user_id: int = Field(index=True)
    share_type: str = Field(default="link", max_length=50)
    recipient: Optional[str] = Field(default=None, max_length=255)
    access_token: Optional[str] = Field(default=None, max_length=64, unique=True)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})

class Funder(SQLModel, table=True):
    __tablename__ = "funders"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=150, index=True)
    type: str = Field(default="Bank", max_length=50)
    sector: str = Field(default="All Sectors", max_length=100)
    county: str = Field(default="All Counties", max_length=100)
    min_amount: float = Field(default=0)
    max_amount: float = Field(default=0)
    interest_rate: Optional[float] = Field(default=None)
    rate_display: str = Field(default="Confirm with provider", max_length=150)
    rate_min: Optional[float] = Field(default=None)
    rate_max: Optional[float] = Field(default=None)
    rate_type: str = Field(default="indicative", max_length=30)
    rating: float = Field(default=0)
    requirements: Optional[str] = Field(default=None, max_length=1000)
    apply_link: Optional[str] = Field(default=None, max_length=500)
    source_url: Optional[str] = Field(default=None, max_length=500)
    verification_status: str = Field(default="unverified", max_length=30)
    disclaimer: str = Field(default=FUNDER_DISCLAIMER, max_length=1000)
    is_active: bool = Field(default=True)
    last_verified_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "sector": self.sector,
            "county": self.county,
            "min_amount": self.min_amount,
            "max_amount": self.max_amount,
            "rate_display": self.rate_display,
            "rate_min": self.rate_min,
            "rate_max": self.rate_max,
            "rate_type": self.rate_type,
            "rating": self.rating,
            "requirements": self.requirements,
            "apply_link": self.apply_link,
            "verification_status": self.verification_status,
            "disclaimer": self.disclaimer,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
        }

TEMPLATE_SEED = [
    {"name": "Executive Intelligence Brief", "report_type": "EXEC_BRIEF", "series": "EvidLens Business Briefs", "pages": "4-8", "audience": "C-Suite / Board", "is_premium": False, "description": "1-page snapshot, 5 key findings, implications, 90-day + 6-12 month actions, risks.", "sections": [{"key": "snapshot", "title": "1-Page Snapshot"}, {"key": "findings", "title": "5 Key Findings"}, {"key": "implications", "title": "Strategic Implications"}, {"key": "actions", "title": "Recommended Actions"}, {"key": "risks", "title": "Risks to Monitor"}]},
    {"name": "Market Feasibility Report - 12 Engines", "report_type": "MARKET_FEASIBILITY", "series": "EvidLens Market Intelligence", "pages": "10-15", "audience": "Strategy / Investment teams", "is_premium": False, "description": "12-engine feasibility: competitive, pricing, demand, location, consumer, risk, policy, funding, export, knowledge, AI.", "sections": [{"key": "executive_summary", "title": "Executive Summary"}, {"key": "methodology", "title": "Methodology"}, {"key": "findings", "title": "Pricing, Demand, County Comparison"}, {"key": "competitive", "title": "Competitive and Location"}, {"key": "consumer_risk", "title": "Consumer, Risk, Policy, Funding, Export"}, {"key": "recommendations", "title": "Recommendations and 30-Day Action Plan"}, {"key": "annex", "title": "Annex A + B"}]},
    {"name": "Industry Outlook", "report_type": "INDUSTRY_OUTLOOK", "series": "EvidLens Industry Outlook", "pages": "40-120", "audience": "Strategy / Investment teams", "is_premium": True, "description": "Flagship 14-chapter outlook: macro, structure, segments, pricing, margin, forecasts, scenarios.", "sections": [{"key": "executive_summary", "title": "Executive Summary"}, {"key": "macro", "title": "Macro Context"}, {"key": "structure", "title": "Industry Structure and Segments"}, {"key": "findings", "title": "Pricing, Demand, County Comparison"}, {"key": "margin", "title": "Pricing and Margin Analysis"}, {"key": "competitive", "title": "Competitive and Location"}, {"key": "consumer_risk", "title": "Consumer, Risk, Policy, Funding, Export"}, {"key": "forecasts", "title": "Forecasts and Scenarios"}, {"key": "recommendations", "title": "Recommendations"}, {"key": "annex", "title": "Annex A + B"}]},
    {"name": "Sector Pulse", "report_type": "SECTOR_PULSE", "series": "EvidLens Sector Pulse", "pages": "8-15", "audience": "Periodic monitoring", "is_premium": False, "description": "Short periodic pulse: snapshot, what changed, charts, watchlist.", "sections": [{"key": "snapshot", "title": "Sector Pulse Snapshot"}, {"key": "changed", "title": "What Changed"}, {"key": "charts", "title": "Pricing and Demand Charts"}, {"key": "watchlist", "title": "Watchlist"}]},
    {"name": "Consumer Insights Report", "report_type": "CONSUMER_ANALYSIS", "series": "EvidLens Consumer Insights", "pages": "20-40", "audience": "Strategy / Marketing", "is_premium": True, "description": "Segmentation, persona cards, journey map, pulse, pricing sensitivity.", "sections": [{"key": "segmentation", "title": "Consumer Segmentation"}, {"key": "personas", "title": "Persona Cards"}, {"key": "journey", "title": "Customer Journey Map"}, {"key": "pulse", "title": "Consumer Pulse"}, {"key": "pricing", "title": "Pricing Sensitivity"}]},
    {"name": "Product Watch", "report_type": "PRODUCT_WATCH", "series": "EvidLens Product Watch", "pages": "15-25", "audience": "Product teams", "is_premium": True, "description": "Product-focused watch: price, competitor, consumer.", "sections": [{"key": "price", "title": "Price Watch"}, {"key": "competitor", "title": "Competitor Watch"}, {"key": "consumer", "title": "Consumer Watch"}]},
    {"name": "Investor Pitch Deck", "report_type": "INVESTOR_PITCH", "series": "EvidLens Business Briefs", "pages": "10-15", "audience": "C-Suite / Investors", "is_premium": True, "description": "Problem, solution, market evidence, competition, use of funds, risks.", "sections": [{"key": "problem", "title": "Problem"}, {"key": "solution", "title": "Solution"}, {"key": "market", "title": "Market Evidence"}, {"key": "competition", "title": "Competition"}, {"key": "funds", "title": "Use of Funds"}, {"key": "risks", "title": "Risks"}]},
    {"name": "Bank Loan Pack", "report_type": "BUSINESS_PLAN", "series": "EvidLens Business Briefs", "pages": "15-25", "audience": "SME / Bank", "is_premium": True, "description": "Bank-ready pack: description, market evidence, competition, financial plan, licences, repayment.", "sections": [{"key": "description", "title": "Business Description"}, {"key": "market", "title": "Market Evidence"}, {"key": "competition", "title": "Competition"}, {"key": "financial", "title": "Financial Plan"}, {"key": "compliance", "title": "Licences and Compliance"}, {"key": "repayment", "title": "Repayment Plan"}]},
    {"name": "KRA Tax Report", "report_type": "KRA_TAX", "series": "EvidLens Business Briefs", "pages": "8-12", "audience": "Finance / Compliance", "is_premium": True, "description": "KRA obligations checklist + evidence base. Information only, not tax advice.", "sections": [{"key": "checklist", "title": "KRA Obligations Checklist"}, {"key": "evidence", "title": "Evidence Base"}]},
]

FUNDER_SEED = [
    {"name": "Equity Bank - SME Loan", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 50000000, "rate_display": "13-16% p.a. indicative", "rate_min": 13.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.5, "requirements": "ID, Business registration, 6 months statements. Rate is CBR 8.75% + risk premium. Confirm written offer.", "apply_link": "https://equitygroupholdings.com/ke/borrow/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "KCB Bank - Biashara Loan", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 100000, "max_amount": 10000000, "rate_display": "13-17% p.a. indicative", "rate_min": 13.0, "rate_max": 17.0, "rate_type": "indicative_range", "rating": 4.5, "requirements": "ID, KCB account, 6 months M-Pesa / bank statements. Rate is CBR + risk premium.", "apply_link": "https://ke.kcbgroup.com/for-business/borrow", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Co-operative Bank - MSME Loan", "type": "Bank", "sector": "Agriculture, Retail", "county": "All Counties", "min_amount": 50000, "max_amount": 10000000, "rate_display": "12-16% p.a. indicative", "rate_min": 12.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.2, "requirements": "ID, Business registration, 6 months statements. Best for SACCO-linked traders and distributors.", "apply_link": "https://www.co-opbank.co.ke/business-banking/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Stanbic Bank - SME Loan", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 100000, "max_amount": 25000000, "rate_display": "12-14% p.a. indicative - prime borrowers", "rate_min": 12.0, "rate_max": 14.0, "rate_type": "indicative_range", "rating": 4.4, "requirements": "ID, Business registration, clean books, 12 months statements. Lowest average rate, strictest underwriting.", "apply_link": "https://www.stanbicbank.co.ke/kenya/personal", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "NCBA Bank - SME / Stawi Loan", "type": "Bank", "sector": "Retail, Services", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "rate_display": "13-16% p.a. indicative", "rate_min": 13.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.2, "requirements": "ID, Business registration, Lipa na M-Pesa till history or bank statements.", "apply_link": "https://www.ncbagroup.com/ke/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Absa Bank - Biashara / LPO Finance", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 100000, "max_amount": 20000000, "rate_display": "14-16% p.a. indicative", "rate_min": 14.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.1, "requirements": "ID, Business registration, LPO / tender documents for LPO finance, 6 months statements.", "apply_link": "https://www.absabank.co.ke/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Family Bank - Biashara Boost", "type": "Bank", "sector": "Retail, Services", "county": "All Counties", "min_amount": 30000, "max_amount": 2000000, "rate_display": "Check with bank - not verified", "rate_min": None, "rate_max": None, "rate_type": "unverified", "rating": 4.0, "requirements": "ID, Business registration. Confirm rate, fees, and total cost in writing before signing.", "apply_link": "https://familybank.co.ke/", "source_url": "https://familybank.co.ke/", "verification_status": "unverified", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Stima SACCO - Business Loan", "type": "SACCO", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "rate_display": "12% p.a. reducing balance - indicative", "rate_min": 12.0, "rate_max": 12.0, "rate_type": "indicative_range", "rating": 4.3, "requirements": "SACCO membership, 6 months savings, up to 3x savings. Confirm membership and loan multiple.", "apply_link": "https://www.stima-sacco.com/", "source_url": "https://www.sasra.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Unaitas SACCO - Biashara Loan", "type": "SACCO", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "rate_display": "1.2% per month reducing - indicative", "rate_min": 14.4, "rate_max": 14.4, "rate_type": "indicative_range", "rating": 4.2, "requirements": "Open membership, savings, up to 3x savings. Best for entrepreneurs and youth.", "apply_link": "https://www.unaitas.com/", "source_url": "https://www.sasra.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Mwalimu National SACCO - Development Loan", "type": "SACCO", "sector": "Education, All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "rate_display": "12-14.5% p.a. reducing - indicative", "rate_min": 12.0, "rate_max": 14.5, "rate_type": "indicative_range", "rating": 4.3, "requirements": "Membership via TSC, education staff, spouses, children. Up to 4x-5x deposits.", "apply_link": "https://mwalimunational.coop/", "source_url": "https://www.sasra.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Harambee SACCO - Business Loan", "type": "SACCO", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 3000000, "rate_display": "12-13% p.a. reducing - indicative", "rate_min": 12.0, "rate_max": 13.0, "rate_type": "indicative_range", "rating": 4.1, "requirements": "Membership, savings, up to 3x savings. Karibu loan available after 1 month for new members - confirm.", "apply_link": "https://harambeesacco.com/", "source_url": "https://www.sasra.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Faulu Microfinance - Biashara Loan", "type": "MFI", "sector": "All Sectors", "county": "All Counties", "min_amount": 30000, "max_amount": 5000000, "rate_display": "16% p.a. indicative - confirm APR + fees", "rate_min": 16.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.0, "requirements": "ID, Business registration, 6 months statements. For businesses banks reject.", "apply_link": "https://www.faulukenya.com/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "KWFT - Group / Biashara Loan", "type": "MFI", "sector": "All Sectors", "county": "All Counties", "min_amount": 5000, "max_amount": 500000, "rate_display": "16% p.a. indicative - confirm APR + fees", "rate_min": 16.0, "rate_max": 16.0, "rate_type": "indicative_range", "rating": 4.1, "requirements": "ID, group membership. Largest MFI by clients, women and rural focus, all 47 counties.", "apply_link": "https://www.kwftdtm.com/", "source_url": "https://www.centralbank.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Youth Enterprise Development Fund", "type": "Grant / Government", "sector": "Youth-led Businesses", "county": "All Counties", "min_amount": 20000, "max_amount": 5000000, "rate_display": "0% group + 5% fee, other products 8%", "rate_min": 0.0, "rate_max": 8.0, "rate_type": "government_fee", "rating": 4.0, "requirements": "Age 18-35, ID, group or business registration. Group loans 0% + 5% fee. Vuka / Agri-Biz up to 5M at 8% - confirm product.", "apply_link": "https://www.youthfund.go.ke/", "source_url": "https://www.youthfund.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Uwezo Fund", "type": "Grant / Government", "sector": "Women, Youth, PWD Groups", "county": "All Counties", "min_amount": 50000, "max_amount": 500000, "rate_display": "0% + 5% admin fee, first loan 50k-100k", "rate_min": 0.0, "rate_max": 0.0, "rate_type": "government_fee", "rating": 4.0, "requirements": "Registered group, ID, minutes. First loan Wezesha 50k-100k. Repeat Endeleza up to 500k. Apply at constituency, do not pay to apply.", "apply_link": "https://www.uwezofund.go.ke/", "source_url": "https://www.uwezofund.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Women Enterprise Fund - Tuinuke", "type": "Grant / Government", "sector": "Women-led Businesses", "county": "All Counties", "min_amount": 100000, "max_amount": 750000, "rate_display": "0% interest + 6% one-time admin fee", "rate_min": 0.0, "rate_max": 0.0, "rate_type": "government_fee", "rating": 4.2, "requirements": "Registered women group, group bank account. First cycle 100k, rising to 750k by 5th cycle. Apply at constituency office.", "apply_link": "https://www.wef.co.ke/", "source_url": "https://www.wef.co.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Kenya Industrial Estates - SME Loan", "type": "Government Loan", "sector": "Manufacturing, Processing", "county": "All Counties", "min_amount": 100000, "max_amount": 20000000, "rate_display": "Up to 10% p.a. - confirm current limit", "rate_min": 0.0, "rate_max": 10.0, "rate_type": "indicative_range", "rating": 4.0, "requirements": "ID, Business registration, business plan, machinery / working capital purpose. KIE lists 100k-20M on one page and 500k-14M on another - confirm.", "apply_link": "https://www.kie.co.ke/", "source_url": "https://www.kie.co.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Biashara Kenya Fund", "type": "Government Loan", "sector": "Youth, Women, PWD Businesses", "county": "All Counties", "min_amount": 50000, "max_amount": 2500000, "rate_display": "6% retained cost - confirm", "rate_min": 6.0, "rate_max": 6.0, "rate_type": "government_fee", "rating": 3.9, "requirements": "Youth 35% / Women 35% / PWD 10% allocation. Merged YEDF + WEF + Uwezo. Confirm current product at county office.", "apply_link": "https://biasharakenya.go.ke/", "source_url": "https://biasharakenya.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "NYOTA Project", "type": "Grant / Government", "sector": "Youth-led Businesses", "county": "All Counties", "min_amount": 50000, "max_amount": 50000, "rate_display": "Grant - 0% - non-repayable", "rate_min": 0.0, "rate_max": 0.0, "rate_type": "grant", "rating": 4.0, "requirements": "Age 18-29, up to 35 for PWD. Non-repayable youth capital. Windows open periodically - confirm if open.", "apply_link": "https://www.nyota.go.ke/", "source_url": "https://www.nyota.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
    {"name": "Hustler Fund - Business", "type": "Government Loan", "sector": "Micro Businesses", "county": "All Counties", "min_amount": 500, "max_amount": 200000, "rate_display": "8% p.a., Personal 500-50k, SME 10k-200k", "rate_min": 8.0, "rate_max": 8.0, "rate_type": "government_fee", "rating": 3.8, "requirements": "ID, phone, *254#. Personal 500-50k, 14 days. SME tier 10k-200k for registered business. 5% goes to savings.", "apply_link": "https://www.hustlerfund.go.ke/", "source_url": "https://www.hustlerfund.go.ke/", "verification_status": "indicative", "disclaimer": FUNDER_DISCLAIMER},
]

def seed_templates(session):
    for row in TEMPLATE_SEED:
        existing = session.exec(__import__("sqlmodel").select(ReportTemplate).where(ReportTemplate.report_type == row["report_type"])).first()
        if not existing:
            session.add(ReportTemplate(**row))
    session.commit()

def seed_funders(session):
    for row in FUNDER_SEED:
        existing = session.exec(__import__("sqlmodel").select(Funder).where(Funder.name == row["name"])).first()
        if not existing:
            session.add(Funder(**row, last_verified_at=datetime.now(timezone.utc)))
    session.commit()
