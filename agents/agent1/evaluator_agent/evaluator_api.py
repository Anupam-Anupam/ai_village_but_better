import json
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from adapters.mongo_adapter import MongoAdapter
from adapters.postgres_adapter import PostgresAdapter
from modules.data_collector import DataCollector
from modules.scoring_engine import ScoringEngine
from modules.llm_interface import LLMInterface
from modules.scheduler import EvaluatorScheduler
from modules.report_builder import ReportBuilder
from modules.visualization import build_performance_figure, figure_to_png_bytes
from fastapi.responses import Response


# Simple structured logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("evaluator_agent")


class Health(BaseModel):
    status: str


def create_app() -> FastAPI:
    app = FastAPI(title="Evaluator Agent API", version="1.0.0")

    mongo = MongoAdapter(logger=logger)
    pg = PostgresAdapter(logger=logger)

    collector = DataCollector(mongo=mongo, pg=pg, logger=logger)
    scorer = ScoringEngine(logger=logger)
    llm = LLMInterface(logger=logger)
    builder = ReportBuilder(logger=logger)
    scheduler = EvaluatorScheduler(collector, scorer, llm, builder, logger=logger)

    # Kick off periodic evaluations
    scheduler.start()

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health(status="ok")

    @app.get("/task/{task_id}")
    def get_task(task_id: str):
        report = scheduler.get_task_report(task_id)
        if not report:
            # Try on-demand evaluation for this task (best-effort)
            try:
                data = collector.collect_for_task(agent_id=os.getenv("DEFAULT_AGENT_ID"), task_id=task_id)
                pack = scorer.score_task(data)
                summary = llm.summarize({**data, **pack})
                report = builder.build_report(data, pack, summary)
                return report
            except Exception:
                pass
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    @app.get("/agent/{agent_id}")
    def get_agent(agent_id: str):
        reports = scheduler.get_agent_reports(agent_id)
        if not reports:
            raise HTTPException(status_code=404, detail="No reports for agent")
        return reports

    @app.get("/reports")
    def get_reports():
        return scheduler.get_all_reports()

    @app.get("/agent/{agent_id}/performance.png")
    def agent_performance_png(agent_id: str):
        try:
            reports = scheduler.get_agent_reports(agent_id)
            if not reports:
                raise HTTPException(status_code=404, detail="No reports for agent")
            fig = build_performance_figure(reports)
            png = figure_to_png_bytes(fig)
            return Response(content=png, media_type="image/png")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(json.dumps({"event": "plot_render_error", "scope": "agent", "agent_id": agent_id, "error": str(e)}))
            return Response(content=f"plot render error: {e}", media_type="text/plain", status_code=503)

    @app.get("/task/{task_id}/performance.png")
    def task_performance_png(task_id: str):
        try:
            # Build per-progress snapshots to ensure a point for each update
            snapshots = collector.collect_snapshots_for_task(agent_id=os.getenv("DEFAULT_AGENT_ID"), task_id=task_id)
            reports = []
            for snap in snapshots:
                pack = scorer.score_task(snap)
                summary = llm.summarize({**snap, **pack})
                rep = builder.build_report(snap, pack, summary)
                # carry forward snapshot collected_at as evaluated_at for plotting continuity
                if "collected_at" in snap:
                    rep["evaluated_at"] = snap["collected_at"]
                reports.append(rep)
            fig = build_performance_figure(reports)
            png = figure_to_png_bytes(fig)
            return Response(content=png, media_type="image/png")
        except Exception as e:
            logger.error(json.dumps({"event": "plot_render_error", "scope": "task", "task_id": task_id, "error": str(e)}))
            return Response(content=f"plot render error: {e}", media_type="text/plain", status_code=503)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
