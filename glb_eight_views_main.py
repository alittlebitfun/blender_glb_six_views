#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import subprocess
import time
from PIL import Image, ImageDraw, ImageFont

def render_with_blender(model_path, output_dir=None, resolution=1000):
    """
    调用Blender渲染模型的八个视图
    
    Args:
        model_path: 模型文件路径
        output_dir: 输出目录，如果为None则使用模型所在目录
        resolution: 渲染分辨率
        
    Returns:
        dict: 包含八个视图路径的字典
    """
    print(f"开始渲染模型: {model_path}")
    
    # 确保模型路径是绝对路径
    model_path = os.path.abspath(model_path)
    
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.dirname(model_path)
    else:
        output_dir = os.path.abspath(output_dir)
    
    # 获取模型名称（不带扩展名）
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    
    # 获取Blender脚本路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    blender_script = os.path.join(script_dir, "blender_eight_views.py")
    
    # 构建Blender命令
    blender_cmd = [
        "blender",
        "--background",
        "--python", blender_script,
        "--",
        model_path,
        "--output", output_dir,
        "--resolution", str(resolution)
    ]
    
    # 执行Blender命令
    try:
        print("执行Blender渲染命令...")
        subprocess.run(blender_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Blender渲染失败: {e}")
        return None
    except FileNotFoundError:
        print("找不到Blender，请确保Blender已安装并添加到PATH环境变量中")
        return None
    
    # 构建视图路径
    view_types = ['正面', '左视图', '背面', '等轴测无材质', '俯视图', '底视图', '右视图', 'UV贴图']
    view_paths = {}
    
    for view_type in view_types:
        view_path = os.path.join(output_dir, f"{model_name}_{view_type}.png")
        if os.path.exists(view_path):
            view_paths[view_type] = view_path
        else:
            print(f"警告: 找不到视图图像 {view_path}")
    
    return view_paths

def combine_views(view_paths, output_path, model_name):
    """
    将八个视图图像合并为一个图像，并添加标签
    
    Args:
        view_paths: 包含八个视图路径的字典
        output_path: 输出图像路径
        model_name: 模型名称，用于标题
    """
    print("开始合并视图图像...")
    
    # 检查是否有所有需要的视图
    required_views = ['正面', '左视图', '背面', '等轴测无材质', '俯视图', '底视图', '右视图', 'UV贴图']
    for view in required_views:
        if view not in view_paths or not os.path.exists(view_paths[view]):
            print(f"错误: 缺少视图 {view} 或文件不存在")
            return None
    
    # 加载所有视图图像
    view_images = {}
    for view_type, path in view_paths.items():
        try:
            img = Image.open(path)
            # 确保图像有白色背景（转换透明背景为白色）
            if img.mode == 'RGBA':
                background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 使用alpha通道作为蒙版
                img = background.convert('RGB')
            view_images[view_type] = img
            print(f"已加载视图: {view_type}, 尺寸: {img.size}")
        except Exception as e:
            print(f"加载视图 {view_type} 时出错: {e}")
            return None
    
    # 获取单个视图的尺寸
    img_width, img_height = next(iter(view_images.values())).size
    
    # 设置间距和标题高度
    padding = 10
    title_height = 40
    label_height = 30
    
    # 计算最终图像的尺寸
    total_width = img_width * 4 + padding * 5
    total_height = (img_height + label_height) * 2 + padding * 3 + title_height
    
    # 创建一个新的白色背景图像
    composite = Image.new('RGB', (total_width, total_height), (255, 255, 255))
    draw = ImageDraw.Draw(composite)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # 尝试使用系统字体
        font_path = "C:\\Windows\\Fonts\\simhei.ttf"  # 黑体
        title_font = ImageFont.truetype(font_path, 36)
        label_font = ImageFont.truetype(font_path, 24)
    except IOError:
        # 如果找不到字体文件，使用默认字体
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
    
    # 绘制标题
    title_width = draw.textlength(model_name, font=title_font)
    draw.text(
        ((total_width - title_width) // 2, padding // 2),
        model_name,
        font=title_font,
        fill=(0, 0, 0)
    )
    
    # 定义每个视图的位置（按照指定的布局）
    positions = {
        '正面': (padding, title_height + padding),
        '左视图': (padding * 2 + img_width, title_height + padding),
        '背面': (padding * 3 + img_width * 2, title_height + padding),
        '等轴测无材质': (padding * 4 + img_width * 3, title_height + padding),
        '俯视图': (padding, title_height + padding * 2 + img_height + label_height),
        '底视图': (padding * 2 + img_width, title_height + padding * 2 + img_height + label_height),
        '右视图': (padding * 3 + img_width * 2, title_height + padding * 2 + img_height + label_height),
        'UV贴图': (padding * 4 + img_width * 3, title_height + padding * 2 + img_height + label_height)
    }
    
    # 放置每个视图并添加标签
    for view_type, pos in positions.items():
        # 放置图像
        composite.paste(view_images[view_type], (pos[0], pos[1] + label_height))
        
        # 添加标签
        label_width = draw.textlength(view_type, font=label_font)
        label_x = pos[0] + (img_width - label_width) // 2
        label_y = pos[1] + (label_height - 24) // 2  # 24是字体大小
        draw.text(
            (label_x, label_y),
            view_type,
            font=label_font,
            fill=(0, 0, 0)
        )
    
    # 保存合成图像为JPG格式
    composite.save(output_path, format='JPEG', quality=95)
    print(f"合成图像已保存到: {output_path}")
    
    return output_path

def process_model(model_path, output_path=None, resolution=1000, keep_temp=False):
    """
    处理模型：渲染八个视图并合并为一个图像
    
    Args:
        model_path: 模型文件路径
        output_path: 输出图像路径，如果为None则使用模型名称_eight_views.jpg
        resolution: 渲染分辨率
        keep_temp: 是否保留临时文件
    """
    start_time = time.time()
    
    # 确保模型路径是绝对路径
    model_path = os.path.abspath(model_path)
    
    # 设置输出路径
    if output_path is None:
        model_dir = os.path.dirname(model_path)
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        output_path = os.path.join(model_dir, f"{model_name}_eight_views.jpg")
    
    # 渲染八个视图
    view_paths = render_with_blender(model_path, resolution=resolution)
    
    if not view_paths:
        print("渲染失败，无法继续")
        return None
    
    # 检查所有视图是否存在
    missing_views = []
    for view_type in ['正面', '左视图', '背面', '等轴测无材质', '俯视图', '底视图', '右视图', 'UV贴图']:
        if view_type not in view_paths or not os.path.exists(view_paths[view_type]):
            missing_views.append(view_type)
    
    if missing_views:
        print(f"警告: 以下视图缺失: {', '.join(missing_views)}")
    
    # 直接在主程序中合并视图，不调用外部脚本
    print("开始合并视图图像...")
    result = combine_views(view_paths, output_path, os.path.splitext(os.path.basename(model_path))[0])
    
    # 清理临时文件
    if not keep_temp and result:
        for path in view_paths.values():
            if os.path.exists(path):
                os.remove(path)
                print(f"已删除临时文件: {path}")
    
    # 计算总处理时间
    elapsed_time = time.time() - start_time
    print(f"总处理时间: {elapsed_time:.2f} 秒")
    
    return result

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='渲染GLB模型的八个视图并合并为一个图像')
    parser.add_argument('model_path', help='GLB模型文件路径')
    parser.add_argument('--output', '-o', help='输出图像路径')
    parser.add_argument('--resolution', '-r', type=int, default=1000, help='渲染分辨率')
    parser.add_argument('--keep-temp', '-k', action='store_true', help='保留临时文件')
    
    args = parser.parse_args()
    
    # 处理模型
    process_model(args.model_path, args.output, args.resolution, args.keep_temp)

if __name__ == "__main__":
    main()
