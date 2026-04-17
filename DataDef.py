"""
@Author:            ZHANG Biyuan
@Date:              2025/5/26
@Brief:             调度元件参数定义
"""
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum

@dataclass
class Thermal:
    """火电机组类"""
    # 机组运行参数
    idx: int = 1    # 机组编号
    pmax: float = 0.0
    pmin: float = 0.0
    RU: float = 0.0
    RD: float = 0.0
    SD: float = pmin
    SU: float = pmin
    UT: int = 0
    DT: int = 0
    cost_u: float = 0.0
    cost_d: float = 0.0
    u_max: int = 0
    d_max: int = 0
    ramp_fix_u: List[float] = field(default_factory=list)
    ramp_fix_d: List[float] = field(default_factory=list)

    # 成本函数参数
    bid_p: List[float] = field(default_factory=list)
    bid_pri: List[float] = field(default_factory=list)

    # 系统参数
    indices: List[int] = field(default_factory=list)
    buses: List[int] = field(default_factory=list)
    num: int = 1
    seg_num: int = 1

    # 另一种成本形式
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0



@dataclass
class Pumped:
    """抽水蓄能机组类（Pumped Storage Unit）"""
    # --- 基本功率与能量参数 ---
    pmax: float = 0.0  # 最大充/放电功率（绝对值，kW）
    pmin: float = 0.0  # 最小充/放电功率（绝对值，kW）
    emax: float = 0.0  # 最大储能容量（kWh）
    emin: float = 0.0  # 最小储能容量（kWh）
    e0: float = 0.0  # 初始储能状态（kWh），通常也作为终态平衡目标

    # --- 效率参数 ---
    n_c: float = 0.0  # 充电效率（0 < n_c ≤ 1），如 0.85
    n_d: float = 0.0  # 放电效率（0 < n_d ≤ 1），如 0.90

    # --- 爬坡速率（单位：kW/时段）---
    R_c: float = 0.0  # 充电功率爬坡上限（绝对值）
    R_d: float = 0.0  # 放电功率爬坡上限（绝对值）

    # --- 最小运行时间（单位：时段数）---
    t_ch: int = 0  # 最小连续充电时间（时段）
    t_dis: int = 0  # 最小连续放电时间（时段）
    t_off: int = 0  # 最小停机时间（时段）

    isFix: bool = False # 是否为恒定速率抽蓄

    # --- 启停成本（可选，若参与启停决策）---
    cost_u: float = 0.0  # 启动成本（充电或放电启动）
    cost_d: float = 0.0  # 停机成本（一般为0）

    # --- 系统拓扑信息 ---
    nodeid: int = -1  # 所在节点ID
    indices: List[int] = field(default_factory=list)  # 机组索引列表（若多台聚合）
    buses: List[int] = field(default_factory=list)  # 对应母线列表
    num: int = 1  # 机组数量（默认1台）
    idx: int = 1    # 群编号

    # ---报价 ---
    bid_p_ch: List[float] = field(default_factory=list)   # 若参与市场报价
    bid_pri_ch: List[float] = field(default_factory=list)

    bid_p_dis: List[float] = field(default_factory=list)   # 若参与市场报价
    bid_pri_dis: List[float] = field(default_factory=list)

    # 另一种成本形式
    a_ch: float = 0.0
    b_ch: float = 0.0
    c_ch: float = 0.0

    a_dis: float = 0.0
    b_dis: float = 0.0
    c_dis: float = 0.0

    seg_num: int = 1

