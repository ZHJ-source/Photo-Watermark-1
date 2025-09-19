# 图片批量水印工具（命令行版）

一个纯命令行的图片批量水印工具，可以自动提取图片EXIF信息中的拍摄日期作为水印，并支持自定义字体大小、颜色和位置。

## 功能特点

- 批量处理指定文件夹中的所有图片
- 自动提取图片EXIF信息中的拍摄日期作为水印文本
- 支持设置字体大小、颜色和位置
- 将处理后的图片保存到原目录下的子目录中
- 支持多种图片格式（JPG、PNG、BMP、GIF、HEIC等）
  **特别说明：** 处理HEIC格式图片需要安装额外依赖库（pyheif和相关依赖）。

## 安装说明

1. 确保已安装Python 3.6或更高版本
2. 安装所需依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

基本使用格式：

```bash
python watermark_cli.py --folder 图片文件夹路径 [可选参数]
```

### 必需参数

- `--folder`, `-f`: 图片文件夹路径

### 可选参数

- `--font-size`, `-s`: 水印字体大小，默认为30
- `--font-color`, `-c`: 水印字体颜色，默认为'white'
- `--position`, `-p`: 水印位置，可选值：'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center'，默认为'bottom-right'
- `--custom-position`, `-cp`: 自定义水印位置坐标 (x, y)，使用此参数将覆盖position参数

### 使用示例

1. 使用默认参数处理图片：

```bash
python watermark_cli.py --folder ./photo
```

2. 自定义字体大小和颜色：

```bash
python watermark_cli.py --folder ./photo --font-size 40 --font-color red
```

3. 自定义水印位置：

```bash
python watermark_cli.py --folder ./photo --position top-left
```

4. 使用自定义坐标位置：

```bash
python watermark_cli.py --folder ./photo --custom-position 50 100
```

## 输出说明

处理后的图片将保存在原图片所在目录的一个新子目录中，子目录名称为`原目录名_watermark`。

例如，如果原图片路径为`/path/to/photos/image.jpg`，则输出路径为`/path/to/photos/photos_watermark/image_watermark.jpg`。

## 注意事项

- 程序会尝试提取图片的EXIF信息中的拍摄日期，如果无法提取，将使用文件的修改日期
- 程序会自动尝试加载系统中的中文字体，确保水印文本正常显示
- HEIC格式的图片会被转换为JPEG格式保存
- 处理过程中会显示进度信息和处理结果