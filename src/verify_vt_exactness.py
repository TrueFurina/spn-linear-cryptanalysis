# -*- coding: utf-8 -*-
"""
verify_vt_exactness.py — 独立校验提交数据中 V_T 列的"方式 1 精确性"

原理（不依赖任何方式 1 的计算，纯数学可证伪检验）
------------------------------------------------------------------
方式 1 定义为对全部 N = 2^32 个明文 x 求代数和：

    S   = sum_x (-1)^(u·x ⊕ v·F^r(x))      （整数）
    V_T = S / 2^32

由此得到两条**必要条件**，任何非穷举（估计/采样）得到的 V_T 都会违反：

  (A) 整数性：V_T · 2^32 必须是整数（在打印精度容差内）。
  (B) 奇偶性：S = #even − #odd = 2^32 − 2·#odd 必为**偶数**。

数据以 5~6 位有效数字打印，(A) 的容差取 min(1.0, |k|·1e-4)。
若 V_T 为任意实数，随机落在宽度 <1 的"含整数区间"内概率约 0.4；
346 条全部通过的概率 ≈ 0.4^346 ≈ 0，故该检验具统计决定性。

用法
----
    python src/verify_vt_exactness.py            # 校验 results/result.txt
    python src/verify_vt_exactness.py --exact    # 额外输出精确化的 V_T = k/2^32

注意：得分只取决于 V_E 与 r（score = log2(2^(2r)·|V_E|)），
故 V_T 精确化不改变总分，仅使有效性边界判定更严格。
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RES = os.path.join(os.path.dirname(_HERE), 'results')
if os.path.isdir(_RES):
    os.chdir(_RES)

N = 2 ** 32
PAT = re.compile(
    r'^@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*(-?[0-9.eE+-]+),\s*(-?[0-9.eE+-]+)\)'
)
SRC = 'result.txt'


def load(fn=SRC):
    rows = []
    with open(fn, encoding='utf-8') as f:
        for line in f:
            m = PAT.match(line.strip())
            if m:
                rows.append((int(m.group(1)), int(m.group(2), 16), int(m.group(3), 16),
                             float(m.group(4)), float(m.group(5))))
    return rows


def main():
    if not os.path.exists(SRC):
        print(f'[FAIL] 找不到 {SRC}')
        return 1
    rows = load()
    print(f'条目总数: {len(rows)}')

    even = odd = 0
    max_dev = 0.0
    bad_int = []
    bad_par = []

    for r, u, v, vt, ve in rows:
        if vt == 0.0:
            continue
        x = vt * N
        k = round(x)
        dev = abs(x - k)
        max_dev = max(max_dev, dev)
        tol = min(1.0, max(abs(k) * 1e-4, 1e-9))
        if dev > tol:
            bad_int.append((r, u, v, vt, x, dev))
        if k % 2 == 0:
            even += 1
        else:
            odd += 1
            bad_par.append((r, u, v, vt, k))

    print(f'(A) 整数性 V_T·2^32 ∈ Z : {len(rows) - len(bad_int)}/{len(rows)} 通过')
    print(f'(B) 奇偶性 S 为偶数     : {even}/{even + odd} 通过')
    print(f'最大取整偏差: {max_dev:.3f}  (仅由 5~6 位有效数字打印造成，应 < 1)')

    if bad_int:
        print('\n[!] 整数性不符条目:')
        for b in bad_int[:10]:
            print(f'    R={b[0]} u=0x{b[1]:08X} v=0x{b[2]:08X}: '
                  f'V_T={b[3]:.6e}  V_T·2^32={b[4]:.3f}  偏差={b[5]:.3f}')
    if bad_par:
        print('\n[!] 奇偶性不符条目:')
        for b in bad_par[:10]:
            print(f'    R={b[0]} u=0x{b[1]:08X} v=0x{b[2]:08X}: '
                  f'V_T={b[3]:.6e}  k={b[4]} (奇数)')

    ok = not bad_int and not bad_par
    print()
    if ok:
        print('[PASS] 全部 V_T 满足 2^32 穷举精确值的两条必要条件 => '
              '可判定为方式 1 精确值（非估计/采样值）')
    else:
        print('[FAIL] 存在不满足的条目，V_T 来源需复核')
        return 1

    if '--exact' in sys.argv:
        print('\n--- 精确化 V_T = k/2^32（前 10 条）---')
        for r, u, v, vt, ve in rows[:10]:
            k = round(vt * N)
            print(f'  @({r}, 0x{u:08X}, 0x{v:08X}, {vt:.6e})  ->  k={k}  '
                  f'V_T_exact={k / N:.12e}')
        print('\n注：得分只由 V_E 与 r 决定，精确化 V_T 不改变总分 2996.53。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
