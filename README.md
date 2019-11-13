# HF
 1.数据源自聚宽的get_ticks
 
 2.Event的FillEvent中可以设置默认手续费，对于特别品种，应在execution.py的execute_order中设置手续费
 
 3.未考虑成交延时、滑点、部分成交的情况
 
 4.本项目为事件驱动回测框架，forecast模块中可以添加预测类模型，joking文件夹用来存放strategy运行脚本
 
 ps:目前forecast尚未完善；
 
    配对交易时，因数据合并对齐，丢失了部分ms级成交量，在考虑概率成交时，此现象在数据环节已经人为降低了成交概率，切记
