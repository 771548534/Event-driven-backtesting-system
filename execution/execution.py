# -*- coding: utf-8 -*-

# execution.py

from __future__ import print_function

from abc import ABCMeta, abstractmethod
import datetime
try:
    import Queue as queue
except ImportError:
    import queue

from event import FillEvent, OrderEvent


class ExecutionHandler(object):
    """
    抽象基类，处理订单生成与订单成交的关系， 可以模拟实盘成交情况
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def execute_order(self, event):
        """
        接收OrderEvent，生成FillEvent
        Parameters:
        event - Contains an Event object with order information.
        """
        raise NotImplementedError("Should implement execute_order()")


class SimulatedExecutionHandler(ExecutionHandler):
    """
    订单自动成交，未考虑延迟、滑点或部分成交
    """
    def __init__(self, events):
        """
        初始化
        Parameters:
        events - queue.Queue()
        """
        self.events = events

    def execute_order(self, event):
        """
        简易成交
        Parameters:
        event - Contains an Event object with order information.
        """
        if event.type == 'ORDER':
            fill_event = FillEvent(datetime.datetime.utcnow(), event.symbol, '某交易所', event.quantity,
                                   event.direction, None, commission=1.5)
            self.events.put(fill_event)


if __name__ == '__main__':
    order_event = OrderEvent(direction='BUY', symbol='A2001_2019-11-05', order_type='MKT', quantity=10)
    execution_handler = SimulatedExecutionHandler(events=queue.Queue())
    execution_handler.execute_order(order_event)
    print(execution_handler.events.qsize())