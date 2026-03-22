import os
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from agents.graph import run_pipeline
from db.database import get_recent_runs, init_db, save_run


load_dotenv()

app = FastAPI(title="IndustryIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.on_event("startup")
def log_registered_routes():
    print("\nRegistered routes:")
    for route in sorted(app.routes, key=lambda item: item.path):
        methods = ",".join(sorted(getattr(route, "methods", []) or []))
        print(f"  {methods:<20} {route.path}")
    print("")


class AnalyzeRequest(BaseModel):
    industry: str = "Hotels"
    brand: str = "Marriott"
    headlines: list[str] = []


class AnalyzeResponse(BaseModel):
    industry: str
    brand: str
    sentiment_count: int
    avg_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    anomaly_count: int
    anomalies: list[dict]
    forecast_30d: float | None
    forecast_60d: float | None
    forecast_90d: float | None
    forecast_label: str
    competitor_delta: list[dict]
    insight_report: str
    top_headlines: list[dict]


class HistoryRun(BaseModel):
    id: int
    timestamp: str
    industry: str
    brand: str
    avg_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    anomaly_count: int
    forecast_30d: float | None
    insight_report: str


class ExportPdfRequest(BaseModel):
    industry: str
    brand: str
    avg_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    anomaly_count: int
    forecast_30d: float | None
    forecast_60d: float | None
    forecast_90d: float | None
    competitor_delta: list[dict]
    anomalies: list[dict]
    insight_report: str
    top_headlines: list[dict]


def _fmt_pdf_metric(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def build_pdf_report(payload: ExportPdfRequest) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    header = "IndustryIQ — Brand Intelligence Report"
    story.append(Paragraph(header, styles["Title"]))
    story.append(
        Paragraph(
            f"Generated on {datetime.now().strftime('%b %d, %Y %I:%M %p')} for {payload.industry} / {payload.brand}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Sentiment Summary", styles["Heading2"]))
    sentiment_table = Table(
        [
            ["Average Score", "Bullish", "Bearish", "Neutral", "Anomalies"],
            [
                _fmt_pdf_metric(payload.avg_score, 3),
                str(payload.bullish_count),
                str(payload.bearish_count),
                str(payload.neutral_count),
                str(payload.anomaly_count),
            ],
        ],
        hAlign="LEFT",
    )
    sentiment_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6d3d1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fafaf9")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(sentiment_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Forecast", styles["Heading2"]))
    forecast_table = Table(
        [
            ["30 Days", "60 Days", "90 Days"],
            [
                _fmt_pdf_metric(payload.forecast_30d, 1),
                _fmt_pdf_metric(payload.forecast_60d, 1),
                _fmt_pdf_metric(payload.forecast_90d, 1),
            ],
        ],
        hAlign="LEFT",
    )
    forecast_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6d3d1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fafaf9")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(forecast_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Competitor Ranking", styles["Heading2"]))
    competitor_rows = [["Brand", "Score", "Label", "Rank"]]
    for item in payload.competitor_delta:
        competitor_rows.append([
            str(item.get("brand", "")),
            _fmt_pdf_metric(item.get("score"), 3) if isinstance(item.get("score"), (int, float)) else "N/A",
            str(item.get("label", "")),
            str(item.get("rank", "")),
        ])
    competitor_table = Table(competitor_rows, hAlign="LEFT")
    competitor_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6d3d1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fafaf9")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(competitor_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Anomalies", styles["Heading2"]))
    if payload.anomalies:
        for anomaly in payload.anomalies:
            text = (
                f"- z={anomaly.get('z_score', 'N/A')} | "
                f"{anomaly.get('direction', 'unknown')} | "
                f"{anomaly.get('text', '')}"
            )
            story.append(Paragraph(text, styles["Normal"]))
    else:
        story.append(Paragraph("No anomalies detected.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("GPT-4 Executive Brief", styles["Heading2"]))
    story.append(Paragraph(payload.insight_report.replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Top Headlines", styles["Heading2"]))
    for item in payload.top_headlines[:5]:
        text = (
            f"- [{item.get('label', '').upper()}] "
            f"{_fmt_pdf_metric(item.get('score'), 2) if isinstance(item.get('score'), (int, float)) else 'N/A'} "
            f"{item.get('text', '')}"
        )
        story.append(Paragraph(text, styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        result = run_pipeline(
            industry=req.industry,
            brand=req.brand,
            headlines=req.headlines or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    scores = result["sentiment_scores"]
    forecast = result["forecast"]

    avg_score = round(sum(s["score"] for s in scores) / len(scores), 4) if scores else 0.0

    fc = forecast[0] if forecast and isinstance(forecast[0], dict) else {}
    day_30 = fc.get("day_30", {}) if isinstance(fc, dict) else {}
    day_60 = fc.get("day_60", {}) if isinstance(fc, dict) else {}
    day_90 = fc.get("day_90", {}) if isinstance(fc, dict) else {}

    bullish_count = sum(1 for s in scores if s["label"] == "bullish")
    bearish_count = sum(1 for s in scores if s["label"] == "bearish")
    neutral_count = sum(1 for s in scores if s["label"] == "neutral")
    anomaly_count = len(result["anomalies"])
    forecast_30d = day_30.get("forecast") if isinstance(day_30, dict) else None

    save_run(
        industry=result["industry"],
        brand=result["brand"],
        avg_score=avg_score,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
        anomaly_count=anomaly_count,
        forecast_30d=forecast_30d,
        insight_report=result["insight_report"],
    )

    top_headlines = []
    for item in scores[:10]:
        top_headlines.append({
            **item,
            "confidence": item.get("confidence", 0.0),
        })

    return AnalyzeResponse(
        industry=result["industry"],
        brand=result["brand"],
        sentiment_count=len(scores),
        avg_score=avg_score,
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        neutral_count=neutral_count,
        anomaly_count=anomaly_count,
        anomalies=result["anomalies"][:5],
        forecast_30d=forecast_30d,
        forecast_60d=day_60.get("forecast") if isinstance(day_60, dict) else None,
        forecast_90d=day_90.get("forecast") if isinstance(day_90, dict) else None,
        forecast_label=fc.get("label", "") if isinstance(fc, dict) else "",
        competitor_delta=result["competitor_delta"],
        insight_report=result["insight_report"],
        top_headlines=top_headlines,
    )


@app.get("/history", response_model=list[HistoryRun])
def history(
    limit: int = Query(default=10, ge=1, le=50),
    brand: str | None = None,
    industry: str | None = None,
):
    return get_recent_runs(limit=limit, brand=brand, industry=industry)


@app.post("/export-pdf")
async def export_pdf(data: dict):
    payload = ExportPdfRequest.model_validate(data)
    pdf_buffer = build_pdf_report(payload)
    headers = {"Content-Disposition": 'attachment; filename="report.pdf"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)


@app.get("/health")
def health():
    return {"status": "ok", "message": "IndustryIQ API is running"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
