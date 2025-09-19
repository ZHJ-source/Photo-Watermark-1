#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont, ExifTags
import piexif
import glob

# 尝试导入pyheif以支持HEIC格式
try:
    import pyheif
    has_pyheif = True
except ImportError:
    has_pyheif = False
    print("警告：未安装pyheif库，可能无法处理HEIC格式图片")
    print("提示：如需处理HEIC格式图片，请先安装系统依赖：brew install libheif")
    print("然后安装Python依赖：pip install pyheif")

# 尝试从PIL导入ImageSequence（用于某些特殊格式处理）
try:
    from PIL import ImageSequence
except ImportError:
    pass

class WatermarkCLI:
    def __init__(self):
        # 解析命令行参数
        self.parser = argparse.ArgumentParser(description='图片批量添加水印工具')
        self.parser.add_argument('--folder', '-f', required=True, help='图片文件夹路径')
        self.parser.add_argument('--font-size', '-s', type=int, default=30, help='水印字体大小')
        self.parser.add_argument('--font-color', '-c', default='white', help='水印字体颜色')
        self.parser.add_argument('--position', '-p', choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'], \
                               default='bottom-right', help='水印位置')
        self.parser.add_argument('--custom-position', '-cp', nargs=2, type=int, help='自定义水印位置坐标 (x, y)')
        
        # 解析参数
        self.args = self.parser.parse_args()
        
        # 验证文件夹路径
        if not os.path.isdir(self.args.folder):
            print(f"错误：文件夹 '{self.args.folder}' 不存在或不是有效文件夹路径")
            sys.exit(1)
        
        # 创建输出目录
        self.output_dir = os.path.join(self.args.folder, os.path.basename(self.args.folder) + '_watermark')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 支持的图片格式
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.heic']
    
    def open_image(self, image_path):
        """打开图片，支持HEIC格式"""
        file_ext = os.path.splitext(image_path)[1].lower()
        
        # 首先尝试直接使用PIL打开（Pillow 10.0+支持HEIC）
        try:
            image = Image.open(image_path)
            return image
        except Exception as pil_error:
            # 如果是HEIC格式且PIL打开失败，尝试其他方法
            if file_ext == '.heic':
                print(f"PIL直接打开HEIC失败：{str(pil_error)}")
                # 尝试使用pyheif
                if has_pyheif:
                    try:
                        # 尝试使用pyheif读取
                        heif_file = pyheif.read(image_path)
                        # 将HEIC转换为PIL图像
                        image = Image.frombytes(
                            heif_file.mode, 
                            heif_file.size, 
                            heif_file.data, 
                            "raw", 
                            heif_file.mode, 
                            heif_file.stride, 
                        )
                        return image
                    except Exception as pyheif_error:
                        print(f"使用pyheif打开HEIC图片 '{image_path}' 时出错：{str(pyheif_error)}")
                else:
                    print(f"提示：如需处理HEIC格式图片，请先安装系统依赖：brew install libheif")
                    print(f"然后安装Python依赖：pip install pyheif")
            
            # 如果是其他格式或所有方法都失败
            print(f"无法打开图片 '{image_path}'：{str(pil_error)}")
            return None
    
    def get_image_files(self):
        """获取文件夹中所有支持的图片文件"""
        image_files = []
        for ext in self.supported_formats:
            # 不区分大小写查找文件
            pattern = os.path.join(self.args.folder, f'*{ext}')
            pattern_upper = os.path.join(self.args.folder, f'*{ext.upper()}')
            image_files.extend(glob.glob(pattern))
            image_files.extend(glob.glob(pattern_upper))
        return image_files
    
    def extract_exif_date(self, image_path):
        """从图片中提取EXIF信息中的拍摄日期"""
        file_ext = os.path.splitext(image_path)[1].lower()
        
        try:
            # 对于HEIC格式，我们需要特殊处理
            if file_ext == '.heic' and has_pyheif:
                try:
                    # 先使用pyheif读取文件
                    heif_file = pyheif.read(image_path)
                    
                    # 检查是否有EXIF数据
                    if hasattr(heif_file, 'metadata') and heif_file.metadata:
                        for metadata in heif_file.metadata:
                            if metadata['type'] == 'Exif':
                                # 尝试使用piexif解析EXIF数据
                                try:
                                    exif_dict = piexif.load(metadata['data'])
                                    if 'Exif' in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                                        date_bytes = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal]
                                        date_str = date_bytes.decode('utf-8', errors='replace')
                                        if ':' in date_str:
                                            date_parts = date_str.split(' ')[0].split(':')
                                            if len(date_parts) >= 3:
                                                return f"{date_parts[0]}年{date_parts[1]}月{date_parts[2]}日"
                                except Exception as piexif_error:
                                    print(f"使用piexif解析HEIC EXIF时出错：{str(piexif_error)}")
                except Exception as e:
                    print(f"使用pyheif读取HEIC时出错：{str(e)}")
            
            # 尝试通用方法 - 先打开图片
            image = self.open_image(image_path)
            if image:
                try:
                    # 对于普通格式，尝试使用PIL的_getexif方法
                    exif_data = image._getexif()
                    if exif_data:
                        exif = {ExifTags.TAGS.get(tag, tag): value for tag, value in exif_data.items()}
                        if 'DateTimeOriginal' in exif:
                            date_str = exif['DateTimeOriginal']
                            if ':' in date_str:
                                date_parts = date_str.split(' ')[0].split(':')
                                if len(date_parts) >= 3:
                                    return f"{date_parts[0]}年{date_parts[1]}月{date_parts[2]}日"
                except Exception as pil_exif_error:
                    print(f"使用PIL读取EXIF时出错：{str(pil_exif_error)}")
            
            # 尝试直接从文件读取EXIF（对于非HEIC格式）
            if file_ext != '.heic':
                try:
                    exif_dict = piexif.load(image_path)
                    if 'Exif' in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                        date_bytes = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal]
                        date_str = date_bytes.decode('utf-8', errors='replace')
                        if ':' in date_str:
                            date_parts = date_str.split(' ')[0].split(':')
                            if len(date_parts) >= 3:
                                return f"{date_parts[0]}年{date_parts[1]}月{date_parts[2]}日"
                except Exception as piexif_error:
                    print(f"使用piexif读取EXIF时出错：{str(piexif_error)}")
            
            # 如果都失败，使用文件修改日期作为后备方案
            try:
                file_mtime = os.path.getmtime(image_path)
                import datetime
                dt = datetime.datetime.fromtimestamp(file_mtime)
                return f"{dt.year}年{dt.month}月{dt.day}日"
            except Exception as mtime_error:
                print(f"获取文件修改时间时出错：{str(mtime_error)}")
            
            # 所有方法都失败
            return "无日期信息"
        except Exception as e:
            print(f"读取图片EXIF信息时出错：{str(e)}")
            return "无法读取日期"
    
    def calculate_position(self, image_width, image_height, text_width, text_height):
        """根据用户选择的位置或自定义坐标计算水印位置"""
        if self.args.custom_position:
            # 使用自定义坐标
            return tuple(self.args.custom_position)
        
        # 边距
        margin = 20
        
        # 根据预设位置计算坐标
        position = self.args.position
        if position == 'top-left':
            return (margin, margin)
        elif position == 'top-right':
            return (image_width - text_width - margin, margin)
        elif position == 'bottom-left':
            return (margin, image_height - text_height - margin)
        elif position == 'bottom-right':
            return (image_width - text_width - margin, image_height - text_height - margin)
        elif position == 'center':
            return ((image_width - text_width) // 2, (image_height - text_height) // 2)
        
        # 默认返回右下角
        return (image_width - text_width - margin, image_height - text_height - margin)
    
    def find_font(self, size=20):
        """尝试加载中文字体，如果失败则使用默认字体"""
        # 尝试常见的中文字体路径
        font_paths = [
            '/Library/Fonts/SimHei.ttf',  # macOS
            '/System/Library/Fonts/PingFang.ttc',  # macOS 系统字体
            '/System/Library/Fonts/SFNS.ttc',  # macOS San Francisco字体
            '/System/Library/Fonts/STHeiti Medium.ttc',  # macOS 黑体
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux
            'C:/Windows/Fonts/simhei.ttf',  # Windows
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception as e:
                    print(f"无法加载字体 '{font_path}'：{str(e)}")
                    continue
        
        # 如果没有找到中文字体，尝试使用系统默认字体，确保支持中文
        try:
            # 使用PIL的默认字体创建一个字体对象，但指定encoding为utf-8
            font = ImageFont.load_default()
            # 输出警告信息
            print("警告：无法找到中文字体，可能会导致水印中的中文显示不正确")
            return font
        except:
            print("严重错误：无法加载任何字体")
            return None
            
    def add_watermark(self, image_path, watermark_text):
        """为单张图片添加水印"""
        try:
            # 打开图片，支持HEIC格式
            image = self.open_image(image_path)
            if image is None:
                print(f"无法打开图片 '{image_path}'")
                return None
            
            draw = ImageDraw.Draw(image)
            
            # 尝试加载中文字体
            font = self.find_font(self.args.font_size)
            if font is None:
                print(f"无法为图片 '{image_path}' 加载字体，跳过处理")
                return None
            
            # 估算文本大小
            try:
                # 使用getbbox方法获取文本边界框（Pillow 8.0+）
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
            except AttributeError:
                # 旧版本Pillow使用textsize方法
                text_width, text_height = draw.textsize(watermark_text, font=font)
            
            # 计算水印位置
            image_width, image_height = image.size
            position = self.calculate_position(image_width, image_height, text_width, text_height)
            
            # 添加水印文本
            draw.text(position, watermark_text, font=font, fill=self.args.font_color)
            
            # 保存水印图片
            original_filename = os.path.basename(image_path)
            name, ext = os.path.splitext(original_filename)
            output_path = os.path.join(self.output_dir, f"{name}_watermark{ext}")
            
            # 保存图片，保持原格式
            if ext.lower() == '.png':
                image.save(output_path, 'PNG')
            elif ext.lower() in ['.jpg', '.jpeg']:
                image.save(output_path, 'JPEG', quality=95)
            elif ext.lower() == '.heic':
                # 对于HEIC格式，保存为JPEG
                output_path = output_path.replace('.heic', '.jpg').replace('.HEIC', '.jpg')
                image.save(output_path, 'JPEG', quality=95)
            else:
                image.save(output_path)
            
            return output_path
        except Exception as e:
            print(f"处理图片 '{image_path}' 时出错：{str(e)}")
            return None
    
    def process_all_images(self):
        """处理文件夹中的所有图片"""
        image_files = self.get_image_files()
        
        if not image_files:
            print(f"错误：在文件夹 '{self.args.folder}' 中未找到支持的图片文件")
            sys.exit(1)
        
        total = len(image_files)
        print(f"找到 {total} 个图片文件，开始处理...")
        
        success_count = 0
        for i, image_path in enumerate(image_files, 1):
            print(f"处理图片 {i}/{total}: {os.path.basename(image_path)}")
            
            # 提取拍摄日期作为水印
            watermark_text = self.extract_exif_date(image_path)
            
            # 添加水印并保存
            output_path = self.add_watermark(image_path, watermark_text)
            
            if output_path:
                print(f"  ✓  已保存：{os.path.basename(output_path)}")
                success_count += 1
            else:
                print(f"  ✗  处理失败")
        
        print(f"\n处理完成！")
        print(f"成功处理: {success_count}/{total}")
        print(f"所有水印图片保存在: {self.output_dir}")

if __name__ == "__main__":
    # 初始化并运行水印工具
    watermark_tool = WatermarkCLI()
    watermark_tool.process_all_images()