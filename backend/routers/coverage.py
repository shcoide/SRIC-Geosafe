from typing import List
from fastapi import APIRouter, Query
from models.schemas import CoverageRegion, CoverageCheckResult
from services.coverage import build_coverage_list, check_coverage

router = APIRouter()

@router.get("/coverage", response_model=List[CoverageRegion])
def get_coverage():
    return build_coverage_list()

@router.get("/coverage/check", response_model=CoverageCheckResult)
def get_coverage_check(lat: float = Query(...), lon: float = Query(...)):
    return check_coverage(lat, lon)
