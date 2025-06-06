from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Union
from ..database import get_db
from ..models import User, OrderStatus
import logging
from ..schemas import CreateOrderResponse, LimitOrder, MarketOrder, LimitOrderBody, MarketOrderBody, Ok
from ..dependencies.user import get_authenticated_user
from ..crud import get_orders_by_user_id
from ..crud import (
    process_market_order,
    process_limit_order,
    unlock_user_balance
)
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ..crud.orders import get_order_by_id as crud_get_order_by_id

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

@router.post("/order", response_model=CreateOrderResponse)
async def create_order(
    order: Union[LimitOrderBody, MarketOrderBody],
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        if isinstance(order, LimitOrderBody):
            result = await process_limit_order(db, order, str(current_user.id))
        else:
            result = await process_market_order(db, order, str(current_user.id))
            
        return {"success": True, "order_id": str(result.id)}
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/order")
async def get_user_orders(
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    db_orders = await get_orders_by_user_id(db, str(current_user.id))
    out: List[Union[LimitOrder, MarketOrder]] = []
    for order in db_orders:
        if order.price is None:
            out.append(MarketOrder.model_validate(order))
        else:
            out.append(LimitOrder.model_validate(order))
    return out

@router.get("/order/{order_id}")
async def get_order_by_id_endpoint(
    order_id: str,
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        db_order = await crud_get_order_by_id(db, order_id, str(current_user.id))
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")

        if db_order.price is not None:
            order_out = LimitOrder.model_validate(db_order)
        else:
            order_out = MarketOrder.model_validate(db_order)

        return JSONResponse(content=jsonable_encoder(order_out), status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.delete("/order/{order_id}", response_model=Ok)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        try:
            uuid_obj = UUID(order_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Order not found")
        order = await crud_get_order_by_id(db, order_id, str(current_user.id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel order with status {order.status.value}"
            )
        
        if order.type == "LIMIT":
            balance_ticker = "RUB" if order.direction == "BUY" else order.instrument_ticker
            locked_amount = order.price * (order.qty - order.filled) if order.direction == "BUY" else (order.qty - order.filled)
            
            await unlock_user_balance(
                db=db,
                user_id=str(current_user.id),
                ticker=balance_ticker,
                amount=locked_amount
            )
        
        order.status = OrderStatus.CANCELLED
        await db.commit()
        
        return Ok()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling order: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")