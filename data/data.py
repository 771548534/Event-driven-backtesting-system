from __future__ import print_function

from abc import ABCMeta, abstractmethod
import datetime
import os, os.path
import queue
import re

import numpy as np
import pandas as pd

from event import MarketEvent


class DataHandler(object):
    """
    抽象基类，可以被即成为用于历史数据和实盘数据
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_latest_bar(self, symbol):
        """
        返回最后一条行情
        """
        raise NotImplementedError("Should implement get_latest_bar()")

    @abstractmethod
    def get_latest_bars(self, symbol, N=1):
        """
        返回最后N条行情
        """
        raise NotImplementedError("Should implement get_latest_bars()")

    @abstractmethod
    def get_latest_bar_datetime(self, symbol):
        """
        返回最后一条行情的时间，datetime对象
        """
        raise NotImplementedError("Should implement get_latest_bar_datetime()")

    @abstractmethod
    def get_latest_bar_value(self, symbol, val_type):
        """
        返回最后一条行情的数据内容
        """
        raise NotImplementedError("Should implement  get_latest_bar_value()")

    @abstractmethod
    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        返回最后N条行情的数据内容
        """
        raise NotImplementedError("Should implement get_latest_bars_values()")

    @abstractmethod
    def update_bars(self):
        """
        将最后一条行情推送至行情队列中
        """
        raise NotImplementedError("Should implement update_bars()")


