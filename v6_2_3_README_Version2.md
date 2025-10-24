# Enhanced Coordination Analysis v6.2.3

**发布日期**: 2025-10-24  
**作者**: DevinNelly8

## 🎯 v6.2.3 关键改进

### ✅ 主要更新

1. **PLUMED平滑切换函数** 🌟
   - 替代硬截断配位数计算
   - 更物理合理，结果更连续

2. **4种GCN变体** 🌟
   ```
   - 标准GCN (gcn_loc)
   - 加权GCN (w_gcn_loc) ← 相关性-0.568***
   - Sn加权GCN (sn_w_gcn_loc) ← 相关性0.412***
   - 壳层GCN (shell_gcn_loc)
   ```

3. **全局Q6包含所有原子**
   - `cluster_all_q6_global`: Pt+Sn+O
   - `cluster_metal_q6_global`: Pt+Sn

4. **简化输出结构**
   - 统一CSV文件（无子文件夹）
   - 易于后续分析

5. **模块化架构**
   - 易于测试和维护
   - 独立模块可复用

## 📦 安装依赖

```bash
pip install numpy pandas scipy MDAnalysis
```

## 🚀 快速开始

### 基础用法

```bash
python main.py --auto --output-dir ./results
```

### 自定义参数

```bash
python main.py --auto \
    --rcut-pt-pt 2.9 \
    --rcut-pt-sn 3.1 \
    --q6-cutoff 3.6 \
    --output-dir ./my_results
```

### 批量测试

```bash
# 测试多个目录
./batch_test.sh dir1 dir2 dir3

# 使用通配符
./batch_test.sh ./data/*/
```

## 📊 输出文件

```
output_dir/
├── coordination_time_series.csv     # 统一的配位数文件
│   ├── Pt_cn_total, Pt_cn_Pt_Pt, Pt_cn_Pt_Sn
│   ├── Pt_gcn_loc, Pt_w_gcn_loc, Pt_sn_w_gcn_loc ← ⭐新增
│   └── Sn_cn_total, Sn_cn_Sn_Sn, Sn_cn_Sn_Pt
│
├── cluster_global_q6_time_series.csv
│   ├── cluster_all_q6_global ← ⭐新增(PtSnO)
│   ├── cluster_metal_q6_global (Pt+Sn)
│   ├── pt_q6_global
│   └── sn_q6_global
│
├── cluster_geometry_time_series.csv
└── element_comparison.csv
```

## 🔧 配置参数

编辑 `modules/config.py` 修改参数：

```python
# 配位数参数
COORDINATION = {
    'rcut_pt_pt': 3.0,
    'plumed': {
        'pt_pt': {'R0': 2.9, 'NN': 6, 'MM': 12}
    }
}

# GCN参数
GCN = {
    'enable': True,  # 启用/禁用GCN计算
    'weighted': {
        'pt_weight': 1.0,
        'sn_weight': 2.0  # Sn权重
    }
}
```

## 📖 模块说明

| 模块 | 功能 | 关键函数 |
|------|------|---------|
| `coordination_module.py` | 配位数+GCN | `calc_bond_specific_cn_smooth()` |
| `q6_module.py` | Q6/Q4序参量 | `calc_q6_fast()`, `calc_q4_fast()` |
| `geometry_module.py` | 几何分析 | `calc_geometry_statistics()` |
| `global_q6_module.py` | 全局Q6 | `calc_cluster_analysis()` |

## 🧪 测试

```bash
# 测试单个模块
python modules/coordination_module.py

# 完整测试
python tests/test_all.py
```

## 📚 相关性分析结果

基于你的数据分析：

```
描述符              相关系数(R)    P值           显著性
----------------------------------------------------------
pt6_wgcn           -0.568       4.465e-07     ***
Pt6_sgcn            0.412       4.794e-04     ***
Pt4_wgcn           -0.356       2.891e-03     **
```

**结论**: wGCN (加权广义配位数) 与吸附能相关性最强！

## 🔗 版本历史

- **v6.2.3** (2025-10-24): PLUMED+GCN+模块化
- **v6.2.2** (2025-10-24): 全局Q6包含所有原子
- **v6.2.1** (2025-10-23): 预处理bug修复
- **v6.2.0** (2025-10-23): 初始版本

## 📧 联系方式

- 作者: DevinNelly8
- GitHub: https://github.com/DevinNelly8/q6