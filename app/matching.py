from . import models
from sqlalchemy import and_
import logging
from .crud import create_transaction

logger = logging.getLogger(__name__)


async def execute_limit_order(db, new_order):
    try:
        if new_order.direction == "BUY":
            opposite_direction = "SELL"
            price_condition = (models.Order.price <= new_order.price)
            order_by = models.Order.price.asc()
        else:
            opposite_direction = "BUY"
            price_condition = (models.Order.price >= new_order.price)
            order_by = models.Order.price.desc()

        opposite_orders = db.query(models.Order).filter(
            and_(
                models.Order.instrument_ticker == new_order.instrument_ticker,
                models.Order.direction == opposite_direction,
                models.Order.status == "NEW",
                models.Order.price.isnot(None),
                price_condition
            )
        ).order_by(order_by).all()

        remaining_qty = new_order.qty - new_order.filled

        for opposite_order in opposite_orders:
            if remaining_qty <= 0:
                break

            available_qty = opposite_order.qty - opposite_order.filled
            executed_qty = min(available_qty, remaining_qty)

            await execute_trade(db, new_order, opposite_order, executed_qty)
            remaining_qty -= executed_qty

        if new_order.filled > 0:
            if new_order.filled >= new_order.qty:
                new_order.status = "FILLED"
            else:
                new_order.status = "PARTIALLY_FILLED"
            db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error executing limit order: {str(e)}")
        raise


async def execute_trade(db, order1, order2, qty):
    try:
        if order1.direction == "BUY":
            buyer_order = order1
            seller_order = order2
        else:
            buyer_order = order2
            seller_order = order1

        execution_price = seller_order.price 
        total_amount = execution_price * qty

        update_balance(db, buyer_order.user_id, buyer_order.instrument_ticker, qty)
        update_balance(db, buyer_order.user_id, "RUB", -total_amount)

        update_balance(db, seller_order.user_id, seller_order.instrument_ticker, -qty)
        update_balance(db, seller_order.user_id, "RUB", total_amount)

        order1.filled += qty
        order2.filled += qty

        if order1.filled >= order1.qty:
            order1.status = "FILLED"
        if order2.filled >= order2.qty:
            order2.status = "FILLED"

        await create_transaction(order1, order2, qty, db)

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Trade execution failed: {str(e)}")
        raise


def update_balance(db, user_id, ticker, amount):
    balance = db.query(models.Balance).filter(
        and_(
            models.Balance.user_id == str(user_id),
            models.Balance.ticker == ticker
        )
    ).first()

    if balance:
        balance.amount += amount
        if balance.amount < 0:
            raise ValueError("Insufficient funds")
    else:
        if amount < 0:
            raise ValueError("Insufficient funds")
        balance = models.Balance(
            user_id=str(user_id),
            ticker=ticker,
            amount=amount
        )
        db.add(balance)
