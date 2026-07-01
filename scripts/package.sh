#!/bin/bash

# 需求分析技能打包脚本
# 用于创建可导入到其他工作区的技能包

SKILL_NAME="requirement-analysis"
VERSION="1.0.0"
SKILL_DIR="${SKILL_NAME}-${VERSION}"
OUTPUT_FILE="${SKILL_NAME}-${VERSION}.tar.gz"

echo "=== 需求分析技能打包工具 ==="
echo ""

# 检查技能目录是否存在
if [ ! -d "$SKILL_DIR" ]; then
    echo "错误: 技能目录不存在: $SKILL_DIR"
    echo "请确保在包含技能目录的父目录中运行此脚本"
    exit 1
fi

echo "技能目录: $SKILL_DIR"
echo "输出文件: $OUTPUT_FILE"
echo ""

# 检查必需文件
echo "检查必需文件..."
REQUIRED_FILES=("_meta.json" "SKILL.md" "package.json" "README.md" "package.sh")
MISSING_FILES=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$SKILL_DIR/$file" ]; then
        echo "  缺失: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    else
        echo "  $file 存在"
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo ""
    echo "错误: 缺失 $MISSING_FILES 个必需文件"
    exit 1
fi

echo ""
echo "所有必需文件检查通过"
echo ""

# 创建压缩包
echo "正在创建压缩包..."
tar -czf "$OUTPUT_FILE" "$SKILL_DIR"

if [ $? -eq 0 ]; then
    echo "打包成功: $OUTPUT_FILE"
    echo ""

    # 显示文件大小
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "文件大小: $FILE_SIZE"
    echo ""

    # 显示内容列表
    echo "包含文件:"
    tar -tzf "$OUTPUT_FILE" | sed 's/^/  /'
    echo ""

    echo "打包完成！"
    echo ""
    echo "使用说明:"
    echo "  1. 将 $OUTPUT_FILE 复制到目标机器"
    echo "  2. 解压到技能目录:"
    echo "     tar -xzf $OUTPUT_FILE -C ~/.claude/skills/"
    echo "  3. (可选) 安装增强依赖:"
    echo "     cd ~/.claude/skills/$SKILL_DIR"
    echo "     pip install python-docx openpyxl"
    echo "  4. 在 Claude Code 中使用:"
    echo "     说: '进行需求分析'"
else
    echo "打包失败"
    exit 1
fi
