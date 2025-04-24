#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import time
from glb_eight_views_main import process_model

def process_directory(directory_path, output_dir=None, resolution=1000, keep_temp=False):
    """
    批量处理指定目录下的所有3D模型文件
    
    Args:
        directory_path: 包含3D模型文件的目录路径
        output_dir: 输出目录，如果为None则使用模型所在目录
        resolution: 渲染分辨率
        keep_temp: 是否保留临时文件
    """
    # 确保目录路径是绝对路径
    directory_path = os.path.abspath(directory_path)
    
    # 如果指定了输出目录，确保它存在
    if output_dir:
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
    
    # 查找目录中的所有支持的3D模型文件
    model_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(('.glb', '.gltf', '.obj')):
                model_files.append(os.path.join(root, file))
    
    if not model_files:
        print(f"在目录 {directory_path} 中未找到支持的3D模型文件")
        return
    
    print(f"找到 {len(model_files)} 个3D模型文件待处理")
    
    # 处理每个3D模型文件
    successful = 0
    failed = 0
    
    for i, model_file in enumerate(model_files, 1):
        print(f"\n[{i}/{len(model_files)}] 处理文件: {os.path.basename(model_file)}")
        
        # 设置输出路径
        if output_dir:
            model_name = os.path.splitext(os.path.basename(model_file))[0]
            output_path = os.path.join(output_dir, f"{model_name}.jpg")
        else:
            model_dir = os.path.dirname(model_file)
            model_name = os.path.splitext(os.path.basename(model_file))[0]
            output_path = os.path.join(model_dir, f"{model_name}.jpg")
        
        try:
            # 直接处理模型文件
            result = process_model(
                model_file, 
                output_path=output_path, 
                resolution=resolution, 
                keep_temp=keep_temp
            )
            
            if result:
                print(f"成功处理: {os.path.basename(model_file)} -> {result}")
                successful += 1
            else:
                print(f"处理失败: {os.path.basename(model_file)}")
                failed += 1
        except Exception as e:
            print(f"处理 {os.path.basename(model_file)} 时出错: {e}")
            failed += 1
    
    # 打印处理结果统计
    print(f"\n批处理完成: 总共 {len(model_files)} 个文件, 成功 {successful} 个, 失败 {failed} 个")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='批量处理3D模型：渲染八个视图并合并为一个图像')
    parser.add_argument('directory_path', help='包含3D模型文件的目录路径')
    parser.add_argument('--output-dir', '-o', help='输出目录，默认为模型所在目录')
    parser.add_argument('--resolution', '-r', type=int, default=1000, help='渲染分辨率')
    parser.add_argument('--keep-temp', '-k', action='store_true', help='保留临时文件')
    
    args = parser.parse_args()
    
    # 处理目录
    start_time = time.time()
    process_directory(args.directory_path, args.output_dir, args.resolution, args.keep_temp)
    elapsed_time = time.time() - start_time
    print(f"总批处理时间: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    main()
