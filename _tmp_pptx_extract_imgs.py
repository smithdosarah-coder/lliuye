# -*- coding: utf-8 -*-
import sys, io, zipfile, os, re, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pptx_path = r"C:/Users/Mr.S/xwechat_files/wxid_r0ty34wac6bt22_7a6c/msg/file/2026-04/Viktor-分享pptx.pptx"
out_dir = r"D:/claude code/credit_report_agent_work/_viktor_images"

if os.path.exists(out_dir):
    shutil.rmtree(out_dir)
os.makedirs(out_dir)

with zipfile.ZipFile(pptx_path) as z:
    # For each slide 10-42, find the rels file to know which picture it references
    for slide_num in range(10, 43):
        slide_rels = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
        if slide_rels not in z.namelist():
            continue
        with z.open(slide_rels) as f:
            content = f.read().decode('utf-8')
        # Find picture Targets
        pics = re.findall(r'Target="\.\./media/([^"]+)"', content)
        if not pics:
            continue
        # Extract first picture
        pic_name = pics[0]
        src = f"ppt/media/{pic_name}"
        if src in z.namelist():
            ext = os.path.splitext(pic_name)[1]
            dst = os.path.join(out_dir, f"slide{slide_num:02d}{ext}")
            with z.open(src) as f:
                with open(dst, 'wb') as out:
                    out.write(f.read())
            size = os.path.getsize(dst) // 1024
            print(f"slide {slide_num}: {pic_name} -> {dst} ({size} KB)")

print(f"\nAll saved to: {out_dir}")
