# -*- coding: utf-8 -*-

# performance.py

from __future__ import print_function

import numpy as np
import pandas as pd


def create_sharpe_ratio(returns, periods=252*5.75*60*60):
    """
    以0为基准，计算夏普比率
    returns - 收益率，pandas Series
    periods - Daily (252), Hourly (252*5.75), Minutely(252*5.75*60), Secondly(252*5.75*60*60) etc.
    """

    return np.sqrt(periods) * (np.mean(returns)) / np.std(returns)


def create_drawdowns(pnl):
    """
    计算回撤
    Parameters:
    pnl - 收益率A pandas Series
    Returns - 回撤，最大回撤， 最长回撤时间
    """

    # High Water Mark
    hwm = [0]
    # 回撤与回撤实现，series
    idx = pnl.index
    drawdown = pd.Series(index=idx)
    duration = pd.Series(index=idx)
    # 循环更新高水位并计算回撤与回撤时间
    for t in range(1, len(idx)):
        hwm.append(max(hwm[t-1], pnl.iloc[t]))
        drawdown.iloc[t] = (hwm[t]-pnl.iloc[t])
        duration.iloc[t] = (0 if drawdown.iloc[t] == 0 else duration.iloc[t-1]+1)
    return drawdown, drawdown.max(), duration.max()


if __name__ == '__main__':
    equity = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 109, 108, 109, 105]
    series = pd.Series(data=equity, dtype='float64')
    drawdown, max_drawdown, max_duration = create_drawdowns(series)
    print(drawdown, max_drawdown, max_duration)
    print(create_sharpe_ratio(equity, periods=len(equity)))