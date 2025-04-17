from .database import SessionLocal

def match_orders(db: Session):
    # Получаем все активные ордера
    active_orders = db.query(models.Order).filter(
        models.Order.status == "NEW"
    ).all()
    
    # Группируем по тикеру
    orders_by_ticker = {}
    for order in active_orders:
        if order.ticker not in orders_by_ticker:
            orders_by_ticker[order.ticker] = []
        orders_by_ticker[order.ticker].append(order)
    
    # Обрабатываем каждый тикер отдельно
    for ticker, orders in orders_by_ticker.items():
        # Разделяем на покупки и продажи
        buy_orders = [o for o in orders if o.direction == "BUY"]
        sell_orders = [o for o in orders if o.direction == "SELL"]
        
        # Сортируем покупки по убыванию цены (лучшая цена вперед)
        buy_orders.sort(key=lambda x: x.price or float('inf'), reverse=True)
        
        # Сортируем продажи по возрастанию цены (лучшая цена вперед)
        sell_orders.sort(key=lambda x: x.price or 0)
        
        # Процесс сопоставления
        while buy_orders and sell_orders:
            best_buy = buy_orders[0]
            best_sell = sell_orders[0]
            
            # Проверяем возможность исполнения
            if best_buy.price >= best_sell.price:
                # Определяем количество для исполнения
                qty = min(best_buy.qty - best_buy.filled, 
                         best_sell.qty - best_sell.filled)
                
                # Исполняем сделку
                execute_trade(db, best_buy, best_sell, qty, ticker)
                
                # Обновляем ордера
                best_buy.filled += qty
                best_sell.filled += qty
                
                # Проверяем полное исполнение
                if best_buy.filled >= best_buy.qty:
                    best_buy.status = "EXECUTED"
                    buy_orders.pop(0)
                
                if best_sell.filled >= best_sell.qty:
                    best_sell.status = "EXECUTED"
                    sell_orders.pop(0)
            else:
                break
    
    db.commit()