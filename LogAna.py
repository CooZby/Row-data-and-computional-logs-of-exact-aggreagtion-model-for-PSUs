import re
import pandas as pd

import re
import pandas as pd

import re
import pandas as pd


def parse_log_robust(log_file_path, output_file='results_summary.xlsx'):
    all_results = []

    # 1. 读取文件
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 2. 正则匹配每一块数据
    pattern = r'\[总表\] 系统: (.*?), Day: (.*?), Solver: (.*?)\n(.*?)(?=\n\[总表\]|\Z)'

    matches = re.findall(pattern, content, re.DOTALL)

    print(f"检测到 {len(matches)} 组数据，正在处理...")

    for system, day, solver, table_str in matches:
        # 3. 使用正则表达式精准提取每一行数据
        row_pattern = r"^\d+\s+([\w_]+)\s+([\d.e+-]+)\s+([\d.]+)\s+([\d.%-]+)"

        lines = table_str.split('\n')
        current_data = {}

        for line in lines:
            match = re.search(row_pattern, line.strip())
            if match:
                model_name = match.group(1)
                cost = str(match.group(2))
                time_val = float(match.group(3))
                error_val = match.group(4)

                current_data[model_name] = {
                    'Cost': cost,
                    'Time': time_val,
                    'Error': error_val
                }

        # 4. 组装这一组（System/Day）的最终结果
        if current_data:
            row_result = {
                'System': system.strip(),
                'Day': int(day.strip()),
                'Solver': solver.strip()
            }

            # M1
            if 'M1_Basic' in current_data:
                row_result['M1_Time'] = current_data['M1_Basic']['Time']

            # M2
            if 'M2_SumAgg' in current_data:
                row_result['M2_Time'] = current_data['M2_SumAgg']['Time']
                row_result['M2_Error'] = float(current_data['M2_SumAgg']['Error'])

            # M3
            if 'M3_Agg' in current_data:
                row_result['M3_Time'] = current_data['M3_Agg']['Time']
                row_result['M3_Error'] = float(current_data['M3_Agg']['Error'])

            # M4
            if 'M4_AggD' in current_data:
                row_result['M4_Time'] = current_data['M4_AggD']['Time']
                row_result['M4_Error'] = float(current_data['M4_AggD']['Error'])

            all_results.append(row_result)


    # 5. 导出结果
    if all_results:
        df = pd.DataFrame(all_results)

        # 指定列顺序
        cols = ['System', 'Day', 'Solver', 'M1_Time', 'M2_Time', 'M2_Error', 'M3_Time', 'M3_Error', 'M4_Time',
                'M4_Error']
        final_cols = [c for c in cols if c in df.columns]
        df = df[final_cols]

        df.to_csv(output_file.replace('.xlsx', '.csv'), index=False)

        print("-" * 30)
        print("✅ 提取成功！详细数据如下：")
        print("-" * 30)
        print(df.to_string(index=False))

        # ==========================================
        # 修复部分：计算平均值统计
        # ==========================================
        print("-" * 30)
        print("📊 各系统平均统计 (保留3位小数)：")
        print("-" * 30)

        # 修改点 1: 只按 ['System'] 分组
        # 修改点 2: 添加 numeric_only=True，这会自动忽略 'Solver' 等字符串列，只对数字列求平均
        stats_df = df.groupby(['System']).mean(numeric_only=True).round(3)

        # 打印结果
        print(stats_df.to_string())

    else:
        print("❌ 未提取到任何数据，请检查日志格式是否完全匹配。")
# --- 使用示例 ---
log_filename = '4M_gurobi.log'


# 运行函数
parse_log_robust(log_filename)