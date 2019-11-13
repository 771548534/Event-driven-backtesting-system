# HF
1.数据源自聚宽的get_ticks
2.Event的FillEvent中可以设置默认手续费，对于特别品种，应在execution.py的execute_order中设置手续费
3.未考虑成交延时、滑点、部分成交的情况
4.本项目为事件驱动回测框架，forecas模块中可以添加预测类模型，joking文件夹用来存放strategy运行脚本
