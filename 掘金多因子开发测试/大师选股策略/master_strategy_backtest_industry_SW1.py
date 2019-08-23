from gm.api import *
import QuantLib as ql
from WindPy import w
import json

import sys
sys.path.append('D:\\programs\\多因子策略开发\\掘金多因子开发测试\\工具')
# 引入工具函数和学习器
from utils import get_trading_date_from_now, list_wind2jq, list_gm2wind, get_SW1_industry, SW1_INDEX
from 行业轮动SW1 import RSRS_standardization
from 大师选股 import AllCode as STRATEGY
from 持仓配置 import 等权持仓 as WEIGHTS
from 候选股票 import SelectedStockPoolFromListV1

w.start()

# 回测的基本参数的设定
BACKTEST_START_DATE = '2019-07-04'  # 回测开始日期，开始日期与结束日期都是交易日，从开始日期开盘回测到结束日期收盘，与回测软件一直
BACKTEST_END_DATE = '2019-08-20'  # 回测结束日期
INCLUDED_INDEX = ['000300.SH', '000016.SH']  # 股票池代码，用Wind代码
EXCLUDED_INDEX = ['801780.SI']  # 剔除的股票代码
TRADING_DATES_LIST = ['10']  # 每月的调仓日期，非交易日寻找下一个最近的交易日

# 行业轮动模型配置
industry_wheel_movement = RSRS_standardization(BACKTEST_START_DATE, BACKTEST_END_DATE, [70]*len(SW1_INDEX), [300]*len(SW1_INDEX))

# 用于记录调仓信息的字典
stock_dict = {}
candidate_stock = []
selected_stock = []

# 根据回测阶段选取好调仓日期
trading_date_list = []  # 记录调仓日期的列表


def init(context):
    global date_trading  # 调仓日期获取
    i = 0
    print('回测开始日期：' + BACKTEST_START_DATE + '，结束日期：' + BACKTEST_END_DATE)
    while True:
        date_now = get_trading_date_from_now(BACKTEST_START_DATE, i, ql.Days)  # 遍历每个交易日
        print(('处理日期第%i个：' + date_now) % (i + 1))
        dates_trading = [get_trading_date_from_now(date_now.split('-')[0] + '-' + date_now.split('-')[1] + '-' + TRADING_DATE, 0, ql.Days)
                        for TRADING_DATE in TRADING_DATES_LIST]
        if date_now in dates_trading:
            trading_date_list.append(date_now)
        i += 1
        if date_now == BACKTEST_END_DATE:
            break
    print('时间列表整理完毕\n-----------------------------------------------\n')
    # 每天time_rule定时执行algo任务，time_rule处于09:00:00和15:00:00之间
    schedule(schedule_func=algo, date_rule='daily', time_rule='10:00:00')


def algo(context):
    global candidate_stock, selected_stock
    date_now = context.now.strftime('%Y-%m-%d')
    date_previous = get_trading_date_from_now(date_now, -1, ql.Days)  # 前一个交易日，用于获取因子数据的日期
    print(date_now + '日回测程序执行中...')
    if date_now not in trading_date_list:  # 非调仓日
        pass  # 预留非调仓日的微调空间
    else:  # 调仓日执行算法
        print(date_now + '日回测程序执行中...')
        # 根据指数获取股票候选池的代码
        code_list = SelectedStockPoolFromListV1(INCLUDED_INDEX, EXCLUDED_INDEX, date_previous).get_stock_pool()
        strategy = STRATEGY(code_list, date_previous)
        candidate_stock = strategy.select_code()  # 调仓日定期调节候选的股票池更新，非调仓日使用旧股票池
    sw1_industry = get_SW1_industry(date_previous, candidate_stock)  # 获取股票的申万一级行业信息字典
    industry_wm_result = industry_wheel_movement[date_now]  # 行业轮动内部自动替换为前一交易日
    candidate_selected_stock = [stock for stock in candidate_stock if sw1_industry[stock] is not None and industry_wm_result[sw1_industry[stock]] == 1]  # 忽略无行业信息的股票并根据行业择时信号选择候选股票

    if candidate_selected_stock == selected_stock:  # 候选股状态与之前一样，不用任何操作
        pass
    else:
        selected_stock = candidate_selected_stock  # 更新已持股池的信息
        if candidate_selected_stock == []:  # 空仓信号
            stock_dict[date_now] = {}
        else:
            candidate_selected_stock = list_wind2jq(candidate_selected_stock)
            stock_now = WEIGHTS(candidate_selected_stock, date_previous).get_weights()
            stock_dict[date_now] = stock_now


def on_backtest_finished(context, indicator):
    # 输出回测指标
    print(indicator)
    stock_json = json.dumps(stock_dict)
    stock_file = open('data\\stock_json.json', 'w')
    stock_file.write(stock_json)
    stock_file.close()


if __name__ == '__main__':
    run(strategy_id='4d2f6b1c-8f0a-11e8-af59-305a3a77b8c5',
        filename='master_strategy_backtest_industry_SW1.py',
        mode=MODE_BACKTEST,
        token='d7b08e7e21dd0315a510926e5a53ade8c01f9aaa',
        backtest_initial_cash=10000000,
        backtest_adjust=ADJUST_PREV,
        backtest_commission_ratio=0.0001,
        backtest_slippage_ratio=0.0001,
        backtest_start_time=BACKTEST_START_DATE+' 09:00:00',
        backtest_end_time=BACKTEST_END_DATE+' 15:00:00')