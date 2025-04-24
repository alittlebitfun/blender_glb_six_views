import os
import sys
import argparse
import time
import bpy
import math
import mathutils
import datetime
import subprocess
import shutil

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
        elif view_type == '等轴测无材质':
            # 等轴测视图 - 从右上方45度角观察
            self.camera.location = (center[0] + self.max_dimension * 1.5, 
                                   center[1] - self.max_dimension * 1.5, 
                                   center[2] + self.max_dimension * 1.5)
            # 设置相机旋转，使其朝向模型中心
            direction = mathutils.Vector(center) - mathutils.Vector(self.camera.location)
            rot_quat = direction.to_track_quat('-Z', 'Y')
            self.camera.rotation_euler = rot_quat.to_euler()
            # 将相机类型改为透视，以获得更好的等轴测效果
            self.camera.data.type = 'PERSP'
            self.camera.data.lens = 50  # 标准视角
        elif view_type == 'UV贴图':
            # 对于UV贴图视图，我们将使用正交相机从正面观察
            self.camera.location = (center[0], center[1] - self.max_dimension * 2, center[2])
            self.camera.rotation_euler = (math.radians(90), 0, 0)
            self.camera.data.type = 'ORTHO'
        else:
            raise ValueError(f"不支持的视图类型: {view_type}")
        
        # 确保相机更新
        bpy.context.view_layer.update()
    
    def set_material_display_mode(self, mode):
        """设置材质显示模式
        
        Args:
            mode: 'normal' 正常材质, 'wireframe' 线框, 'solid' 纯色无材质
        """
        # 获取所有网格对象
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        if mode == 'normal':
            # 正常显示材质，不做任何更改
            pass
        elif mode == 'wireframe':
            # 设置为线框模式
            for obj in mesh_objects:
                if obj.active_material:
                    obj.active_material.use_nodes = False
                    obj.active_material.diffuse_color = (0.8, 0.8, 0.8, 1.0)  # 灰色
                obj.display_type = 'WIRE'
        elif mode == 'solid':
            # 设置为纯色模式，无材质
            for obj in mesh_objects:
                # 选择对象
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 创建新的纯色材质
                mat = bpy.data.materials.new(name="SolidMaterial")
                mat.use_nodes = False
                mat.diffuse_color = (0.8, 0.8, 0.8, 1.0)  # 灰色
                
                # 清除所有材质槽
                while len(obj.material_slots) > 0:
                    bpy.ops.object.material_slot_remove()
                
                # 添加新材质
                obj.data.materials.append(mat)
                obj.display_type = 'SOLID'
        else:
            raise ValueError(f"不支持的材质显示模式: {mode}")
    
    def create_uv_map_image(self, output_path):
        """创建UV贴图视图并保存到指定路径"""
        # 获取所有网格对象
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        
        # 检查是否有网格对象
        if not mesh_objects:
            print("警告: 没有找到网格对象，无法创建UV贴图")
            return False
        
        # 查找模型中的所有贴图
        found_textures = False
        
        # 遍历所有材质寻找贴图
        for material in bpy.data.materials:
            if material.use_nodes:
                # 查找节点树中的图像纹理节点
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        # 找到贴图，保存到输出路径
                        print(f"找到贴图: {node.image.name}")
                        found_textures = True
                        
                        try:
                            # 检查图像是否已打包
                            if node.image.packed_file:
                                # 如果图像已打包，直接保存
                                temp_path = output_path
                                node.image.save_render(temp_path)
                                print(f"已保存打包贴图到: {temp_path}")
                                return True
                            else:
                                # 如果图像有文件路径，复制文件
                                import shutil
                                if node.image.filepath and os.path.exists(node.image.filepath_raw):
                                    shutil.copy2(node.image.filepath_raw, output_path)
                                    print(f"已复制贴图文件到: {output_path}")
                                    return True
                                else:
                                    # 尝试直接保存图像
                                    node.image.save_render(output_path)
                                    print(f"已保存贴图到: {output_path}")
                                    return True
                        except Exception as e:
                            print(f"保存贴图时出错: {e}")
                            # 继续尝试其他贴图
                            continue
        
        # 如果没有找到贴图，使用备用方法
        if not found_textures:
            print("未找到贴图，使用备用方法生成UV图像")
            
            try:
                # 创建一个简单的UV网格图像
                # 选择第一个网格对象
                obj = mesh_objects[0]
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 创建UV显示材质
                mat = bpy.data.materials.new(name="UVMaterial")
                mat.use_nodes = True
                
                # 获取节点树
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                
                # 清除所有节点
                for node in nodes:
                    nodes.remove(node)
                
                # 创建节点
                output = nodes.new(type='ShaderNodeOutputMaterial')
                shader = nodes.new(type='ShaderNodeBsdfPrincipled')
                uvmap = nodes.new(type='ShaderNodeTexCoord')
                
                # 连接节点
                links.new(uvmap.outputs['UV'], shader.inputs['Base Color'])
                links.new(shader.outputs['BSDF'], output.inputs['Surface'])
                
                # 清除所有材质槽
                while len(obj.material_slots) > 0:
                    bpy.ops.object.material_slot_remove()
                
                # 添加新材质
                obj.data.materials.append(mat)
                
                # 渲染UV图像
                bpy.context.scene.render.filepath = output_path
                bpy.ops.render.render(write_still=True)
                
                return True
                
            except Exception as e:
                print(f"备用方法创建UV图像时出错: {e}")
                return False
                
        return False
    
    def render_view(self, view_type, output_path):
        """渲染指定视图"""
        print(f"  渲染 {view_type}...")
        
        # 根据视图类型设置特殊渲染模式
        if view_type == '等轴测无材质':
            # 先定位相机
            self.position_camera(view_type)
            # 设置为纯色无材质模式
            self.set_material_display_mode('solid')
        elif view_type == 'UV贴图':
            # UV贴图使用特殊方法创建
            return self.create_uv_map_image(output_path)
        else:
            # 其他视图使用正常材质
            self.set_material_display_mode('normal')
            # 定位相机
            self.position_camera(view_type)
        
        # 设置输出路径
        bpy.context.scene.render.filepath = output_path
        
        # 渲染
        bpy.ops.render.render(write_still=True)
        
        # 如果更改了材质模式，恢复正常材质
        if view_type == '等轴测无材质':
            # 重新导入模型以恢复原始材质
            self.clean_scene()
            self.import_model()
            self.calculate_bounds()
            self.setup_scene()
        
        return output_path

    def render_eight_views(self):
        """渲染所有八个视图"""
        print("渲染模型的八个视图...")
        
        # 八个视图
        view_types = ['正面', '左视图', '背面', '等轴测无材质', '俯视图', '底视图', '右视图', 'UV贴图']
        view_paths = {}
        
        # 渲染每个视图
        for view_type in view_types:
            output_path = os.path.join(self.output_dir, f"{self.model_name}_{view_type}.png")
            self.render_view(view_type, output_path)
            view_paths[view_type] = output_path
        
        # 打印视图文件路径
        print(f"\n八个视图已保存到: {self.output_dir}")
        print(f"总渲染时间: {time.time() - self.start_time:.2f} 秒\n")
        
        print("视图文件路径:")
        for view_type, path in view_paths.items():
            print(f"{view_type}: {path}")
        
        print("")  # 添加空行，使输出更整洁
        
        return view_paths

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='使用Blender渲染GLB模型的八个视图')
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
    
    # 创建渲染器并渲染八个视图
    renderer = BlenderGLBRenderer(args.model_path, args.output, args.resolution)
    renderer.import_model()
    renderer.calculate_bounds()
    renderer.setup_scene()
    view_paths = renderer.render_eight_views()
    
    return view_paths

if __name__ == "__main__":
    main()
