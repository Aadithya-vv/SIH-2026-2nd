from fastapi import FastAPI
from app.api.routes import router
from app.market.api import router as market_router
from app.forecasting.api import router as forecast_router
from app.charter.api import router as charter_router

app = FastAPI(title='Freight Intelligence Platform', version='0.4.0',
              description='Prototype vessel, voyage, market, forecasting and charter timing decision support. Demo references and simulated/imported data retain provenance. No live feeds or operational guarantees.')
app.include_router(router)

app.include_router(market_router)

app.include_router(forecast_router)
app.include_router(charter_router)
