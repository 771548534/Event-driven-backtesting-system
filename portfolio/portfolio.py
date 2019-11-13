# -*- coding: utf-8 -*-

# portfolio.py

from __future__ import print_function

import datetime
from math import floor
try:
    import Queue as queue
except ImportError:
    import queue
import numpy as np
import pandas as pd

from event import FillEvent, OrderEvent, MarketEvent, SignalEvent
from performance import create_sharpe_ratio, create_drawdowns
from data import HistoricCSVDataHandler


class Portfolio(object):
    """
    在获取新行情数据后，处理头寸和市值positions ，holdings
    """
    def __init__(self, bars, events, start_date, initial_capital=100000.0):
        """
        初始化，设置初始资金
        Parameters:
        bars - DataHandler对象
        events - queue.Qeue()
        start_date - 开始日期，日内交易要写开始时间
        initial_capital - 初始资金
        """
        self.bars = bars
        self.events = events
        self.symbol_list = self.bars.symbol_list
        self.start_date = start_date
        self.initial_capital = initial_capital
        self.all_positions = self.construct_all_positions()
        self.current_positions = dict( (k,v) for k, v in [(s, 0) for s in self.symbol_list] )
        self.all_holdings = self.construct_all_holdings()
        self.current_holdings = self.construct_current_holdings()

    def construct_all_positions(self):
        """
        根据品种列表创建头寸字典
        """

        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d['datetime'] = self.start_date
        return [d]

    def construct_all_holdings(self):
        """
        根据品种列表创建市值字典
        """

        d = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['datetime'] = self.start_date
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return [d]

    def construct_current_holdings(self):
        """
        根据品种列表创建当前瞬时市值字典
        """

        d = dict((k, v) for k, v in [(s, 0.0) for s in self.symbol_list])
        d['cash'] = self.initial_capital
        d['commission'] = 0.0
        d['total'] = self.initial_capital
        return d

    def update_timeindex(self, event):
        """
        根据最新接收到的行情信息，计算当前瞬时头寸和市值，并更新到字典中
        """

        latest_datetime = self.bars.get_latest_bar_datetime(self.symbol_list[0])

        # 更新头寸
        dp = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        dp['datetime'] = latest_datetime
        for s in self.symbol_list:
            dp[s] = self.current_positions[s]
        # 存入字典
        self.all_positions.append(dp)

        # 更新市值
        dh = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        dh['datetime'] = latest_datetime
        dh['cash'] = self.current_holdings['cash']
        dh['commission'] = self.current_holdings['commission']
        dh['total'] = self.current_holdings['cash']
        for s in self.symbol_list:
            # 模拟实时
            market_value = self.current_positions[s] * self.bars.get_latest_bar_value(s, "current")
            dh[s] = market_value
            dh['total'] += market_value
        # 存入字典
        self.all_holdings.append(dh)

    def update_positions_from_fill(self, fill):
        """
        根据成交，更新头寸
        Parameters:
        fill - Fill对象
        """

        # 判断fill方向
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1
        # 更新头寸
        self.current_positions[fill.symbol] += fill_dir * fill.quantity

    def update_holdings_from_fill(self, fill):
        """
        根据成交，更新市值
        Parameters:
        fill - Fill对象
        """

        # 判断fill方向
        fill_dir = 0
        if fill.direction == 'BUY':
            fill_dir = 1
        if fill.direction == 'SELL':
            fill_dir = -1
        # 更新市值
        fill_cost = self.bars.get_latest_bar_value(fill.symbol, "current")
        cost = fill_dir * fill_cost * fill.quantity
        self.current_holdings[fill.symbol] += cost
        self.current_holdings['commission'] += fill.commission
        self.current_holdings['cash'] -= (cost + fill.commission)
        self.current_holdings['total'] -= (cost + fill.commission)

    def update_fill(self, event):
        """
        根据Fill对象，更新头寸和市值
        """

        if event.type == 'FILL':
            self.update_positions_from_fill(event)
            self.update_holdings_from_fill(event)

    def generate_naive_order(self, signal):
        """
        生成订单，暂未考虑资金管理与头寸管理
        Parameters:
        signal - SignalEvent
        """

        order = None

        symbol = signal.symbol
        direction = signal.signal_type
        strength = signal.strength

        mkt_quantity = 10
        cur_quantity = self.current_positions[symbol]
        order_type = 'MKT'

        if direction == 'LONG' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'BUY')
        if direction == 'SHORT' and cur_quantity == 0:
            order = OrderEvent(symbol, order_type, mkt_quantity, 'SELL')

        if direction == 'EXIT' and cur_quantity > 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'SELL')
        if direction == 'EXIT' and cur_quantity < 0:
            order = OrderEvent(symbol, order_type, abs(cur_quantity), 'BUY')

        return order

    def update_signal(self, event):
        """
        根据接收到的SignalEvent生成新订单
        """

        if event.type == 'SIGNAL':
            order_event = self.generate_naive_order(event)
            self.events.put(order_event)

    def create_equity_curve_dataframe(self):
        """
        根据市值字典，计算权益曲线dataframe
        """

        curve = pd.DataFrame(self.all_holdings)
        curve.set_index('datetime', inplace = True)
        curve['returns'] = curve['total'].pct_change()
        curve['equity_curve'] = (1.0 + curve['returns']).cumprod()
        self.equity_curve = curve

    def output_summary_stats(self):
        """
        回测后的统计总结
        """

        total_return = self.equity_curve['equity_curve'].iloc[-1]
        returns = self.equity_curve['returns']
        pnl = self.equity_curve['equity_curve']
        sharpe_ratio = create_sharpe_ratio(returns, periods=5.75*60*60)
        drawdown, max_dd, dd_duration = create_drawdowns(pnl)
        self.equity_curve['drawdown'] = drawdown
        stats = [("Total Return", "%0.2f%%" % ((total_return - 1.0) * 100.0)),
                 ("Sharpe Ratio", "%0.2f" % sharpe_ratio),
                 ("Max Drawdown", "%0.2f%%" % (max_dd * 100.0)),
                 ("Drawdown Duration", "%d" % dd_duration)]
        self.equity_curve.to_csv('equity.csv')
        return stats