class HistoricCSVDataHandler(DataHandler):
    """
    读取并处理csv文件，模拟实盘情况，获取最新一条行情数据
    """
    def __init__(self, events, csv_dir, symbol_list):
        """
        初始化
        Parameters:
        events - 事件队列，即queue.Queue()
        csv_dir - csv文件路径
        symbol_list - 品种标签，采用csv文件名
        """
        self.events = events
        self.csv_dir = csv_dir
        self.symbol_list = symbol_list
        # 存储清洗好的数据
        self.symbol_data = {}
        # 存储获取到的行情数据，模拟实盘的数据实时获取
        self.latest_symbol_data = {}
        self.continue_backtest = True

        # 配对策略，传入2个csv文件时的数据预处理
        if len(self.symbol_list) == 2:
            self._open_convert_csv_files_in_pairs()
        # 非配对策略，传入一个、三个或多个csv文件时的数据预处理
        else:
            self._open_convert_csv_files()

        self.symbol_iters = self._initialize_iters()

    def _open_convert_csv_files(self):
        """
        打开若干csv文件，将数据存入字典。数据源自聚宽的get_ticks
        """

        # comb_index = None
        for s in self.symbol_list:
            # Load the CSV file with no header information, indexed on date
            # self.symbol_data[s] = pd.read_csv(os.path.join(self.csv_dir, '%s.csv' % s), header=0, index_col=0,
            #                                   parse_dates=True, names=['datetime', 'open', 'high','low', 'close',
            #                                                            'volume', 'adj_close']).sort_index()

            # 读取聚宽tick数据，列名为['time', 'current', 'high', 'low', 'volume', 'money', 'position', 'a1_v',
            #                          'a1_p', 'b1_v', 'b1_p']
            self.symbol_data[s] = pd.read_csv(os.path.join(self.csv_dir, '%s.csv' % s), header=0, index_col=0)# >>>>
            self.symbol_data[s]['time'] = self.symbol_data[s]['time'].astype('str')
            self.symbol_data[s]['time'] = self.symbol_data[s]['time'].apply(lambda t: re.findall(
                r'[0-9]*:[0-9]*:[0-9][0-9]', t)[0])

            # Combine the index to pad forward values，但是对于期货日内tick数据，不需要补齐日期索引
            # if comb_index is None:
            #     comb_index = self.symbol_data[s].index
            # else:
            #     comb_index.union(self.symbol_data[s].index)
            # Set the latest symbol_data to None
            self.latest_symbol_data[s] = []
        # Reindex the dataframes，但是对于期货日内tick数据，不需要补齐日期索引
        # for s in self.symbol_list:
        #     self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()

    def _open_convert_csv_files_in_pairs(self):
        """
        打开一对csv文件，将数据存入字典。数据源自聚宽的get_ticks
        """

        # 分别打开两个文件，提取时间，格式为‘09：01：01’，丢弃秒级重复数据，保留第一条
        symbol_data_x = pd.read_csv(os.path.join(self.csv_dir, '%s.csv' % self.symbol_list[0]), header=0,
                                    index_col=0)
        symbol_data_x['time'] = symbol_data_x['time'].astype(str).apply(lambda t: re.findall(
            r'[0-9]*:[0-9]*:[0-9][0-9]', t)[0])
        symbol_data_x.drop_duplicates(subset='time', keep='first', inplace=True)

        symbol_data_y = pd.read_csv(os.path.join(self.csv_dir, '%s.csv' % self.symbol_list[1]), header=0,
                                    index_col=0)
        symbol_data_y['time'] = symbol_data_y['time'].astype(str).apply(lambda t: re.findall(
            r'[0-9]*:[0-9]*:[0-9][0-9]', t)[0])
        symbol_data_y.drop_duplicates(subset='time', keep='first', inplace=True)

        # 将两个数据进行拼接，并以time列进行数据对其，对于缺失数据，以前一秒来补齐，然后存入字典
        symbol_data_xy = symbol_data_x.merge(symbol_data_y, how='outer', on='time')
        symbol_data_xy.sort_values(by='time', inplace=True, ascending=True)
        symbol_data_xy.reset_index(drop=True, inplace=True)
        symbol_data_xy.fillna(method='ffill', inplace=True)
        self.symbol_data[self.symbol_list[0]] = symbol_data_xy[['time', 'current_x', 'high_x', 'low_x', 'volume_x',
                                                               'money_x', 'position_x', 'a1_v_x', 'a1_p_x',
                                                               'b1_v_x', 'b1_p_x']]
        self.symbol_data[self.symbol_list[1]] = symbol_data_xy[['time', 'current_y', 'high_y', 'low_y', 'volume_y',
                                                               'money_y', 'position_y', 'a1_v_y', 'a1_p_y',
                                                               'b1_v_y', 'b1_p_y']]

        # 在merge后，对列统一重命名
        for s in self.symbol_list:
            self.symbol_data[s].columns = ['time', 'current', 'high', 'low', 'volume', 'money', 'position', 'a1_v',
                                           'a1_p', 'b1_v', 'b1_p']
            self.latest_symbol_data[s] = []

    def _get_new_bar(self, symbol):
        """
        从清洗好的数据字典中，获取最新一条行情数据。模仿实盘的数据接收
        """

        for b in self.symbol_data[symbol].iterrows():
            yield b

    def get_latest_bar(self, symbol):
        """
        返回最新获取到的行情数据
        """

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1]

    def get_latest_bars(self, symbol, N=1):
        """
        返回最新获取到的N条行情数据
        """

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-N:]

    def get_latest_bar_datetime(self, symbol):
        """
        返回最新获取到的行情数据的time值
        """

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return bars_list[-1][1]['time']

    def get_latest_bar_value(self, symbol, val_type):
        """
        根据val_type，返回最新获取到的行情数据的value
        """

        try:
            bars_list = self.latest_symbol_data[symbol]
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return getattr(bars_list[-1][1], val_type)

    def get_latest_bars_values(self, symbol, val_type, N=1):
        """
        根据val_type，返回最新获取到的N条行情数据的value
        """

        try:
            bars_list = self.get_latest_bars(symbol, N)
        except KeyError:
            print("That symbol is not available in the historical data set.")
            raise
        else:
            return np.array([getattr(b[1], val_type) for b in bars_list])

    def update_bars(self):
        """
        模拟实盘数据接收，从存储的数据字典中获取1条新数据，并存入latest_symbol_data以备回测使用
        """

        for s in self.symbol_list:
            try:
                bar = next(self.symbol_iters[s])
            except StopIteration:
                self.continue_backtest = False
            else:
                if bar is not None:
                    self.latest_symbol_data[s].append(bar)
        self.events.put(MarketEvent())

    def _initialize_iters(self):
        """
        根据品种列表，为每个csv初始化一个迭代器，装入字典
        """

        symbol_iters = {}
        for s in self.symbol_list:
            symbol_iters[s] = self._get_new_bar(s)
        return symbol_iters


if __name__ == '__main__':
    data_handler = HistoricCSVDataHandler(events=queue.Queue(), csv_dir='D:\\tick_data\\test_data',
                                          symbol_list=['A2001_2019-11-05', 'A2001_2019-11-06'])
    # print(data_handler.symbol_data['A2001_2019-11-05'].info())
    # data_handler._open_convert_csv_files_in_pairs()
    # print(data_handler.symbol_data['A2001_2019-11-05']['current'])
    i = 0
    while i < 10:
        data_handler.update_bars()
        i += 1
    print(data_handler.latest_symbol_data['A2001_2019-11-05'][-1])
    # print(data_handler.get_latest_bars('A1605_2016-01-05', 3))
    # print(data_handler.get_latest_bar_datetime('A1605_2016-01-05'))
    # print(data_handler.get_latest_bar_value('A1605_2016-01-05', 'current'))
    # print(data_handler.get_latest_bars_values('A1605_2016-01-05', 'current', 9))
