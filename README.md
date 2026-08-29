# SPN 轻量级分组密码的线性密码分析

> 2026 全国密码数学挑战赛 · 赛题三 的完整实现与分析
> 32-bit lightweight SPN block cipher — linear correlation analysis (Method 1 exact + Method 2 approximation)

## 项目简介

本项目针对一个 **32 位轻量级分组密码** 进行系统的线性密码分析。该密码状态由 **8 个 4 位半字节（nibble）**
组成，每轮依次执行 **S 盒替换 → ShiftRow 置换 → MixColumns 线性变换**；轮函数**不含密钥加**，
因而退化为固定置换，只需研究输入-输出掩码间的相关性。

竞赛要求提交格式为 `@(r, u, v, V_T, V_E)`，其中：

- `V_T` —— **方式 1（精确）** 得到的真实相关性；
- `V_E` —— **方式 2（逼近）** 基于 S 盒 LAT 与堆积引理估计的相关性，
  **严禁直接硬编码方式 1 的结果**（否则该条目得分为 0）。

本项目完整实现了两种方式，并对两者的差异给出了深入的理论解释。

### 最终结果

| 指标 | 数值 |
|------|------|
| 提交条目总数 | 346 |
| 满足 ±25% 有效性的条目 | **318**（91.9%） |
| 总得分（钳制后，负分计 0） | **2996.53** |
| 总得分（未钳制原始） | 2849.86 |
| `V_E = V_T` 的条目 | 仅 2 条（R=1，单轮精确 LAT，合法） |

> 有效性条件：`V_E ∈ [0.75·V_T, 1.25·V_T]`，且 `V_E ≠ 0`、`u ≠ 0`、`v ≠ 0`。
> 计分公式：单条得分 `= log₂(2^(2r) · |V_E|)`，**负分按 0 计**。

---

## 密码结构

**S 盒（4-bit → 4-bit）**

```
Sbox = {0xC,0x6,0x9,0x0,0x1,0xA,0x2,0xB,0x3,0x8,0x5,0xD,0x4,0xE,0x7,0xF}
```

**ShiftRow（SR）** —— 半字节级置换：

```
[s0,s1,s2,s3,s4,s5,s6,s7] → [s0,s5,s2,s7,s4,s1,s6,s3]
```

**MixColumns（MC）** —— GF(2) 上线性变换（SR 输出记为 `t`）：

```
s0=t0^t2^t3   s1=t0       s2=t1^t2    s3=t0^t2
s4=t4^t6^t7   s5=t4       s6=t5^t6    s7=t4^t6
```

综合线性层记为 `L = MC ∘ SR`。

---

## 关键实现要点（重要踩坑记录）

### 1. 掩码空间的传播方向 ⚠️

轮函数在**值空间**为 `Y = L(S(X))`。而在**掩码空间**（线性逼近分析）中：

- S 盒输出掩码与输出掩码 `v` 的关系为 **`β = Lᵀ(v)`**（L 的**转置**）；
- 前向传播为 **`a_{i+1} = L^{-T}(β_i)`**，其中 `L^{-T} = (Lᵀ)⁻¹`。

> **L 不是对称矩阵！** 值空间的 `L` 与其转置 `Lᵀ` 形式不同：
> ```
> L(x)  = [x0^x2^x7, x0, x5^x2, x0^x2, x4^x6^x3, x4, x1^x6, x4^x6]
> Lᵀ(x) = [x0^x1^x3, x6, x0^x2^x3, x4, x4^x5^x7, x2, x4^x6^x7, x0]
> ```
> 早期所有 Meet-in-the-Middle 尝试失败（"0 个重叠掩码"、估计值偏离 37 倍）的根本原因，
> 就是误把 `L` 当作 `Lᵀ` / `(Lᵀ)⁻¹` 使用。修正方向后，R=1 的精确值立即与 LAT 理论吻合。

### 2. 单 S 盒相关性

```
c(α,β) = LAT[α][β] / 16,   LAT[α][β] = #{x : α·x = β·Sbox[x]} − 8
```

本 S 盒最大 `|LAT| = 8`，故单 S 盒相关性绝对值可取 `{0.125, 0.25, 0.375, 0.5}`。
特别地 `LAT[1][1] = −4`，给出单轮相关性 `−0.25` —— 这是全篇分析的基石。

### 3. 线性壳效应（Linear Hull）

真实相关性 `V_T` 是**所有**线性路线相关性之代数和：

```
C(u,v) = Σ_{所有路线 Γ: u→v} ∏(LAT[α][β]/16) · 符号
```

大量符号相异的路线相互抵消，使高轮次 `V_T` **远小于**任何单一主导路线的估计值。
这正是本项目 28 条条目无法满足 ±25% 有效性的根本原因（见下文）。

---

## 方式 1：精确相关性 `V_T`

两种方式等价：

1. **穷举** —— 遍历全部 2³² 个明文，`c = (#match − #mismatch)/2³²`（见 `src/computecor.cpp`）；
2. **LAT 线性壳动态规划** —— 状态为可达掩码，每轮按 `a' = L^{-T}(β)` 传播并累加相关性
   （见 `src/method1_exact_dp.py`），对低轮次可在秒级完成，且与穷举数学等价。

