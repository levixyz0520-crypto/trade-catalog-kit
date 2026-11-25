# Trade Catalog Kit 中文说明

把 Excel 或 CSV 和产品图片生成带品牌信息的 A4 PDF 目录。适合家具外贸、制造工厂、出口商和 B2B 批发商制作选品册、展会目录及新品资料。支持 Streamlit 网页界面和命令行，核心流程可在本机运行。

[English](README.md) · [Excel 模板](examples/product-template.xlsx) · [CSV 模板](examples/product-template.csv) · [英文样板](examples/demo.pdf) · [中文样板](examples/demo-minimal.pdf)

## Windows 和 macOS 安装

安装 Python 3.11 或更新版本，推荐从 Python 3.12 开始。下载并解压项目源码，在项目目录打开终端。

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[web]"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

**macOS 和 Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[web]'
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

在浏览器访问 `http://127.0.0.1:8501`。界面使用英文，可先勾选 **Try the included furniture example** 试跑。使用自己的文件时，先上传产品表格和图片，按需调整字段映射并修正校验错误。然后选择版式、每页款数、品牌、主题色及 Logo。在 **PDF labels** 选择简体中文可以生成中文标签。点击 **Generate PDF preview** 逐页预览，最后点击 **Download catalog PDF** 下载。按 Ctrl+C 关闭应用。

## 准备资料

- Excel 读取第一张工作表，CSV 使用 UTF-8。首行为标题。SKU、产品名称和产品尺寸必填。以零开头的 SKU 在 Excel 中请设为文本。公式需转换为静态值。
- 标准模板包含 Product Code、Product Name、Category、Product Size、Carton Size、Gross Weight、CBM、Cartons per Piece、40HQ Quantity、Color、Material、Description、Image。现有列名也可手动映射。
- 尺寸可用 `80 × 40 × 90 cm`、`800 × 400 × 900 mm` 等格式。支持 mm、cm、m、in、ft。没写单位时默认 cm。混合单位时请逐项注明。毛重支持 kg、g、lb，默认 kg。
- 多个相同包装填写一组尺寸加件均箱数。多个不同纸箱用 `;` 分隔尺寸。填写了手工 CBM 时以手工值为准，与计算值差异超过 5% 会提醒。
- 40HQ 理论数量按可用体积 × 利用率 ÷ 单件 CBM 向下取整。默认 76 m³ 和 85%，可修改。实际装柜还取决于尺寸、堆叠和载重。表格自带数量会单独标为提供值。
- 上传 JPEG、PNG 或 WebP。Image 留空时按文件名去掉后缀匹配型号。缺图会提示并显示占位图。图片默认等比缩放，可选居中裁剪和透明区域白底合成。可选 AI 去背景使用本地 CPU 模型，首次使用需要下载模型。检查去背景后的产品边缘。
- 选择三种版式之一与每页 1、2 或 4 款，设置封面、公司介绍、联系方式和封底。自定义字体须为可嵌入的 `.ttf` 文件。产品文字按源表输出。字段太长时，请缩短文字或减少每页款数。

## 命令行

以已安装工具的虚拟环境运行，或把 `python` 换成上面的虚拟环境路径。

```sh
python -m trade_catalog_kit examples/furniture.xlsx --images examples/images --check
python -m trade_catalog_kit examples/furniture.xlsx --images examples/images --theme minimal --language zh --per-page 1 --out catalog.pdf
```

[高级用法](docs/usage.md) · [Docker 与 Community Cloud](docs/deployment.md) · [路线图](docs/roadmap.md) · [问题反馈](https://github.com/levixyz0520-crypto/trade-catalog-kit/issues) · [MIT 协议](LICENSE)
