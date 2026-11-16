from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from app.services.standings import standings_cache,StandingsUnavailable

router=APIRouter(prefix="/standings",tags=["standings"])

def cache_dependency():return standings_cache

@router.get("/{league}")
def league_standings(league:Literal["NFL","MLB","EPL"],cache=Depends(cache_dependency)):
    try:return cache.get(league)
    except StandingsUnavailable as exc:raise HTTPException(503,str(exc)) from None
