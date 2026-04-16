# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import xlsxwriter

DST = r'D:/claude code/credit_report_agent_work/docs/文档审核智能体_功能清单.xlsx'
wb = xlsxwriter.Workbook(DST)
ws = wb.add_worksheet('功能清单')

# formats
hdr_fmt = wb.add_format({
    'bold': True, 'font_size': 12, 'bg_color': '#1C1C1C', 'font_color': '#FFFFFF',
    'border': 1, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
    'font_name': 'Microsoft YaHei'
})
cat_fmt = wb.add_format({
    'bold': True, 'font_size': 11, 'bg_color': '#F2F2F2',
    'border': 1, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
    'font_name': 'Microsoft YaHei'
})
scene_fmt = wb.add_format({
    'font_size': 10, 'border': 1, 'text_wrap': True, 'valign': 'vcenter',
    'font_name': 'Microsoft YaHei'
})
desc_fmt = wb.add_format({
    'font_size': 10, 'border': 1, 'text_wrap': True, 'valign': 'top',
    'font_name': 'Microsoft YaHei'
})

ws.set_column('A:A', 16)
ws.set_column('B:B', 14)
ws.set_column('C:C', 20)
ws.set_column('D:D', 70)
ws.set_column('E:E', 14)

ws.write_row(0, 0, ['产品', '场景分类', '场景描述', '功能/能力描述', '是否已支持'], hdr_fmt)

status_yes = wb.add_format({
    'font_size': 10, 'border': 1, 'text_wrap': True, 'valign': 'vcenter',
    'align': 'center', 'font_name': 'Microsoft YaHei',
    'font_color': '#217346', 'bold': True
})
status_plan = wb.add_format({
    'font_size': 10, 'border': 1, 'text_wrap': True, 'valign': 'vcenter',
    'align': 'center', 'font_name': 'Microsoft YaHei',
    'font_color': '#BF8F00', 'bold': True
})
ws.set_row(0, 28)

