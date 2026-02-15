"""Health, metrics, and metrics dashboard endpoints."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from backend.services.monitoring_service import get_health, get_metrics

router = APIRouter(tags=["monitoring"])


@router.get("/health", summary="Health check")
def health():
    """
    Health check for load balancers and orchestration.
    Returns database and LLM config status. Does not require authentication.
    """
    return get_health()


@router.get("/metrics", summary="Prometheus-style metrics")
def metrics():
    """
    Aggregate metrics: guidelines processed, trees compiled, LLM calls/cost, test pass rate.
    Suitable for scraping or dashboard. Phase 1: JSON; can add text/plain for Prometheus later.
    """
    return get_metrics()


@router.get("/metrics/dashboard", response_class=HTMLResponse, summary="Metrics dashboard (HTML)")
def metrics_dashboard():
    """Simple HTML dashboard showing key metrics. Refresh to update."""
    data = get_metrics()
    health_data = get_health()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CAIRE Metrics</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f5f5f5; }}
    h1 {{ color: #1e293b; }}
    .card {{ background: white; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
    .metric {{ font-size: 1.5rem; font-weight: 600; color: #0f172a; }}
    .label {{ font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }}
    .status {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; }}
    .status.up {{ background: #dcfce7; color: #166534; }}
    .status.down {{ background: #fee2e2; color: #991b1b; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <h1>CAIRE Metrics Dashboard</h1>
  <div class="card">
    <strong>Health</strong>
    <p><span class="status {'up' if health_data.get('checks', {}).get('database', {}).get('status') == 'up' else 'down'}">DB: {health_data.get('checks', {}).get('database', {}).get('message', 'unknown')}</span>
       <span class="status {'up' if health_data.get('checks', {}).get('llm_config', {}).get('status') == 'configured' else 'down'}">LLM: {health_data.get('checks', {}).get('llm_config', {}).get('message', 'unknown')}</span></p>
  </div>
  <div class="card">
    <div class="metric">{data.get('guidelines_processed', 0)}</div>
    <div class="label">Guidelines processed</div>
  </div>
  <div class="card">
    <div class="metric">{data.get('trees_compiled', 0)}</div>
    <div class="label">Trees compiled</div>
  </div>
  <div class="card">
    <div class="metric">{data.get('compilations_completed', 0)}</div>
    <div class="label">Compilations completed</div>
  </div>
  <div class="card">
    <div class="metric">{data.get('compilations_failed', 0)}</div>
    <div class="label">Compilations failed</div>
  </div>
  <div class="card">
    <div class="metric">${data.get('llm_estimated_cost_usd', 0):.4f}</div>
    <div class="label">LLM estimated cost (USD)</div>
  </div>
  <div class="card">
    <div class="metric">{data.get('llm_api_calls', 0)}</div>
    <div class="label">LLM API calls</div>
  </div>
  <div class="card">
    <div class="metric">{data.get('test_pass_rate_percent') is not None and str(data.get('test_pass_rate_percent')) + '%' or 'N/A'}</div>
    <div class="label">Test pass rate (from recent runs)</div>
  </div>
  <p><a href="/api/metrics">JSON metrics</a> | <a href="/docs">API docs</a></p>
</body>
</html>"""
    return HTMLResponse(html)
