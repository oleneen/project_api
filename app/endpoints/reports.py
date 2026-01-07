from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from .. import schemas
from ..database import get_db
from ..dependencies.user import get_authenticated_user
from ..models import User, Report
from ..crud.reports import upload_report_to_storage, get_user_trades_for_month
from sqlalchemy import select

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)

@router.post("/reports", response_model=schemas.ReportInfo)
async def create_monthly_report(
    report_request: schemas.ReportRequest,
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает отчет по сделкам пользователя за указанный месяц.
    
    Отчет содержит следующие поля:
    - trade_id: порядковый номер сделки в отчете
    - order_id: идентификатор ордера
    - instrument: тикер инструмента
    - side: тип операции (buy/sell)
    - quantity: количество
    - price: цена за единицу
    - total_amount: общая сумма
    - executed_at: время исполнения
    """
    trades = await get_user_trades_for_month(
        db,
        str(current_user.id),
        report_request.year,
        report_request.month,
    )

    if not trades:
        raise HTTPException(
            status_code=404,
            detail=f"Нет сделок за {report_request.month:02d}/{report_request.year}",
        )

    report_info = await upload_report_to_storage(
        db,
        str(current_user.id),
        report_request.year,
        report_request.month,
    )

    return schemas.ReportInfo(
        user_id=current_user.id,
        year=report_request.year,
        month=report_request.month,
        file_url=report_info["file_url"],
        trade_count=report_info["trade_count"],
        generated_at=report_info["generated_at"],
        status=report_info["status"],
    )