# Enhanced Coordination Analysis v6.2.3

**发布日期**: 2025-10-24  
**作者**: DevinNelly8  
**仓库**: https://github.com/DevinNelly8/q6

---

## 🎯 v6.2.3 核心改进

### ✨ 主要特性

| 特性 | v6.2.2 | v6.2.3 | 改进 |
|------|--------|--------|------|
| **配位数计算** | 硬截断 | PLUMED平滑 | ✅ 更物理 |
| **GCN描述符** | ❌ 无 | ✅ 4种变体 | ✅ 新增 |
| **全局Q6** | Metal-only | PtSnO + Metal | ✅ 更全面 |
| **相关性** | - | wGCN: -0.568*** | ✅ 最强 |

### 🔬 GCN描述符详情

```python
# 1. 标准GCN
gcn_loc = Σ exp(-r/0.3)

# 2. 加权GCN (⭐ 相关性-0.568***)
w_gcn_loc = Σ[w_Pt·exp(-r_Pt/0.3) + w_Sn·exp(-r_Sn/0.3)]
  其中: w_Pt=1.0, w_Sn=2.0

# 3. Sn加权GCN (相关性0.412***)
sn_w_gcn_loc = 0.8·N_Pt(2.0-2.8Å) + 2.5·N_Sn(2.0-2.8Å)

# 4. 壳层GCN
shell_gcn_loc = Σ[w_shell·N_shell]
```

---

## 📦 安装

### 依赖项

```bash
pip install numpy pandas scipy MDAnalysis
```

### Python版本要求

- Python >= 3.7

---

## 🚀 快速开始

### 1. 单文件分析

```bash
cd v6_2_3
python main.py --auto --output-dir ./results
```

### 2. 自定义参数

```bash
python main.py sampling.xyz \
    --rcut-pt-pt 2.9 \
    --rcut-pt-sn 3.1 \
    --q6-cutoff 3.6 \
    --output-dir ./my_results
```

### 3. 批量测试

```bash
# 测试多个目录
chmod +x batch_test.sh
./batch_test.sh dir1 dir2 dir3

# 使用通配符
./batch_test.sh ../data/*/
```

### 4. 结果验证

```bash
python validate_results.py ./results
python validate_results.py ./batch_results_20251024_055823
```

---

## 📊 输出文件说明

### 主要输出

```
output_dir/
├── coordination_time_series.csv          # ⭐ 核心数据
│   ├── frame, time_ps                    # 时间信息
│   ├── Pt_cn_total, Pt_cn_Pt_Pt         # 配位数
│   ├── Pt_gcn_loc, Pt_w_gcn_loc ⭐      # GCN（新增）
│   ├── Pt_sn_w_gcn_loc, Pt_shell_gcn_loc
│   ├── Pt_q6, Pt_q4, Pt_structure       # Q6/Q4
│   └── Sn_... (Sn原子的对应数据)
│
├── cluster_global_q6_time_series.csv
│   ├── cluster_all_q6_global ⭐         # PtSnO全局Q6（新增）
│   ├── cluster_metal_q6_global          # Pt+Sn全局Q6
│   ├── pt_q6_global                     # Pt全局Q6
│   └── sn_q6_global                     # Sn全局Q6
│
├── cluster_geometry_time_series.csv
├── element_comparison.csv
└── detection_info.txt
```

### 数据示例

**coordination_time_series.csv** (前5列):
```csv
frame,time_ps,Pt_cn_total,Pt_w_gcn_loc,Pt_q6
0,0.0,8.245,15.632,0.4523
10,10.0,8.137,15.428,0.4489
20,20.0,8.312,15.751,0.4556
```

---

## 🔧 配置参数

### 快速修改配置

编辑 `modules/config.py`:

```python
# 启用/禁用GCN
GCN = {
    'enable': True,  # False to disable
    ...
}

# 修改Sn权重
GCN['weighted']['sn_weight'] = 2.5  # 默认2.0

# 修改PLUMED参数
COORDINATION['plumed']['pt_pt']['R0'] = 2.8  # 默认2.9
```

### 命令行覆盖

```bash
python main.py --rcut-pt-pt 2.95 --disable-gcn
```

---