if __name__ == '__main__':
    data_handler = HistoricCSVDataHandler(events=queue.Queue(), csv_dir='D:\\tick_data\\test_data',
                                          symbol_list=['A2001_2019-11-05', 'A2001_2019-11-06'])
    portfolio = Portfolio(bars=data_handler, events=queue.Queue(), start_date=1)

    market_event = MarketEvent()
    i = 0
    while i < 5:
        i += 1
        data_handler.update_bars()

    fill_event = FillEvent(direction='BUY', fill_cost=3, quantity=10, symbol='A2001_2019-11-05',
                       timeindex='09:00:01', exchange='dalian')
    portfolio.update_fill(fill_event)
    portfolio.update_timeindex(market_event)

    # print(portfolio.all_holdings)
    # print(portfolio.current_holdings)
    # print(portfolio.current_positions)
    # print(portfolio.current_holdings)

    # signal_event = SignalEvent(strategy_id=0, symbol='A1605_2016-01-06', signal_type='LONG', strength=1,
    #                            datetime='2016-01-05 09:00:01')
    # print(portfolio.current_positions)
    # print(portfolio.generate_naive_order(signal=signal_event))
    # portfolio.update_signal(signal_event)
    # print(portfolio.events.qsize())

    portfolio.create_equity_curve_dataframe()
    # print(portfolio.equity_curve['equity_curve'].iloc[-1])
    # df = portfolio.equity_curve
    # print(df.iloc[1])
    # series = portfolio.equity_curve['equity_curve']
    # print(series.iloc[-1])
    # print(portfolio.all_holdings)

    stats = portfolio.output_summary_stats()
    print(stats)