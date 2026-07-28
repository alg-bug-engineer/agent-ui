"""
Ring-Barrier环图配时数据解析与可视化工具
解析配时方案CSV，展示NEMA标准的Ring-Barrier结构
"""
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import re

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 进口道方向映射 - 解码后的方向代码 -> 中文名称
# ============================================================
DIRECTION_NAME = {
    0: '北', 2: '东', 4: '南', 6: '西',
    1: '东北', 3: '东南', 5: '西南', 7: '西北',
}

# ============================================================
# 转向映射 - 解码后的转向代码 -> 中文名称
# ============================================================
TURN_NAME = {
    -1: '未知', 11: '直行', 12: '左转', 13: '右转',
    14: '直左调头', 15: '右调头', 16: '左右调头', 17: '直右调头', 18: '左直右调头',
    21: '直左混行', 22: '直右混行', 23: '左右混行', 24: '直左右混行',
    31: '掉头', 41: '直行掉头', 42: '左转掉头',
    98: '其他', 99: '其他', 100: '出入口行人', 101: '入口行人', 102: '出口行人',
}

# ============================================================
# 【待修正】channelDim解析映射 - 来自test2.py
# ============================================================
direction_map = {0: 0, 1: 2, 2: 4, 3: 6, 4: 1, 5: 3, 6: 5, 7: 7}
turn_map = {
    1: 12, 2: 11, 3: 13, 4: 31, 5: 42, 6: 21, 7: 23, 8: 22, 9: 24,
    10: 41, 11: 101, 12: 102, 13: 100, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18
}

def channelDim_analysis(channel_list: list):
    """解析channelDim"""
    result = []
    for num in channel_list:
        if num == 0:
            result.append([])
        else:
            binary_num = bin(num)[2:]
            zero_count = (8 - len(binary_num) % 8) % 8
            binary_num = "0" * zero_count + binary_num
            binary_groups = [binary_num[i:i+8] for i in range(0, len(binary_num), 8)]
            group_list = []
            for group in binary_groups:
                first_three = int(group[:3], 2)
                last_five = int(group[3:], 2)
                if last_five in turn_map:
                    direction = direction_map.get(first_three, first_three)
                    turn = turn_map[last_five]
                    group_list.append((direction, turn))
            result.append(group_list)
    return result

def parse_cycle_list(cycle_list_str):
    """解析cycle_list，返回每个Ring的相位序列和barrier位置"""
    cycle_dict = json.loads(cycle_list_str.replace('""', '"'))
    rings = []
    
    for i in range(1, len(cycle_dict) + 1):
        ring_key = f'Cycle{i}'
        if ring_key in cycle_dict:
            ring_str = cycle_dict[ring_key]
            # 解析相位和barrier: "1 2_3_" -> phases=[1,2,3], barriers after 2,3
            phases = []
            barriers = []
            parts = ring_str.replace('_', ' _ ').split()
            phase_idx = 0
            for part in parts:
                if part == '_':
                    if phases:
                        barriers.append(phase_idx - 1)
                elif part.strip():
                    phases.append(int(part))
                    phase_idx += 1
            rings.append({'phases': phases, 'barriers': barriers})
    
    return rings

def parse_timing_csv(csv_path):
    """解析配时方案CSV文件"""
    df = pd.read_csv(csv_path)
    records = []
    
    for _, row in df.iterrows():
        phase_list = json.loads(row['phase_list'].replace('""', '"'))
        phase_data = phase_list[0]
        
        green_times = [int(x) for x in phase_data['greenTime'].split()]
        yellow_times = [int(x) for x in phase_data['yellowTime'].split()]
        red_times = [int(x) for x in phase_data['redTime'].split()]
        channel_dims = [int(x) for x in phase_data['channelDim'].split()]
        
        channel_info = channelDim_analysis(channel_dims)
        rings = parse_cycle_list(row['cycle_list'])
        
        records.append({
            'time': row['request_time'],
            'pattern': row['pattern'],
            'cycle_len': row['cycle_len'],
            'ring_count': row['ring_count'],
            'green_times': green_times,
            'yellow_times': yellow_times,
            'red_times': red_times,
            'channel_info': channel_info,
            'rings': rings
        })
    
    return records

