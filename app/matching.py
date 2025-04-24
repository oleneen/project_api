from .database import SessionLocal
from . import models
from sqlalchemy import and_, or_

def match_orders(db):

    buy_orders = db.query(models.Order).filter(
        and_(
            models.Order.status == "NEW",
            models.Order.direction == "BUY",
            models.Order.price.isnot(None)
        )
    ).order_by(models.Order.price.desc(), models.Order.created_at).all()

    sell_orders = db.query(models.Order).filter(
        and_(
            models.Order.status == "NEW",
            models.Order.direction == "SELL",
            models.Order.price.isnot(None)
        )
    ).order_by(models.Order.price.asc(), models.Order.created_at).all()

    for buy_order in buy_orders:
        for sell_order in sell_orders:

            if (buy_order.ticker == sell_order.ticker and 
                buy_order.price >= sell_order.price):

                qty = min(buy_order.qty - buy_order.filled,
                          sell_order.qty - sell_order.filled)

                if qty <= 0:
                    continue

                buyer_balance = db.query(models.Balance).filter(
                    and_(
                        models.Balance.user_id == buy_order.user_id,
                        models.Balance.ticker == "РУБ"
                    )
                ).first()

                seller_balance = db.query(models.Balance).filter(
                    and_(
                        models.Balance.user_id == sell_order.user_id,
                        models.Balance.ticker == sell_order.ticker
                    )
                ).first()

                # ???? по сути перед созданием ордера мы проверяем баланс, но будем ли замораживать?? или оставим проверку тут
                if not buyer_balance or buyer_balance.amount < buy_order.price * qty:
                    continue

                if not seller_balance or seller_balance.amount < qty:
                    continue

                try:

                    buyer_balance.amount -= buy_order.price * qty
                    
                    seller_money_balance = db.query(models.Balance).filter(
                        and_(
                            models.Balance.user_id == sell_order.user_id,
                            models.Balance.ticker == "РУБ"
                        )
                    ).first()
                    
                    if not seller_money_balance:
                        seller_money_balance = models.Balance(
                            user_id=sell_order.user_id,
                            ticker="РУБ",
                            amount=0
                        )
                        db.add(seller_money_balance)
                    
                    seller_money_balance.amount += buy_order.price * qty
                    seller_balance.amount -= qty
                    
                    buyer_asset_balance = db.query(models.Balance).filter(
                        and_(
                            models.Balance.user_id == buy_order.user_id,
                            models.Balance.ticker == buy_order.ticker
                        )
                    ).first()
                    
                    if not buyer_asset_balance:
                        buyer_asset_balance = models.Balance(
                            user_id=buy_order.user_id,
                            ticker=buy_order.ticker,
                            amount=0
                        )
                        db.add(buyer_asset_balance)
                    
                    buyer_asset_balance.amount += qty

                    buy_order.filled += qty
                    sell_order.filled += qty

                    if buy_order.filled >= buy_order.qty:
                        buy_order.status = "EXECUTED"
                    
                    if sell_order.filled >= sell_order.qty:
                        sell_order.status = "EXECUTED"

                    db.commit()

                except Exception as e:
                    db.rollback()
                    raise e

    db.query(models.Order).filter(
        models.Order.filled >= models.Order.qty,
        models.Order.status == "NEW"
    ).update({"status": "EXECUTED"})
    
    db.commit()

def process_market_orders(db):

    market_orders = db.query(models.Order).filter(
        and_(
            models.Order.status == "NEW",
            models.Order.price.is_(None)
        )
    ).all()

    for order in market_orders:
        if order.direction == "BUY":

            best_offer = db.query(models.Order).filter(
                and_(
                    models.Order.ticker == order.ticker,
                    models.Order.direction == "SELL",
                    models.Order.status == "NEW",
                    models.Order.price.isnot(None)
            ).order_by(models.Order.price.asc()).first())
            
            if best_offer:
                order.price = best_offer.price 
        else: 
            best_bid = db.query(models.Order).filter(
                and_(
                    models.Order.ticker == order.ticker,
                    models.Order.direction == "BUY",
                    models.Order.status == "NEW",
                    models.Order.price.isnot(None)
            ).order_by(models.Order.price.desc()).first())
            
            if best_bid:
                order.price = best_bid.price