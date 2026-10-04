from fastapi import APIRouter

router = APIRouter(tags=['health'])


@router.get('')
def healthcheck() -> dict[str, str]:
    return {'status': 'ok', 'service': 'pilotproof-backend'}
