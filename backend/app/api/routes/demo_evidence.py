"""Lightweight helper route to export synthetic demo CSVs directly."""

import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.evidence_engine import generate_demo_datasets

router = APIRouter()

_VALID_DATASETS = {"clean_pass", "hero_problematic", "corrected_resubmission"}


@router.get("/api/v2/demo/evidence-csv/{dataset_name}", tags=["Evidence V2"])
def download_demo_csv(dataset_name: str):
    """Download a synthetic demo evidence CSV file without authentication."""
    if dataset_name not in _VALID_DATASETS:
        raise HTTPException(
            404,
            detail=f"Unknown dataset '{dataset_name}'. Valid options: {sorted(_VALID_DATASETS)}.",
        )
    datasets = generate_demo_datasets()
    csv_content = datasets[dataset_name]
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=synthetic-{dataset_name}.csv", "X-PilotProof-Demo": "true"},
    )