def get_phase_label(phase_no, channel_info):
    """获取相位的方向转向标签"""
    if phase_no <= len(channel_info) and channel_info[phase_no - 1]:
        labels = []
        for dir_code, turn_code in channel_info[phase_no - 1]:
            dir_name = DIRECTION_NAME.get(dir_code, f'D{dir_code}')
            turn_name = TURN_NAME.get(turn_code, f'T{turn_code}')
            labels.append(f'{dir_name}{turn_name}')
        return '\n'.join(labels)  # 显示所有转向信息
    return ''

def visualize_ring_barrier(record, output_path=None):
    """可视化Ring-Barrier环图"""
    rings = record['rings']
    cycle_len = record['cycle_len']
    green_times = record['green_times']
    yellow_times = record['yellow_times']
    red_times = record['red_times']
    channel_info = record['channel_info']
    
    n_rings = len(rings)
    fig, ax = plt.subplots(figsize=(18, 4 + n_rings * 2))
    
    colors = {'green': '#4CAF50', 'yellow': '#FFC107', 'red': '#F44336', 'barrier': '#333333'}
    ring_height = 1.0
    ring_gap = 0.5
    
    # 计算每个ring的时间轴
    for ring_idx, ring in enumerate(rings):
        y_pos = (n_rings - ring_idx - 1) * (ring_height + ring_gap)
        x_pos = 0
        
        for phase_idx, phase_no in enumerate(ring['phases']):
            g = green_times[phase_no - 1] if phase_no <= len(green_times) else 0
            y = yellow_times[phase_no - 1] if phase_no <= len(yellow_times) else 0
            r = red_times[phase_no - 1] if phase_no <= len(red_times) else 0
            total = g + y + r
            
            if total == 0:
                continue
            
            # 绿灯
            if g > 0:
                rect = patches.Rectangle((x_pos, y_pos), g, ring_height,
                                         facecolor=colors['green'], edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
                label = get_phase_label(phase_no, channel_info)
                ax.text(x_pos + g/2, y_pos + ring_height/2, f'Φ{phase_no}\n{g}s\n{label}',
                       ha='center', va='center', fontsize=10, fontweight='bold')
            
            # 黄灯
            if y > 0:
                rect = patches.Rectangle((x_pos + g, y_pos), y, ring_height,
                                         facecolor=colors['yellow'], edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
            
            # 全红
            if r > 0:
                rect = patches.Rectangle((x_pos + g + y, y_pos), r, ring_height,
                                         facecolor=colors['red'], edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
            
            x_pos += total
            
            # 画barrier线
            if phase_idx in ring['barriers']:
                ax.axvline(x=x_pos, color=colors['barrier'], linewidth=2, linestyle='--', alpha=0.7)
        
        # Ring标签
        ax.text(-8, y_pos + ring_height/2, f'Ring {ring_idx + 1}',
               ha='right', va='center', fontsize=14, fontweight='bold')
    
    # 设置坐标轴
    ax.set_xlim(-15, cycle_len + 10)
    ax.set_ylim(-0.5, n_rings * (ring_height + ring_gap))
    ax.set_xlabel('时间 (秒)', fontsize=12)
    ax.set_title(f'Ring-Barrier环图 - 方案{record["pattern"]} @ {record["time"]}\n周期: {cycle_len}秒, {n_rings}环',
                fontsize=14, fontweight='bold')
    ax.set_yticks([])
    ax.axhline(y=0, color='black', linewidth=0.5)
    
    # 图例
    legend_elements = [
        patches.Patch(facecolor=colors['green'], edgecolor='black', label='绿灯'),
        patches.Patch(facecolor=colors['yellow'], edgecolor='black', label='黄灯'),
        patches.Patch(facecolor=colors['red'], edgecolor='black', label='全红'),
        plt.Line2D([0], [0], color=colors['barrier'], linewidth=2, linestyle='--', label='Barrier')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11)
    
    # 在图像下方添加channelDim解析信息
    info_lines = ["channelDim解析结果:"]
    for phase_idx, channels in enumerate(channel_info):
        if channels:
            g = green_times[phase_idx] if phase_idx < len(green_times) else 0
            ch_str = ', '.join([f'{DIRECTION_NAME.get(d,"D"+str(d))}{TURN_NAME.get(t,"T"+str(t))}' for d, t in channels])
            info_lines.append(f"Φ{phase_idx+1}: 绿{g}s | {ch_str}")
    
    info_text = '\n'.join(info_lines)
    fig.text(0.02, -0.02, info_text, fontsize=10, va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.25)
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f'图表已保存: {output_path}')
    
    plt.show()

def print_timing_summary(record):
    """打印配时摘要"""
    print(f"\n{'='*70}")
    print(f"【展示时刻】{record['time']}")
    print(f"【配时方案号】{record['pattern']}")
    print(f"【周期长度】{record['cycle_len']}秒")
    print(f"【环数】{record['ring_count']}")
    print(f"{'='*70}")
    
    for ring_idx, ring in enumerate(record['rings']):
        print(f"\n【Ring {ring_idx + 1}】相位序列: {ring['phases']}, Barrier位置: {ring['barriers']}")
        for phase_no in ring['phases']:
            g = record['green_times'][phase_no - 1] if phase_no <= len(record['green_times']) else 0
            y = record['yellow_times'][phase_no - 1] if phase_no <= len(record['yellow_times']) else 0
            channels = record['channel_info'][phase_no - 1] if phase_no <= len(record['channel_info']) else []
            
            if g > 0 or channels:
                channel_str = ', '.join([f'({d},{t})' for d, t in channels]) if channels else '无'
                print(f"  Φ{phase_no}: 绿{g}s 黄{y}s | channelDim: {channel_str}")

def find_record(records, target_date=None, target_time=None):
    """根据日期和时间查找记录，默认返回第一个3环方案"""
    filtered = records
    
    if target_date:
        filtered = [r for r in filtered if target_date in r['time']]
        if not filtered:
            print(f"未找到日期包含 '{target_date}' 的记录")
            return None
    
    if target_time:
        for r in filtered:
            if target_time in r['time']:
                return r
        print(f"未找到时间包含 '{target_time}' 的记录")
    
    # 默认返回第一个3环方案
    for r in filtered:
        if r['ring_count'] == 3:
            return r
    return filtered[0] if filtered else None

def list_available_dates(records):
    """列出所有可用的日期"""
    dates = sorted(set(r['time'].split()[0] for r in records))
    print("\n可用日期:")
    for d in dates:
        count = sum(1 for r in records if d in r['time'])
        print(f"  {d} ({count}条记录)")
    return dates

def main(target_date=None, target_time=None):
    csv_path = r'C:\HZY\traffic\绿波带优化\0312流向急活\data\经十路-转山西路配时方案.csv'
    
    print("正在解析配时方案CSV...")
    records = parse_timing_csv(csv_path)
    print(f"共解析 {len(records)} 条配时记录")
    
    if not records:
        return
    
    list_available_dates(records)
    
    record = find_record(records, target_date, target_time)
    if record:
        print_timing_summary(record)
        output_path = r'C:\HZY\traffic\绿波带优化\0312流向急活\output\雷视\ring_barrier_diagram.png'
        visualize_ring_barrier(record, output_path)

if __name__ == '__main__':
    import sys
    # 用法: python ring_timing_visualizer.py [日期] [时间]
    # 例如: python ring_timing_visualizer.py 2026-03-12 07:21
    # 2026/3/11  7:21:31
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    target_time = sys.argv[2] if len(sys.argv) > 2 else None
    main(target_date, target_time)
