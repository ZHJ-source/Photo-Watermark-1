#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont, ExifTags
import piexif
import glob

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
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
    
    def open_image(self, image_path):
        """打开图片，支持指定的图片格式"""
        file_ext = os.path.splitext(image_path)[1].lower()
        
        # 检查是否支持该格式
        if file_ext not in self.supported_formats:
            print(f"不支持的文件格式 '{file_ext}'，跳过处理图片 '{image_path}'")
            return None
        
        # 尝试使用PIL打开图片
        try:
            image = Image.open(image_path)
            return image
        except Exception as pil_error:
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
        
        try:
            # 尝试通用方法 - 先打开图片
            image = self.open_image(image_path)
            if image:
                try:
                    # 尝试使用PIL的_getexif方法
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
            
            # 尝试直接从文件读取EXIF
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
            # 打开图片
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
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 计算水印位置
            position = self.calculate_position(image.width, image.height, text_width, text_height)
            
            # 添加水印
            draw.text(position, watermark_text, font=font, fill=self.args.font_color)
            
            # 保存图片
            file_name = os.path.basename(image_path)
            output_path = os.path.join(self.output_dir, file_name)
            
            # 根据原图片格式保存
            image_format = image.format
            if not image_format:
                image_format = 'JPEG'  # 默认保存为JPEG格式
            
            # 如果是透明背景的PNG，保持透明度
            if image_format == 'PNG' and image.mode == 'RGBA':
                image.save(output_path, format=image_format)
            else:
                # 对于其他格式，转换为RGB
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(output_path, format=image_format)
            
            return output_path
        except Exception as e:
            print(f"处理图片 '{image_path}' 时出错：{str(e)}")
            return None
    
    def process_all_images(self):
        """处理文件夹中的所有图片"""
        # 获取所有图片文件
        image_files = self.get_image_files()
        if not image_files:
            print(f"在文件夹 '{self.args.folder}' 中未找到支持的图片文件")
            return
        
        total_files = len(image_files)
        success_count = 0
        
        print(f"开始处理 {total_files} 个图片文件...")
        
        for i, image_path in enumerate(image_files, 1):
            print(f"处理图片 {i}/{total_files}: {os.path.basename(image_path)}")
            
            # 提取拍摄日期作为水印文本
            watermark_text = self.extract_exif_date(image_path)
            
            # 添加水印
            result = self.add_watermark(image_path, watermark_text)
            if result:
                success_count += 1
                print(f"  ✓ 水印添加成功：{os.path.basename(result)}")
            else:
                print(f"  ✗ 水印添加失败")
        
        print(f"\n处理完成！")
        print(f"总文件数: {total_files}")
        print(f"成功: {success_count}")
        print(f"失败: {total_files - success_count}")
        print(f"水印图片保存目录: {self.output_dir}")

if __name__ == "__main__":
    try:
        watermark_cli = WatermarkCLI()
        watermark_cli.process_all_images()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行时出错：{str(e)}")
        sys.exit(1)