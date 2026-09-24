from fastapi import FastAPI
from app.api.routes import router
from app.market.api import router as market_router
from app.forecasting.api import router as forecast_router

app = FastAPI(title='Freight Intelligence Platform', version='0.3.0',
              description='Batch 1 decision support and Batch 2 market data foundation. Costs use demo references; market histories are SIMULATED or USER_IMPORT. No live feeds; forecasts retain source labels and do not make charter decisions.')
app.include_router(router)

app.include_router(market_router)

app.include_router(forecast_router)