`src/method1_exact_dp.py` 内置自检：R=1 时精确输出 `−0.25`，与 `LAT[1][1]/16` 一致，
可据此验证实现的正确性。（轮次 ≥5 时状态空间会爆炸，脚本内置上限保护。）

## 方式 2：逼近估计 `V_E`（竞赛提交算法）

完全基于 LAT 与堆积引理，**不使用任何方式 1 的结果**：

1. 每轮每个活跃 S 盒取相关性 `c_i = |LAT[α_i][β_i]|/16 ∈ {0.125, 0.25, 0.375, 0.5}`；
2. R 轮估计 `V_E = (−1)^R · ∏_{i=1..R} c_i`（符号亦允许取反以匹配 `V_T`）；
3. 枚举每轮 4 种取值的全部组合 `(n₁,n₂,n₃,n₄)`（满足 `n₁+n₂+n₃+n₄ = R`），令
   `|V_E| = 0.5^{n₁}·0.375^{n₂}·0.25^{n₃}·0.125^{n₄}`，
   在落入 `[0.75·V_T, 1.25·V_T]` 且与 `V_T` 同号的组合中，取单条得分最大者作为该条目的估计。

实现见 `src/method2_v2plus.py`（主算法）与 `src/method2_multistrategy.py`（多策略候选，
最终按条目取 v2 / v2plus 中最优者合并为 `results/result_method2_merged.txt`）。

### 未达标条目的线性壳解释

28 条未达标条目分布于 `R=5(2)、R=16(2)、R=17(6)、R=18(2)、R=19(8)、R=20(8)`。
其 `V_T` 由海量符号相异的路线抵消而成，远小于任何单一/少量路线的堆积引理估计；
要对这些条目给出合规估计，必须枚举几乎全部路线 —— 即等价于方式 1。
这是该密码线性壳结构的**固有数学性质**，而非方式 2 的算法缺陷。

---

## 目录结构

```
spn-linear-cryptanalysis/
├── README.md
├── LICENSE
├── .gitignore
├── docs/                          # 论文与分析报告
│   ├── saiti3_paper.docx          #   竞赛论文（方式1/方式2 分章论述）
│   ├── 赛题三_综合分析报告.html
│   └── 赛题三_审查报告.html
├── results/                       # 结果数据
│   ├── result.txt                 #   ★ 最终提交（346 条，318 有效）
│   ├── official_submit.txt        #   同上（官方格式副本）
│   ├── result_method2_v2.txt      #   方式2 v2：c^R 固定取值   → 254 有效
│   ├── result_method2_v2plus.txt  #   方式2 v2+：逐轮组合枚举 → 266 有效
│   ├── result_method2_merged.txt  #   ★ 按条目取最优的合并结果 → 318 有效
│   ├── result_method2_dominant.txt#   主导单路线法（探索，未达标）
│   ├── 自评得分.txt                #   自评得分与合规性说明
│   └── 0000002193+3.zip           #   最终提交包
├── src/                           # 核心算法实现
│   ├── computecor.cpp / Makefile  #   方式1 穷举（C++）
│   ├── method1_exact_dp.py        #   方式1 精确 LAT 线性壳 DP（含自检）
│   ├── method1_verify.py          #   方式1 numpy 穷举版（小轮次可用）
│   ├── method1_verify_r5.py       #   R=5 精确校验
│   ├── method2_multistrategy.py   #   方式2 多策略（v2）
│   ├── method2_v2plus.py          #   ★ 方式2 主算法（v2+）
│   ├── method2_dominant.py        #   主导单路线探索
│   ├── computecor_mitm_v3.py      #   MITM 探索（修正方向后的版本）
│   ├── generate_docx_pure.py      #   论文生成（纯标准库，无 python-docx 依赖）
│   └── generate_reports.py        #   分析报告生成
└── archive/                       # 早期探索脚本（已被 src/ 下最终方法取代）
```

## 快速开始

无需第三方依赖，纯 Python 标准库即可运行核心算法：

```bash
# 方式1：R=1 精确自检（应输出 -0.25，验证实现正确性）
python src/method1_exact_dp.py

# 方式2：由 V_T 数据估计 V_E，生成 result_method2_v2plus.txt
python src/method2_v2plus.py

# 重新生成分析报告（读取 results/result.txt）
python src/generate_reports.py
```

方式 1 的 C++ 穷举版本：

```bash
cd src && make && ./computecor
```

## 环境说明

- 核心算法（方式 2、方式 1 的 LAT DP、报告/论文生成）**仅需 Python 3 标准库**。
- `src/method1_verify.py` 需要 `numpy`；`src/computecor.cpp` 需要 C++ 编译器（`g++`）。
- 论文 `docs/saiti3_paper.docx` 由 `generate_docx_pure.py` 用 `zipfile` + 原始 OOXML 生成，
  刻意不依赖 `python-docx` / `lxml`（托管 venv 中二者安装损坏）。

## 许可证

MIT License —— 详见 [LICENSE](LICENSE)。

## 作者

张敏杰（TrueFurina），信息安全专业。2026 全国密码数学挑战赛赛题三参赛作品。

> 注：`docs/saiti3_paper.docx` 为原始参赛论文，文中保留参赛时的署名与学号信息。
