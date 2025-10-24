#!/bin/bash
# ============================================
# 批量测试脚本 v6.2.3
# 功能：遍历多个目录并行执行分析
# 作者: DevinNelly8
# 日期: 2025-10-24
# ============================================

# ==================== 配置区 ====================
PYTHON_SCRIPT="$(dirname $0)/main.py"
MAX_PARALLEL=4  # 并行任务数
OUTPUT_ROOT="./batch_results_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${OUTPUT_ROOT}/logs"

# ==================== 函数定义 ====================

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  批量配位数分析工具 v6.2.3                                  ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

analyze_directory() {
    local DIR="$1"
    local INDEX="$2"
    local DIR_NAME=$(basename "$DIR")
    local OUTPUT_DIR="${OUTPUT_ROOT}/${DIR_NAME}"
    local LOG_FILE="${LOG_DIR}/${DIR_NAME}.log"
    local STATUS_FILE="${LOG_DIR}/${DIR_NAME}.status"
    
    echo "START" > "$STATUS_FILE"
    
    {
        echo "============================================"
        echo "任务 #${INDEX}: $DIR_NAME"
        echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "============================================"
        
        cd "$DIR" || { echo "ERROR: 无法进入目录"; echo "FAILED" > "$STATUS_FILE"; exit 1; }
        
        # 执行Python脚本
        python3 "$PYTHON_SCRIPT" --auto --output-dir "$OUTPUT_DIR"
        
        EXIT_CODE=$?
        
        echo ""
        echo "============================================"
        echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "退出码: $EXIT_CODE"
        echo "============================================"
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "SUCCESS" > "$STATUS_FILE"
        else
            echo "FAILED" > "$STATUS_FILE"
        fi
        
    } > "$LOG_FILE" 2>&1
}

export -f analyze_directory
export PYTHON_SCRIPT OUTPUT_ROOT LOG_DIR

# ==================== 主程序 ====================

print_header

# 解析参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <目录1> [目录2] [目录3] ..."
    echo ""
    echo "示例:"
    echo "  $0 dir1 dir2 dir3"
    echo "  $0 ./data/*/"
    exit 1
fi

# 收集目标目录
TARGET_DIRS=()
for arg in "$@"; do
    if [ -d "$arg" ]; then
        TARGET_DIRS+=("$arg")
    else
        echo "⚠ 跳过无效目录: $arg"
    fi
done

if [ ${#TARGET_DIRS[@]} -eq 0 ]; then
    echo "✗ 错误: 未找到有效目录"
    exit 1
fi

echo "【目标目录】(共${#TARGET_DIRS[@]}个)"
printf '%s\n' "${TARGET_DIRS[@]}" | nl
echo ""

# 创建输出目录
mkdir -p "$LOG_DIR"

echo "【开始批量处理】"
echo "输出根目录: $OUTPUT_ROOT"
echo "日志目录: $LOG_DIR"
echo ""

START_TIME=$(date +%s)

# 并行执行
INDEX=1
for dir in "${TARGET_DIRS[@]}"; do
    analyze_directory "$dir" "$INDEX" &
    
    # 控制并行数
    if (( INDEX % MAX_PARALLEL == 0 )); then
        wait
    fi
    
    INDEX=$((INDEX + 1))
done

wait

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ==================== 统计结果 ====================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  批量处理完成                                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

SUCCESS_COUNT=$(grep -l "SUCCESS" ${LOG_DIR}/*.status 2>/dev/null | wc -l)
FAILED_COUNT=$(grep -l "FAILED" ${LOG_DIR}/*.status 2>/dev/null | wc -l)
TOTAL_COUNT=${#TARGET_DIRS[@]}

echo "【统计结果】"
echo "  总任务数: $TOTAL_COUNT"
echo "  成功: $SUCCESS_COUNT"
echo "  失败: $FAILED_COUNT"
echo "  用时: ${ELAPSED}s"
echo ""

if [ $FAILED_COUNT -gt 0 ]; then
    echo "【失败任务】"
    grep -l "FAILED" ${LOG_DIR}/*.status 2>/dev/null | while read status_file; do
        dir_name=$(basename "$status_file" .status)
        echo "  ✗ $dir_name"
    done
fi

echo ""
echo "结果保存至: $OUTPUT_ROOT"

if [ $FAILED_COUNT -eq 0 ]; then
    echo "✓ 所有任务成功完成！"
    exit 0
else
    echo "⚠ 部分任务失败"
    exit 1
fi