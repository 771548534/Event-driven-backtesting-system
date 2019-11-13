# -*- coding: utf-8 -*-

# backtest.py

from __future__ import print_function

import datetime
import pprint
try:
    import Queue as queue
except ImportError:
    import queue
import time


class Backtest(object):
    """
    事件驱动回测系统
    """
    def __init__(self, csv_dir, symbol_list, initial_capital, heartbeat, start_date, data_handler, execution_handler,
                 portfolio, strategy):
        """
        初始化
        Parameters:
        csv_dir - csv文件所在文件夹的路径
        symbol_list - 品种标签列表，采用csv文件名
        intial_capital - 初始资金
        heartbeat - 停顿，/秒
        start_date - 开始时间
        data_handler - (Class) DataHandler，数据接收
        execution_handler - (Class) ExecutionHandler， 处理订单成交
        portfolio - (Class) Portfolio，更新头寸和市值
        strategy - (Class) Strategy，根据接收到的数据，生成信号
        """
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        self.initial_capital = initial_capital
        self.heartbeat = heartbeat
        self.start_date = start_date
        self.data_handler_cls = data_handler
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.strategy_cls = strategy
        self.events = queue.Queue()
        self.signals = 0
        self.orders = 0
        self.fills = 0
        self.num_strats = 1
        self._generate_trading_instances()

    def _generate_trading_instances(self):
        """
        生成回测中的各类实例对象
        """

        print("Creating DataHandler, Strategy, Portfolio and ExecutionHandler")
        self.data_handler = self.data_handler_cls(self.events, self.csv_dir, self.symbol_list)
        self.strategy = self.strategy_cls(self.data_handler, self.events)
        self.portfolio = self.portfolio_cls(self.data_handler, self.events, self.start_date, self.initial_capital)
        self.execution_handler = self.execution_handler_cls(self.events)

    def _run_backtest(self):
        """
        执行回测
        """

        i = 0
        while True:
            i += 1
            print(i)
            # 接收数据
            if self.data_handler.continue_backtest == True:
                self.data_handler.update_bars()
            else:
                break
            # 处理事件Events
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break
                else:
                    if event is not None:
                        if event.type == 'MARKET':
                            self.strategy.calculate_signals(event)
                            self.portfolio.update_timeindex(event)
                        elif event.type == 'SIGNAL':
                            self.signals += 1
                            self.portfolio.update_signal(event)
                        elif event.type == 'ORDER':
                            self.orders += 1
                            self.execution_handler.execute_order(event)
                        elif event.type == 'FILL':
                            self.fills += 1
                            self.portfolio.update_fill(event)
            time.sleep(self.heartbeat)

    def _output_performance(self):
        """
        输出回测情况
        """

        self.portfolio.create_equity_curve_dataframe()

        print("Creating summary stats...")
        stats = self.portfolio.output_summary_stats()

        print("Creating equity curve...")
        print(self.portfolio.equity_curve.tail(10))
        pprint.pprint(stats)

        print("Signals: %s" % self.signals)
        print("Orders: %s" % self.orders)
        print("Fills: %s" % self.fills)

    def simulate_trading(self):
        """
        模拟回测并输出结果
        """

        self._run_backtest()
        self._output_performance()
