#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import tempfile
import subprocess
import shutil

def convert_obj_to_glb(obj_path, output_path=None):
    """
    将OBJ文件转换为GLB格式
    
    Args:
        obj_path: OBJ文件路径
        output_path: 输出GLB文件路径，如果为None则使用相同目录和文件名
    
    Returns:
        转换后的GLB文件路径，如果转换失败则返回None
    """
    # 确保输入路径是绝对路径
    obj_path = os.path.abspath(obj_path)
    
    # 如果未指定输出路径，则使用相同的目录和文件名
    if output_path is None:
        obj_dir = os.path.dirname(obj_path)
        obj_name = os.path.splitext(os.path.basename(obj_path))[0]
        output_path = os.path.join(obj_dir, f"{obj_name}.glb")
    
    # 创建一个临时脚本文件
    script_path = None
    try:
        # 准备Blender脚本内容
        script_content = '''
import bpy
import os

# 清除场景中的所有对象
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 导入OBJ文件
obj_path = r"{0}"
bpy.ops.import_mesh.obj(filepath=obj_path)

# 导出为GLB
output_path = r"{1}"
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_texcoords=True,
    export_normals=True,
    export_materials=True
)
print(f"成功将OBJ转换为GLB: {{output_path}}")
'''.format(obj_path, output_path)

        # 创建一个临时文件并写入脚本内容
        fd, script_path = tempfile.mkstemp(suffix='.py')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 运行Blender脚本
        blender_cmd = ["blender", "--background", "--python", script_path]
        print(f"执行命令: {' '.join(blender_cmd)}")
        
        # 使用subprocess.run并捕获输出
        result = subprocess.run(
            blender_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8', 
            errors='replace'
        )
        
        if result.returncode != 0:
            print(f"转换失败，Blender返回错误代码: {result.returncode}")
            print(f"错误信息: {result.stderr}")
            return None
        
        # 检查输出文件是否存在
        if not os.path.exists(output_path):
            print(f"转换失败，输出文件不存在: {output_path}")
            return None
        
        print(f"成功将 {obj_path} 转换为 {output_path}")
        return output_path
        
    finally:
        # 删除临时脚本
        if script_path and os.path.exists(script_path):
            try:
                os.unlink(script_path)
            except Exception as e:
                print(f"警告: 无法删除临时脚本 {script_path}: {e}")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='将OBJ文件转换为GLB格式')
    parser.add_argument('obj_path', help='OBJ文件路径')
    parser.add_argument('--output', '-o', help='输出GLB文件路径')
    
    args = parser.parse_args()
    
    # 转换文件
    convert_obj_to_glb(args.obj_path, args.output)

if __name__ == "__main__":
    main()