## 📈 相关性分析结果

基于实际数据（96帧，Pt-Sn团簇）：

| 描述符 | 相关系数(R) | P值 | 显著性 | 解释 |
|--------|-------------|-----|--------|------|
| **pt6_wgcn** | **-0.568** | 4.5e-07 | *** | 加权GCN（最强） |
| **Pt6_sgcn** | **0.412** | 4.8e-04 | *** | Sn加权GCN |
| Pt4_wgcn | -0.356 | 2.9e-03 | ** | 中等相关 |
| Pt0_gcn_loc | 0.325 | 6.9e-03 | ** | 标准GCN |

**关键发现**:
- ✅ wGCN是**最强**吸附能描述符
- ✅ Sn的权重对预测至关重要
- ✅ 壳层分辨提高了精度

---

## 🧪 测试

### 模块单元测试

```bash
# 测试配位数模块
python modules/coordination_module.py

# 测试Q6模块
python modules/q6_module.py

# 测试几何分析
python modules/geometry_module.py
```

### 完整集成测试

```bash
# 使用测试数据
python main.py --auto tests/test_data.xyz --output-dir tests/output

# 验证结果
python validate_results.py tests/output
```

---

## 📚 模块架构

```
v6_2_3/
├── modules/
│   ├── __init__.py
│   ├── config.py              # 配置参数
│   ├── coordination_module.py # ⭐ 配位数+GCN
│   ├── q6_module.py           # Q6/Q4计算
│   ├── geometry_module.py     # 几何分析
│   └── global_q6_module.py    # 全局Q6
├── main.py                    # 主脚本
├── batch_test.sh              # 批量测试
├── validate_results.py        # 结果验证
└── README.md                  # 本文档
```

---

## 🔬 理论背景

### PLUMED平滑切换函数

```
sw(r) = [1 - ((r-D0)/R0)^NN] / [1 - ((r-D0)/R0)^MM]
```

**优势**:
- 避免硬截断的不连续性
- 物理上更合理
- 数值稳定性更好

### 广义配位数（GCN）

传统配位数只考虑"在/不在"，GCN引入连续权重：

```
GCN = Σ w_i · f(r_i)
```

其中 `f(r)` 是距离衰减函数，`w_i` 是元素权重。

**为什么Sn权重更高？**
- Sn原子对Pt的电子结构影响更显著
- Sn-Pt相互作用强于Pt-Pt
- 实验和DFT计算均支持此结论

---

## 🐛 故障排除

### 常见问题

**Q: 找不到模块**
```bash
# 确保在v6_2_3目录下运行
cd v6_2_3
python main.py --auto
```

**Q: GCN全为0**
```python
# 检查config.py
GCN['enable'] = True  # 确保已启用
```

**Q: 结果与参考代码不同**
```bash
# v6.2.3使用平滑函数，数值会略有不同
# 这是正常的，且更准确
```

---

## 📖 引用

如果你使用了此代码，请引用：

```bibtex
@software{enhanced_cn_analysis_v623,
  author = {DevinNelly8},
  title = {Enhanced Coordination Analysis v6.2.3},
  year = {2025},
  url = {https://github.com/DevinNelly8/q6}
}
```

---

## 🔗 相关链接

- [GitHub仓库](https://github.com/DevinNelly8/q6)
- [问题反馈](https://github.com/DevinNelly8/q6/issues)
- [PLUMED文档](https://www.plumed.org)

---

## 📝 更新日志

### v6.2.3 (2025-10-24)
- ✅ 使用PLUMED平滑切换函数
- ✅ 新增4种GCN描述符
- ✅ 全局Q6包含所有原子
- ✅ 模块化架构重构

### v6.2.2 (2025-10-24)
- 全局Q6包含PtSnO
- 简化输出结构

### v6.2.1 (2025-10-23)
- 预处理bug修复
- 多帧验证

---

## 🤝 贡献

欢迎贡献！请：

1. Fork仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

---

## 📧 联系方式

- **作者**: DevinNelly8
- **GitHub**: [@DevinNelly8](https://github.com/DevinNelly8)
- **Email**: 通过GitHub联系

---

**License**: MIT

**最后更新**: 2025-10-24 05:58 UTC