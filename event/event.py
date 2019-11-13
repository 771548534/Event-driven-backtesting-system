# -*- coding: utf-8 -*-

# event.py
"""
定义基本事件类
"""

from __future__ import print_function


class Event(object):
    """
    基类，由其他能够在交易过程中触发的专项事件来继承
    """
    pass


class MarketEvent(Event):
    """
    处理接收到的新市场行情
    """

    def __init__(self):
        """
        初始化MarketEvent
        """
        self.type = 'MARKET'


class SignalEvent(Event):
    """
    处理Strategy对象发出的交易信号，由Portfolio对象接收并处理
    """

    def __init__(self, strategy_id, symbol, datetime, signal_type, strength):
        """
        初始化SignalEvent

        Parameters:
        strategy_id - strategy编号， 暂未用上
        symbol - 品种标签，最好采用csv文件名
        datetime - 生成信号时的timestamp
        signal_type - ’LONG’ ， ’SHORT’ ， ‘EXIT’
        strength - 信号强度，在构建portfo时权衡下单量的大小。主要用于配对交易
        """

        self.type = 'SIGNAL'
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.strength = strength


class OrderEvent(Event):
    """
    处理向交易系统发送的订单
    """

    def __init__(self, symbol, order_type, quantity, direction):
        """
        初始化OrderEvent
        Parameters:
        symbol - 品种标签，最好采用csv文件名
        order_type - 市价订单’MKT’或 限价订单’LMT’
        quantity - 非负整数
        direction - ’BUY’ ， ’SELL’
        """

        self.type = 'ORDER'
        self.symbol = symbol
        self.order_type = order_type
        self.quantity = quantity
        self.direction = direction

    def print_order(self):
        """
        输出订单内容
        """

        print("Order: Symbol=%s, Type=%s, Quantity=%s, Direction=%s" % (self.symbol, self.order_type, self.quantity, self.direction))


class FillEvent(Event):
    """
    记录订单成交情况，因此框架为回测框架，所以成交均为虚拟成交。实盘模型应改为捕捉成交反馈记录。
    """

    def __init__(self, timeindex, symbol, exchange, quantity, direction, fill_cost, commission=None):
        """
        初始化FillEvent
        Parameters:
        timeindex - 成交时的时间，暂未使用
        symbol - 品种标签，最好采用csv文件名
        exchange - 交易所，暂未使用
        quantity - 成交量
        direction - 成交方向(’BUY’ ， ’SELL’)
        fill_cost - 成交金额
        commission - 费用
        """
        self.type = 'FILL'
        self.timeindex = timeindex
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_cost = fill_cost
        # 计算手续费
        if commission is None:
            self.commission = self.calculate_ib_commission()
        else:
            self.commission = commission

    def calculate_ib_commission(self):
        """
        仅计算IF和IH交易所手续费。IF、IH为万分之0.23，今平万分之3.45
        """

        # full_cost = 3
        full_cost = 0.000345 * self.quantity

        return full_cost
