#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py — 一键复现最终提交 result.txt
=========================================
完整复现链路（官方要求"生成 txt 文档的完整的可运行程序"）：

    results/result.txt（含 V_T，方式1 精确值）
        │  python method2_multistrategy.py   （方式2 策略 v2：c^R / 有效c / 网格搜索）
        ▼
    results/result_method2_v2.txt
        │  python method2_v2plus.py          （方式2 主算法 v2+：逐轮组合枚举堆积引理）
        ▼
    results/result_method2_v2plus.txt
        │  python merge_v2_v2plus.py         （按条目取 v2 / v2plus 最优）
        ▼
    results/result_method2_merged.txt
        │  校验：与 result.txt 逐条一致（内容级比对）
        ▼
    PASS / FAIL

用法：  python run_all.py          （在提交包根目录运行）

说明：
- 方式2 的所有 V_E 均来自 S 盒 LAT 结构常数 {0.125,0.25,0.375,0.5} 与堆积引理，
  未使用任何方式1结果（合规）。
- 运行时间约 1~2 分钟（多策略枚举），无需第三方依赖（纯 Python 标准库）。
"""
import os
import re
import sys
import math
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, 'results')
SRC = os.path.join(ROOT, 'src')
PY = sys.executable

PAT = re.compile(r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([-0-9.eE+]+),\s*([-0-9.eE+]+)\)')

def parse(fn):
    d = {}
    with open(fn, 'r', encoding='utf-8') as f:
        for line in f:
            m = PAT.match(line.strip())
            if m:
                d[(int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16))] = \
                    (float(m.group(4)), float(m.group(5)))
    return d

def run_step(name, script, cwd):
    print(f'\n[{name}] 运行 {script} ...')
    r = subprocess.run([PY, os.path.join(SRC, script)], cwd=cwd,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.stdout:
        for line in r.stdout.splitlines()[-6:]:
            print('   ', line)
    if r.returncode != 0:
        print('   [STDERR]', r.stderr[-800:] if r.stderr else '(无)')
        print('   [失败] 步骤中断')
        sys.exit(1)
    return r

def main():
    print('=' * 60)
    print('SPN 32-bit 线性密码分析 — 提交结果一键复现')
    print('=' * 60)

    # 0. 前置检查
    result = os.path.join(RESULTS, 'result.txt')
    if not os.path.exists(result):
        print(f'[错误] 缺少 {result}，请确认在提交包根目录运行。')
        sys.exit(1)
    n = sum(1 for _ in open(result, encoding='utf-8'))
    print(f'[0/4] 输入 result.txt：{n} 条（含方式1 V_T）')

    # 1. 方式2 策略 v2
    run_step('1/4', 'method2_multistrategy.py', RESULTS)

    # 2. 方式2 主算法 v2+
    run_step('2/4', 'method2_v2plus.py', RESULTS)

    # 3. 合并取最优
    run_step('3/4', 'merge_v2_v2plus.py', RESULTS)

    # 4. 校验
    print('\n[4/4] 校验 merged 与提交 result.txt ...')
    merged = parse(os.path.join(RESULTS, 'result_method2_merged.txt'))
    orig = parse(result)
    if len(merged) != len(orig):
        print(f'   [FAIL] 条目数不一致：merged={len(merged)} result.txt={len(orig)}')
        sys.exit(1)
    bad = [(k, merged[k], orig[k]) for k in merged
           if k not in orig or abs(merged[k][1] - orig[k][1]) > 1e-9]
    if bad:
        print(f'   [FAIL] {len(bad)} 条 V_E 与提交不一致，示例：')
        for k, a, b in bad[:5]:
            print(f'     R={k[0]} u={k[1]:08X} v={k[2]:08X}: merged={a[1]:.6e} result={b[1]:.6e}')
        sys.exit(1)

    # 得分复算（钳制，负分计0）
    nv = s = 0
    for k, (vt, ve) in merged.items():
        if ve != 0 and vt != 0 and k[1] != 0 and k[2] != 0 and \
                0.75 * abs(vt) <= abs(ve) <= 1.25 * abs(vt):
            nv += 1
            s += max(math.log2((2 ** (2 * k[0])) * abs(ve)), 0.0)
    print(f'   [PASS] 完全复现：{len(orig)} 条全部一致')
    print(f'   [得分] 有效 {nv}/346，钳制后总分 {s:.2f}（与自评得分.txt 一致应约 2996.53）')
    print('\n复现完成。最终提交文件：results/result.txt')

if __name__ == '__main__':
    main()