data = [
    ('文档解析', [
        ('多格式文档支持', '支持 PDF（标准文档和扫描件）、Word（.doc/.docx）上传，系统自动识别文档类型并选择对应解析方式；Excel 表格与 PPT 演示文稿即将上线', '已支持'),
        ('扫描件识别', '对扫描件 PDF 和图片格式文档，通过高精度 OCR 提取全部文字、表格结构、印章位置和签名内容', '已支持'),
        ('大文档处理', '支持 100 页以上大型文档，自动分段并行处理，30 页内文档审核总耗时不超过 90 秒', '即将上线'),
        ('文档结构化', '智能识别章节层级、标题、正文、表格、附件，为后续逐项审核建立结构化基础', '已支持'),
    ]),
    ('内容审核', [
        ('合规性审核', '检查文档内容是否符合法规政策及企业内部规范，识别敏感表述、禁用词、政治风险措辞及不当称谓，降低合规风险', '已支持'),
        ('跨文档一致性校验', '自动比对多份关联文档中的关键字段：合同标的、金额、公司名称、法人信息、银行账户、统一信用代码、纳税人识别号等，不一致项逐条高亮标出', '已支持'),
        ('文档内一致性校验', '校验单文档内部的数据一致性：正文与表格数据是否匹配、前后描述有无矛盾、时间节点逻辑是否合理', '已支持'),
        ('敏感信息识别', '识别涉及政治敏感、地区称谓规范（如台湾/香港/澳门称谓）、领土主权等方面的不当表述，避免舆情与合规风险', '已支持'),
        ('链接有效性验证', '自动遍历文档中引用的外部网络链接，逐一验证可访问性并截图留存，确保引用来源可靠', '已支持'),
    ]),
    ('财务审核', [
        ('金额校验', '校验金额大小写一致性，自动比对含税总额、不含税金额、税金与税率的计算关系，反向推导验证准确性', '已支持'),
        ('分项合计校验', '合同涉及多项金额明细时，自动校验各分项之和是否等于总金额，避免人工计算遗漏', '已支持'),
        ('数字格式规范', '检查千分位符、小数点、计量单位（元/万元）的统一性，防止单位混用导致金额误读', '已支持'),
    ]),
    ('格式审核', [
        ('模板匹配', '按企业预设标准模板检查文档排版：字体字号、行距段距、页眉页脚、章节编号，偏差项逐一标出', '已支持'),
        ('水印与防伪', '检查文档是否包含指定水印、页眉页脚等规范标识，确保文档来源的官方性', '已支持'),
        ('自定义模板', '支持企业自定义格式模板，不同客户可配置不同排版标准，新增模板无需改动核心系统', '已支持'),
    ]),
    ('签章审核', [
        ('印章识别与校验', '自动识别合同中印章的位置、类型和内容，校验双方是否均已用章、章面是否清晰可辨、印章名称与合同主体是否完全匹配', '已支持'),
        ('签字完整性', '检查合同各方代表签字是否齐全，签字人姓名与所盖名章或公司名称是否对应', '已支持'),
        ('授权委托校验', '若签字人为授权代表而非法人代表，自动校验授权委托书的有效性——授权范围、期限、授权人与被授权人信息是否匹配', '已支持'),
    ]),
    ('审核报告', [
        ('问题可视化', '原文在线预览，审核问题按风险等级（高/中/低）分色高亮标注在文档中，点击任意问题可跳转原文定位', '已支持'),
        ('智能聚合与总结', '同一段落多个问题合并展示，避免重复干扰；系统自动生成审核总结，包含总问题数、各等级分布、重点风险概述', '已支持'),
        ('误报处理', '用户可一键标记误报，标记后自动隐藏且导出报告不再出现。误报数据回传系统，用于持续优化审核准确率', '已支持'),
        ('一键导出', '支持 PDF 审核报告和 Word 带批注可编辑文档导出，审核人员拿到可编辑稿即可直接修改交付，无需对照誊抄', '已支持'),
    ]),
    ('管理后台', [
        ('数据看板', '可视化展示系统运行状态、审核效果指标（准确率/处理量/耗时趋势）、问题分布热力图，管理层打开即可掌握系统价值', '已支持'),
        ('规则管理', '业务专家通过图形界面自主维护审核规则，支持规则的增删改查、启用停用、版本追溯，无需技术人员介入', '已支持'),
        ('场景管理', '不同业务线、不同文档类型可配置独立审核场景，各场景拥有独立规则集，互不干扰，灵活适配多业务需求', '已支持'),
        ('用户权限管理', '支持用户登录认证、多角色管控（审核员/管理员/只读）、数据隔离——每个用户仅可见其权限范围内的文档与结果', '已支持'),
    ]),
    ('安全合规', [
        ('数据加密', '传输层采用 TLS/SSL 加密，存储层采用 AES-256 高强度加密，确保数据在传输和静态存储时的全链路安全', '已支持'),
        ('访问控制与审计', '基于角色的访问控制（RBAC），所有关键操作（上传/审核/规则修改/用户登录）记录审计日志，满足内部合规与外部监管要求', '已支持'),
        ('私有化部署', '支持客户内网私有化部署，文档数据不出客户网络，满足金融等高安全要求行业的数据主权需求', '已支持'),
    ]),
    ('扩展能力', [
        ('多语种文档支持', '规划支持英文、日文等多语种文档审核，覆盖跨境业务场景', '规划中'),
        ('版本智能比对', '支持同一文档草稿与终稿的自动比对，识别实质性修改（条款变动、金额调整、主体变更），区分格式修改与内容修改', '规划中'),
        ('OA / CMS 集成', '支持与企业内部办公系统、合同管理系统对接，审核请求和结果双向流转，嵌入现有业务流程无需改变用户习惯', '规划中'),
        ('批量审核', '支持同时提交多份文档进入审核队列，系统并发处理，50 份文档同时审核不排队', '已支持'),
    ]),
]

row = 1
total_start = 1
for cat, items in data:
    start_row = row
    for i, (scene, desc, status) in enumerate(items):
        ws.set_row(row, max(45, len(desc) // 5 * 3))
        ws.write(row, 2, scene, scene_fmt)
        ws.write(row, 3, desc, desc_fmt)
        fmt = status_yes if status == '已支持' else status_plan
        ws.write(row, 4, status, fmt)
        row += 1
    if len(items) > 1:
        ws.merge_range(start_row, 1, row - 1, 1, cat, cat_fmt)
    else:
        ws.write(start_row, 1, cat, cat_fmt)

# A 列整体合并为"文档审核助手"
ws.merge_range(total_start, 0, row - 1, 0, '文档审核助手', cat_fmt)

wb.close()
print(f'Done: {DST}')
print(f'Categories: {len(data)}, Total rows: {row - 1}')
