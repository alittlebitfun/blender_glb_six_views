import os
import sys
import argparse
import time
import bpy
import math
import mathutils
import datetime
import subprocess

class BlenderGLBRenderer:
    def __init__(self, model_path, output_dir=None, resolution=2000):
        # 确保模型路径是绝对路径
        self.model_path = os.path.abspath(model_path)
        self.resolution = resolution
        
        # 设置输出目录
        if output_dir is None:
            self.output_dir = os.path.dirname(os.path.abspath(model_path))
        else:
            self.output_dir = os.path.abspath(output_dir)
        
        # 获取模型名称（不带扩展名）
        self.model_name = os.path.splitext(os.path.basename(model_path))[0]
        
        print(f"模型路径: {self.model_path}")
        print(f"输出目录: {self.output_dir}")
        print(f"模型名称: {self.model_name}")
            
        # 记录开始时间
        self.start_time = time.time()
        
        # 清理当前场景
        self.clean_scene()
    
    def clean_scene(self):
        """清理当前Blender场景"""
        # 删除所有对象
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        # 删除所有材质
        for material in bpy.data.materials:
            bpy.data.materials.remove(material)
        
        # 删除所有纹理
        for texture in bpy.data.textures:
            bpy.data.textures.remove(texture)
        
        # 删除所有图像
        for image in bpy.data.images:
            bpy.data.images.remove(image)
    
    def import_model(self):
        """导入GLB/GLTF模型"""
        print(f"导入模型: {self.model_path}")
        
        # 导入GLB/GLTF模型
        if self.model_path.lower().endswith('.glb') or self.model_path.lower().endswith('.gltf'):
            bpy.ops.import_scene.gltf(filepath=self.model_path)
        else:
            raise ValueError(f"不支持的文件格式: {self.model_path}")
        
        # 检查是否成功导入
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        if not mesh_objects:
            raise ValueError("导入失败，没有找到网格对象")
        
        print(f"成功导入 {len(mesh_objects)} 个网格对象")
        
        return mesh_objects
    
    def calculate_bounds(self):
        """计算模型的边界框"""
        # 获取所有网格对象
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        # 初始化边界框
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        
        # 计算所有对象的边界框
        for obj in mesh_objects:
            for v in obj.bound_box:
                # 将局部坐标转换为全局坐标
                global_v = obj.matrix_world @ mathutils.Vector(v)
                
                # 更新边界框
                min_x = min(min_x, global_v.x)
                min_y = min(min_y, global_v.y)
                min_z = min(min_z, global_v.z)
                max_x = max(max_x, global_v.x)
                max_y = max(max_y, global_v.y)
                max_z = max(max_z, global_v.z)
        
        # 存储边界框
        self.bounds_min = (min_x, min_y, min_z)
        self.bounds_max = (max_x, max_y, max_z)
        self.dimensions = (max_x - min_x, max_y - min_y, max_z - min_z)
        self.max_dimension = max(self.dimensions)
        
        print(f"模型边界: {self.bounds_min} 到 {self.bounds_max}")
        print(f"模型尺寸: {self.dimensions}, 最大尺寸: {self.max_dimension}")
    
    def setup_scene(self):
        """设置渲染场景"""
        # 设置渲染引擎为Cycles
        bpy.context.scene.render.engine = 'CYCLES'
        
        # 设置设备为GPU（如果可用）
        bpy.context.scene.cycles.device = 'GPU'
        
        # 设置渲染质量
        bpy.context.scene.cycles.samples = 64
        bpy.context.scene.cycles.use_denoising = True
        
        # 设置渲染分辨率
        bpy.context.scene.render.resolution_x = self.resolution
        bpy.context.scene.render.resolution_y = self.resolution
        bpy.context.scene.render.resolution_percentage = 100
        
        # 设置透明背景
        bpy.context.scene.render.film_transparent = True
        
        # 创建相机
        bpy.ops.object.camera_add()
        self.camera = bpy.context.object
        bpy.context.scene.camera = self.camera
        
        # 设置相机为正交
        self.camera.data.type = 'ORTHO'
        
        # 设置正交相机的缩放比例，确保模型完全可见
        # 添加一些边距
        margin = 1.2  # 20%的边距
        self.camera.data.ortho_scale = self.max_dimension * margin
        
        # 删除所有现有灯光
        for obj in bpy.context.scene.objects:
            if obj.type == 'LIGHT':
                bpy.data.objects.remove(obj)
        
        # 计算模型中心
        center = ((self.bounds_min[0] + self.bounds_max[0]) / 2,
                 (self.bounds_min[1] + self.bounds_max[1]) / 2,
                 (self.bounds_min[2] + self.bounds_max[2]) / 2)
        
        # 创建四点照明系统
        # 主光源（Key Light）- 从右上方照射
        bpy.ops.object.light_add(type='SUN', location=(center[0] + self.max_dimension, 
                                                      center[1] - self.max_dimension, 
                                                      center[2] + self.max_dimension * 1.5))
        key_light = bpy.context.object
        key_light.data.energy = 2.0
        key_light.data.angle = 0.1  # 较小的角度使光线更平行
        
        # 填充光（Fill Light）- 从左侧照射
        bpy.ops.object.light_add(type='SUN', location=(center[0] - self.max_dimension * 1.5, 
                                                      center[1], 
                                                      center[2] + self.max_dimension * 0.8))
        fill_light = bpy.context.object
        fill_light.data.energy = 1.5
        fill_light.data.angle = 0.2
        
        # 背光（Back Light）- 从后上方照射
        bpy.ops.object.light_add(type='SUN', location=(center[0], 
                                                      center[1] + self.max_dimension * 1.5, 
                                                      center[2] + self.max_dimension))
        back_light = bpy.context.object
        back_light.data.energy = 1.8
        back_light.data.angle = 0.15
        
        # 顶光（Top Light）- 从正上方照射，提供均匀照明
        bpy.ops.object.light_add(type='SUN', location=(center[0], 
                                                      center[1], 
                                                      center[2] + self.max_dimension * 2))
        top_light = bpy.context.object
        top_light.data.energy = 1.0
        top_light.data.angle = 0.3  # 较大的角度使光线更分散
        
        # 环境光（Ambient Light）- 通过世界设置提供柔和的环境光
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            bpy.context.scene.world = world
        
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get('Background')
        if bg_node:
            bg_node.inputs[0].default_value = (1, 1, 1, 1)  # 白色背景
            bg_node.inputs[1].default_value = 0.3  # 低强度环境光
    
    def position_camera(self, view_type):
        """根据视图类型定位相机"""
        # 计算模型中心
        center = ((self.bounds_min[0] + self.bounds_max[0]) / 2,
                 (self.bounds_min[1] + self.bounds_max[1]) / 2,
                 (self.bounds_min[2] + self.bounds_max[2]) / 2)
        
        # 根据视图类型设置相机位置
        if view_type == '正面':
            self.camera.location = (center[0], center[1] - self.max_dimension * 2, center[2])
            self.camera.rotation_euler = (math.radians(90), 0, 0)
        elif view_type == '背面':
            self.camera.location = (center[0], center[1] + self.max_dimension * 2, center[2])
            self.camera.rotation_euler = (math.radians(90), 0, math.radians(180))
        elif view_type == '左视图':
            # 修改左视图相机位置和旋转
            self.camera.location = (center[0] - self.max_dimension * 2, center[1], center[2])
            self.camera.rotation_euler = (math.radians(90), 0, math.radians(270))
        elif view_type == '右视图':
            # 修改右视图相机位置和旋转
            self.camera.location = (center[0] + self.max_dimension * 2, center[1], center[2])
            self.camera.rotation_euler = (math.radians(90), 0, math.radians(90))
        elif view_type == '俯视图':
            self.camera.location = (center[0], center[1], center[2] + self.max_dimension * 2)
            self.camera.rotation_euler = (0, 0, 0)
        elif view_type == '底视图':
            self.camera.location = (center[0], center[1], center[2] - self.max_dimension * 2)
            self.camera.rotation_euler = (math.radians(180), 0, 0)
        else:
            raise ValueError(f"不支持的视图类型: {view_type}")
        
        # 确保相机更新
        bpy.context.view_layer.update()
    
    def render_view(self, view_type, output_path):
        """渲染指定视图"""
        print(f"  渲染 {view_type}...")
        
        # 定位相机
        self.position_camera(view_type)
        
        # 设置输出路径
        bpy.context.scene.render.filepath = output_path
        
        # 渲染
        bpy.ops.render.render(write_still=True)
        
        return output_path
    
    def render_six_views(self):
        """渲染所有六个标准视图"""
        print("渲染模型的六个标准视图...")
        
        # 六个标准视图
        view_types = ['正面', '左视图', '背面', '右视图', '俯视图', '底视图']
        view_paths = {}
        
        # 渲染每个视图
        for view_type in view_types:
            output_path = os.path.join(self.output_dir, f"{self.model_name}_{view_type}.png")
            self.render_view(view_type, output_path)
            view_paths[view_type] = output_path
        
        # 打印视图文件路径
        print(f"\n六个视图已保存到: {self.output_dir}")
        print(f"总渲染时间: {time.time() - self.start_time:.2f} 秒\n")
        
        print("视图文件路径:")
        for view_type, path in view_paths.items():
            print(f"{view_type}: {path}")
        
        print("")  # 添加空行，使输出更整洁
        
        return view_paths

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='使用Blender渲染GLB模型的六个标准视图')
    parser.add_argument('model_path', help='GLB模型文件路径')
    parser.add_argument('--output', '-o', help='输出目录路径')
    parser.add_argument('--resolution', '-r', type=int, default=2000, help='渲染分辨率')
    
    # 获取Blender传递的参数（去掉Blender自己的参数）
    argv = sys.argv
    
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    
    args = parser.parse_args(argv)
    
    # 创建渲染器并渲染六个视图
    renderer = BlenderGLBRenderer(args.model_path, args.output, args.resolution)
    renderer.import_model()
    renderer.calculate_bounds()
    renderer.setup_scene()
    view_paths = renderer.render_six_views()
    
    return view_paths

if __name__ == "__main__":
    main()
