"""
@Author:            ZHANG Biyuan
@Date:              2025/5/26
@Brief:             Data reader for power system optimization
"""
from DataDef import *
import pandas as pd
from typing import List, Dict
import numpy as np


class DataReader:
    """Data reader"""
    def __init__(self, data_path: str, duration, l_rate=1.0):
        self.data_path = "inputdata/" + data_path
        self.data_file = pd.ExcelFile(self.data_path)
        self.l_rate = l_rate
        self.random_seed = 100

        self.DayMax = 20
        self.duration = int(duration)
        self.slf = []
        self.load_offset = {}
        self.loadc = {}

        self._parse_all_sheets()

    def _parse_all_sheets(self):
        self._parse_para_value()
        self._parse_slf_generators()
        self._parse_bra_ptdf()
        self._parse_thermal_basic()
        self._parse_pumped_basic()

    def _parse_thermal_basic(self):
        from func import quad_cost, split_power_segments, generate_ramp_fix

        thermal_df = pd.read_excel(self.data_file, sheet_name="thermal")
        derta_t = self.duration / self.input_duration

        self.thermals = []
        idx_map = {}

        for idx, row in thermal_df.iterrows():
            thermal = Thermal()

            if "机组序号" in thermal_df.columns:
                gid = int(row["机组序号"])
            else:
                gid = idx + 1
            thermal.indices = [gid]
            thermal.idx = gid

            thermal.unit_count = int(row.get("num", 1))

            pmax = float(row.get("pmax", 0))
            pmin = float(row.get("pmin", 0))
            thermal.pmax = pmax
            thermal.pmin = pmin
            thermal.SU = float(row.get('SU', thermal.pmin))
            thermal.SD = float(row.get('SD', thermal.pmin))

            r = float(row.get("r", 0))
            thermal.RU = r / derta_t
            thermal.RD = r / derta_t

            thermal.UT = int(row.get("ton", 0) * derta_t)
            thermal.DT = int(row.get("toff", 0) * derta_t)

            if "u_max" in thermal_df.columns:
                thermal.u_max = int(row.get("u_max", 0))
            else:
                if pmax > 300:
                    thermal.u_max = 3
                elif pmax >= 100:
                    thermal.u_max = 4
                else:
                    thermal.u_max = 5

            if "d_max" in thermal_df.columns:
                thermal.d_max = int(row.get("d_max", 0))
            else:
                thermal.d_max = thermal.u_max

            thermal.cost_u = float(row.get("fixed", 0))
            thermal.cost_d = float(row.get("fixed", 0))

            thermal.a = float(row.get("a", 0))
            thermal.b = float(row.get("b", 0))
            thermal.c = float(row.get("c", 0))
            thermal.seg_num = int(row.get("seg_num", 5))

            thermal.buses = [int(row.get("busno", 0))]

            seg = thermal.seg_num
            bid_p = split_power_segments(pmin, pmax, seg)
            thermal.bid_p = bid_p

            points = [pmin] + [pmin + sum(bid_p[:i]) for i in range(1, len(bid_p) + 1)]
            thermal.bid_pri = [quad_cost(p, thermal.a, thermal.b, thermal.c) for p in points]

            if self.duration == 96:
                if pmax < 50:
                    length = 1
                elif pmax < 150:
                    length = 3
                elif pmax < 200:
                    length = 3
                elif pmax < 300:
                    length = 4
                elif pmax < 600:
                    length = 6
                else:
                    length = 8

            elif self.duration == 24:
                if pmax < 100:
                    length = 1
                elif pmax < 150:
                    length = 2
                elif pmax < 200:
                    length = 2
                elif pmax < 300:
                    length = 2
                elif pmax < 600:
                    length = 3
                else:
                    length = 4
            else:
                raise ValueError("Unsupported duration for ramp_fix length rule")

            fix_u, fix_d = generate_ramp_fix(length, pmin)
            thermal.ramp_fix_u = fix_u
            thermal.ramp_fix_d = fix_d
            thermal.UT = thermal.UT + len(fix_d) + len(fix_u)

            self.thermals.append(thermal)
            idx_map[gid] = len(self.thermals) - 1

    def _parse_para_value(self):
        try:
            para_df = pd.read_excel(self.data_file, sheet_name="para", index_col=0)
        except Exception as e:
            raise RuntimeError(f"Failed to read parameter file: {e}")

        if para_df.shape[1] == 0:
            raise ValueError("Sheet 'para' has no data. Ensure first column is parameter names, second is values.")

        data_col = para_df.columns[0]

        def _get(key, cast_type, default=None):
            try:
                if key not in para_df.index:
                    if default is not None:
                        return default
                    raise KeyError(f"Parameter '{key}' not found in sheet.")
                val = para_df.at[key, data_col]
                if pd.isna(val):
                    if default is not None:
                        return default
                    raise ValueError(f"Parameter '{key}' is empty.")
                return cast_type(val)
            except Exception as e:
                raise type(e)(f"Error reading parameter '{key}': {e}")

        self.input_duration = _get("duration", int)
        self.input_busno = _get("busno", int)
        self.input_brano = _get("brano", int)
        self.input_swing = _get("swing", int)
        self.input_reserve = _get("reserve", float)

    def _parse_slf_generators(self, fig_flag=False):
        from func import interpolate_day_load, plot_all_load_curves

        slf_df = pd.read_excel(self.data_file, sheet_name="loadc")

        for i in range(self.DayMax):
            temp_loadc = list(
                slf_df.iloc[i * self.input_duration: (i + 1) * self.input_duration]["c1"]
            )

            if self.input_duration != self.duration:
                interpolated = interpolate_day_load(temp_loadc, self.duration, method="cubic")
                self.loadc[f"day_{i + 1}"] = list(interpolated)
            else:
                self.loadc[f"day_{i + 1}"] = temp_loadc

        load_df = pd.read_excel(self.data_file, sheet_name="load")
        self.load_sum = load_df["rt"].sum()

        if fig_flag:
            plot_all_load_curves(self.loadc)

    def _parse_bra_ptdf(self):
        bra_df = pd.read_excel(self.data_file, sheet_name="bra")
        brano_full = len(bra_df)
        busno = self.input_busno
        swing = self.input_swing - 1

        B = np.zeros((busno, busno))
        for i in range(brano_full):
            b1 = int(bra_df.loc[i, "b1"]) - 1
            b2 = int(bra_df.loc[i, "b2"]) - 1
            x = float(bra_df.loc[i, "x"])
            invx = 1 / x
            B[b1, b2] -= invx
            B[b2, b1] -= invx
            B[b1, b1] += invx
            B[b2, b2] += invx

        B_mod = B.copy()
        B_mod[swing, :] = float(1E+8)
        B_mod[:, swing] = float(1E+8)
        X = np.linalg.inv(B_mod)

        BL_full = np.zeros((brano_full, brano_full))
        A_full = np.zeros((brano_full, busno))
        for i in range(brano_full):
            BL_full[i, i] = 1 / bra_df.loc[i, "x"]
            A_full[i, int(bra_df.loc[i, "b1"]) - 1] = 1
            A_full[i, int(bra_df.loc[i, "b2"]) - 1] = -1

        PTDF_full = BL_full @ A_full @ X
        PTDF_full[np.abs(PTDF_full) <= 1e-5] = 0

        n_selected = max(1, int(np.ceil(brano_full * self.l_rate)))

        if n_selected >= brano_full:
            selected_indices = np.arange(brano_full)
        else:
            if hasattr(self, 'random_seed'):
                np.random.seed(self.random_seed)
            selected_indices = np.random.choice(
                brano_full, size=n_selected, replace=False
            )
            selected_indices = np.sort(selected_indices)

        bra_df_sub = bra_df.iloc[selected_indices].reset_index(drop=True)
        PTDF_sub = PTDF_full[selected_indices, :]
        brano = len(selected_indices)

        load_df = pd.read_excel(self.data_file, sheet_name="load")
        bus_load = {int(row.busno): float(row.rt) for _, row in load_df.iterrows()}

        self.bra_dict = {}
        self.load_offset_Mar = {f"day_{d + 1}": {} for d in range(self.DayMax)}

        for l in range(brano):
            orig_idx = selected_indices[l]
            row = bra_df.iloc[orig_idx]

            bus1 = int(row["b1"])
            bus2 = int(row["b2"])
            s = float(row["s"])
            state = int(row["state"]) if "state" in bra_df.columns else 1

            ptdf_dict = {bus + 1: float(PTDF_sub[l, bus]) for bus in range(busno)}

            self.bra_dict[l + 1] = {
                "b1": bus1,
                "b2": bus2,
                "s": s,
                "state": state,
                "ptdf": ptdf_dict,
                "original_id": int(orig_idx + 1)
            }

            load_offset_sum = sum(
                ptdf_dict.get(bus, 0) * bus_load.get(bus, 0)
                for bus in range(1, busno + 1)
            )
            for d in range(self.DayMax):
                self.load_offset_Mar[f"day_{d + 1}"][l + 1] = [
                    load_offset_sum * self.loadc[f"day_{d + 1}"][t]
                    for t in range(self.duration)
                ]

    def _parse_pumped_basic(self):
        from func import quad_cost, split_power_segments

        pumped_df = pd.read_excel(self.data_file, sheet_name="pumped")
        derta_t = self.duration / self.input_duration

        self.pumps = []
        idx_map = {}

        for idx, row in pumped_df.iterrows():
            pump = Pumped()

            if "机组序号" in pumped_df.columns:
                gid = int(row["机组序号"])
            else:
                gid = idx + 1
            pump.indices = [gid]
            pump.idx = gid

            pump.num = int(row.get("num", 4))

            pmax = float(row.get("pmax", 0.0))
            pmin = float(row.get("pmin", 0.0))
            emax = float(row.get("emax", 0.0))
            emin = float(row.get("emin", 0.0))
            e0 = float(row.get("e0", emax * 0.5))
            pump.pmax = pmax / pump.num
            pump.pmin = pmin / pump.num
            pump.emax = emax / pump.num
            pump.emin = emin / pump.num
            pump.e0 = e0 / pump.num

            pump.n_c = float(row.get("n_c", 0.85))
            pump.n_d = float(row.get("n_d", 0.90))

            r_c = float(row.get("R_c", 0.0))
            r_d = float(row.get("R_d", 0.0))
            pump.R_c = r_c / derta_t / pump.num
            pump.R_d = r_d / derta_t / pump.num

            t_ch_hr = float(row.get("t_ch", 1.0))
            t_dis_hr = float(row.get("t_dis", 1.0))
            t_off_hr = float(row.get("t_off", 1.0))
            pump.t_ch = max(1, int(round(t_ch_hr * derta_t)))
            pump.t_dis = max(1, int(round(t_dis_hr * derta_t)))
            pump.t_off = max(1, int(round(t_off_hr * derta_t)))

            pump.cost_u = float(row.get("cost_u", 0.0))
            pump.cost_d = float(row.get("cost_d", 0.0))

            pump.buses = [int(row.get("busno", 0))]

            pump.a_ch = float(row.get("a", 0.0))
            pump.b_ch = float(row.get("b", 0.0))
            pump.c_ch = float(row.get("c", 0.0))

            pump.a_dis = float(row.get("a", 0.0))
            pump.b_dis = float(row.get("b", 0.0))
            pump.c_dis = float(row.get("c", 0.0))
            pump.isFix = bool(row.get("isFix", False))

            seg_num = int(row.get("seg_num", 5))
            pump.seg_num = seg_num

            bid_p_ch = split_power_segments(pmin, pmax, seg_num)
            points_ch = [pmin] + [pmin + sum(bid_p_ch[:i]) for i in range(1, len(bid_p_ch) + 1)]
            bid_pri_ch = [quad_cost(p, pump.a_ch, pump.b_ch, pump.c_ch) for p in points_ch]

            pump.bid_p_ch = bid_p_ch
            pump.bid_pri_ch = bid_pri_ch

            bid_p_dis = split_power_segments(pmin, pmax, seg_num)
            points_dis = [pmin] + [pmin + sum(bid_p_dis[:i]) for i in range(1, len(bid_p_dis) + 1)]
            bid_pri_dis = [quad_cost(p, pump.a_dis, pump.b_dis, pump.c_dis) for p in points_dis]

            pump.bid_p_dis = bid_p_dis
            pump.bid_pri_dis = bid_pri_dis

            self.pumps.append(pump)
            idx_map[gid] = len(self.pumps) - 1

        self.pumped_idx_map = idx_map