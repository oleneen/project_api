import asyncio
import boto3
import os
import csv
import io
from datetime import datetime, date
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import HTTPException
import logging
import uuid

from .. import models

logger = logging.getLogger(__name__)

def get_s3_client():
    """Создает клиент для Yandex Object Storage"""
    return boto3.client(
        's3',
        endpoint_url=os.getenv('YC_OBJ_STORAGE_ENDPOINT', 'https://storage.yandexcloud.net'),
        aws_access_key_id=os.getenv('YC_ACCESS_KEY_ID', ''),
        aws_secret_access_key=os.getenv('YC_SECRET_ACCESS_KEY', ''),
        region_name=os.getenv('YC_REGION', 'ru-central1')
    )

# Получает сделки пользователя за месяц в нужном формате
async def get_user_trades_for_month(
    db: AsyncSession, 
    user_id: str, 
    year: int, 
    month: int
) -> List[Dict[str, Any]]:

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    buyer_trades_query = (
        select(
            models.Transaction,
            models.Order.id.label("order_id"),
            models.Order.direction
        )
        .join(
            models.Order,
            models.Order.id == models.Transaction.buy_order_id
        )
        .where(
            and_(
                models.Order.user_id == user_id,
                models.Transaction.timestamp >= start_date,
                models.Transaction.timestamp < end_date
            )
        )
    )
    
    seller_trades_query = (
        select(
            models.Transaction,
            models.Order.id.label("order_id"),
            models.Order.direction
        )
        .join(
            models.Order,
            models.Order.id == models.Transaction.sell_order_id
        )
        .where(
            and_(
                models.Order.user_id == user_id,
                models.Transaction.timestamp >= start_date,
                models.Transaction.timestamp < end_date
            )
        )
    )
    
    buyer_result = await db.execute(buyer_trades_query)
    seller_result = await db.execute(seller_trades_query)
    
    trades = []
    
    for tx, order_id, direction in buyer_result.all():
        trades.append({
            "transaction": tx,
            "order_id": order_id,
            "side": "buy" if direction.value == "BUY" else "sell",
            "is_buyer": True
        })
    
    for tx, order_id, direction in seller_result.all():
        trades.append({
            "transaction": tx,
            "order_id": order_id,
            "side": "sell" if direction.value == "SELL" else "buy",
            "is_buyer": False
        })
    
    trades.sort(key=lambda x: x["transaction"].timestamp)
    
    return trades

# Генерирует CSV отчет со сделками пользователя
async def generate_csv_report(db: AsyncSession, user_id: str, year: int, month: int) -> str:

    trades = await get_user_trades_for_month(db, user_id, year, month)
    
    if not trades:
        raise HTTPException(
            status_code=404, 
            detail=f"Нет сделок за {month:02d}/{year}"
        )
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['trade_id', 'order_id', 'instrument', 'side', 
                     'quantity', 'price', 'total_amount', 'executed_at'])
    
    for i, trade in enumerate(trades, start=1):
        tx = trade["transaction"]
        
        price_decimal = tx.price
        total_amount_decimal = (tx.qty * tx.price)
        
        writer.writerow([
            i,  # trade_id
            trade["order_id"],  # order_id
            tx.ticker,  # instrument
            trade["side"],  # side
            tx.qty,  # quantity
            f"{price_decimal:.2f}",  # price
            f"{total_amount_decimal:.2f}",  # total_amount
            tx.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')  # executed_at
        ])
    
    return output.getvalue()

# Генерирует и загружает отчет, возвращает информацию об отчете
async def upload_report_to_storage(
    db: AsyncSession,
    user_id: str,
    year: int,
    month: int
) -> Dict[str, Any]:

    csv_content = await generate_csv_report(db, user_id, year, month)
    trades = await get_user_trades_for_month(db, user_id, year, month)

    s3 = get_s3_client()
    bucket = os.getenv('YC_OBJ_STORAGE_BUCKET')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"reports/{user_id}/{year}_{month:02d}/report_{timestamp}.csv"

    def sync_upload():
        s3.put_object(
            Bucket=bucket,
            Key=file_name,
            Body=csv_content.encode("utf-8"),
            ContentType="text/csv",
            Metadata={
                "user_id": user_id,
                "year": str(year),
                "month": str(month),
                "trade_count": str(len(trades)),
            }
        )

        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": file_name},
            ExpiresIn=3600
        )

    url = await asyncio.get_event_loop().run_in_executor(None, sync_upload)

    return {
        "file_url": url,
        "file_path": file_name,
        "trade_count": len(trades),
        "status": "completed",
        "generated_at": datetime.utcnow(),
    }