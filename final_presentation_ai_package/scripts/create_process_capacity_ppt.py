from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_THEME_COLOR

OUT = '/home/hegelty/programming/IMEN376/final_presentation_ai_package/process_capacity_bottleneck_2page.pptx'

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Colors
NAVY = RGBColor(15, 36, 64)
BLUE = RGBColor(38, 92, 160)
CYAN = RGBColor(86, 165, 215)
LIGHT = RGBColor(242, 246, 250)
GRAY = RGBColor(93, 107, 122)
DARK = RGBColor(35, 45, 55)
ORANGE = RGBColor(230, 126, 34)
RED = RGBColor(192, 57, 43)
GREEN = RGBColor(39, 174, 96)
WHITE = RGBColor(255,255,255)

FONT = 'Malgun Gothic'

def set_text(tf, text, size=18, color=DARK, bold=False, align=None, line_spacing=None):
    tf.clear()
    p=tf.paragraphs[0]
    r=p.add_run()
    r.text=text
    r.font.name=FONT
    r.font.size=Pt(size)
    r.font.color.rgb=color
    r.font.bold=bold
    if align:
        p.alignment=align
    if line_spacing:
        p.line_spacing=line_spacing
    return p

def add_box(slide, x,y,w,h, fill=LIGHT, line=None, radius=False):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line or fill
    return shape

def add_textbox(slide, x,y,w,h,text,size=16,color=DARK,bold=False,align=None):
    tb=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.text_frame.margin_left = Inches(0.05)
    tb.text_frame.margin_right = Inches(0.05)
    tb.text_frame.margin_top = Inches(0.03)
    tb.text_frame.margin_bottom = Inches(0.03)
    tb.text_frame.word_wrap = True
    set_text(tb.text_frame, text, size, color, bold, align)
    return tb

# Slide 1
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_box(slide,0,0,13.333,0.55,NAVY)
add_textbox(slide,0.45,0.11,9.8,0.35,'OB Cass Process Capacity Estimate: Public Large-Brewery Normalization',18,WHITE,True)
add_textbox(slide,10.65,0.13,2.45,0.3,'IMEN376 Proposal Support',11,WHITE,False,PP_ALIGN.RIGHT)

add_textbox(slide,0.55,0.72,12.0,0.38,'Key idea: OB process data are private; normalize public large-lager benchmarks to an OB production proxy',17,NAVY,True)

# left formula panel
add_box(slide,0.55,1.28,4.2,5.57,RGBColor(236,243,250),RGBColor(210,225,240),True)
add_textbox(slide,0.8,1.58,3.7,0.35,'1) OB production proxy',15,NAVY,True)
formula = '2024 Korea beer shipments\n1,637,210 kL/year\n× OB home-market share 55.3%\n≈ 905,377 kL/year\n= 9.05 million hL/year'
add_textbox(slide,0.85,2.03,3.55,1.25,formula,14,DARK)
add_textbox(slide,0.8,3.47,3.7,0.35,'2) Scale factor',15,NAVY,True)
add_textbox(slide,0.85,3.9,3.55,0.75,'OB proxy / Alrode capacity\n= 9.05 / 8.8 ≈ 1.029',15,DARK)
add_textbox(slide,0.8,5.0,3.7,0.35,'3) Planning load',15,NAVY,True)
add_textbox(slide,0.85,5.42,3.55,1.0,'176,000 hL/week × 1.029 / 7 × 87%\n≈ 22,505 hL/day\n= 7.5 standard batches/day',14,DARK)

# right benchmark cards
cards = [
    ('SAB Alrode Brewery', '8.8 million hL/year\n176,000 hL/week brewing\n205,000 hL/week packaging\n96 fermentation + 60 maturation vessels\neach vessel 3,000 hL'),
    ('AB InBev Leuven / GEA', 'New cold block: 36 tanks\n116 total tanks after expansion\nTank sizes: 2,700–4,700 hL\nCentrifuge: 600–700 hL/hour'),
    ('Steinecker / Krones', 'Steinecker mash filter:\n14 brews/day output\nKrones bottle filler:\nup to 78,000 containers/hour')
]
xs=[5.05,7.75,10.45]
for i,(title,body) in enumerate(cards):
    add_box(slide,xs[i],1.35,2.45,3.35,WHITE,RGBColor(210,225,240),True)
    add_textbox(slide,xs[i]+0.15,1.58,2.15,0.5,title,14,NAVY,True,PP_ALIGN.CENTER)
    add_textbox(slide,xs[i]+0.2,2.25,2.05,1.95,body,12,DARK)

add_box(slide,5.05,4.95,7.9,1.9,RGBColor(255,248,235),RGBColor(245,210,150),True)
add_textbox(slide,5.3,5.15,7.45,0.35,'Normalization logic',16,ORANGE,True)
add_textbox(slide,5.3,5.6,7.45,0.95,'Do not copy the plant-level 87% operating rate into every process.\nUse 87% only for planning load; estimate process capacities from equipment rated speeds or tank residence times.',15,DARK)

add_textbox(slide,0.55,7.05,12.4,0.25,'Sources: SASSDA Alrode Brewery; GEA AB InBev Leuven; Steinecker mash filter; Krones filling lines',8,GRAY)

# Slide 2
slide = prs.slides.add_slide(prs.slide_layouts[6])
add_box(slide,0,0,13.333,0.55,NAVY)
add_textbox(slide,0.45,0.11,9.2,0.35,'Process Utilization: Bottleneck is the Fermentation-Centered Cold Block',18,WHITE,True)
add_textbox(slide,10.9,0.13,2.1,0.3,'2-page summary',11,WHITE,False,PP_ALIGN.RIGHT)

add_textbox(slide,0.55,0.75,12.1,0.45,'Planning load = 7.5 standard batches/day. Capacity is estimated from process-specific public benchmarks.',17,NAVY,True)

# Table left
headers=['Stage','Capacity','Util.','Interpretation']
rows=[
 ('Milling/Mashing/Lautering','14.0 b/d','54%','Slack'),
 ('Boiling/Cooling','12.0 b/d','63%','Not constraining'),
 ('Fermentation','~8.0 b/d','94%','Primary bottleneck'),
 ('Maturation','~8.6 b/d','87%','Secondary constraint'),
 ('Final filtration','9.6–11.2 b/d','67–78%','Some slack'),
 ('Bright beer holding','~13.0 b/d','58%','Buffer'),
 ('Packaging','~10.0 b/d','75%','Slack')]

x0,y0,w,h=0.55,1.35,6.15,4.75
add_box(slide,x0,y0,w,h,WHITE,RGBColor(210,225,240),False)
# header row
colw=[2.25,1.35,0.9,1.5]
cur=x0
for j,head in enumerate(headers):
    add_box(slide,cur,y0,colw[j],0.42,NAVY,NAVY)
    add_textbox(slide,cur+0.03,y0+0.08,colw[j]-0.06,0.22,head,10,WHITE,True,PP_ALIGN.CENTER)
    cur += colw[j]
rowh=0.59
for i,row in enumerate(rows):
    y=y0+0.42+i*rowh
    fill = RGBColor(255,242,235) if row[0]=='Fermentation' else (RGBColor(255,248,235) if row[0]=='Maturation' else RGBColor(248,251,253))
    cur=x0
    for j,val in enumerate(row):
        add_box(slide,cur,y,colw[j],rowh,fill,RGBColor(225,232,238),False)
        color = RED if row[0]=='Fermentation' and j in (0,2,3) else (ORANGE if row[0]=='Maturation' and j in (0,2,3) else DARK)
        bold = row[0] in ('Fermentation','Maturation')
        add_textbox(slide,cur+0.04,y+0.12,colw[j]-0.08,0.34,val,10,color,bold,PP_ALIGN.CENTER if j>0 else None)
        cur += colw[j]

# Bar chart right
add_box(slide,7.05,1.35,5.75,4.75,WHITE,RGBColor(210,225,240),True)
add_textbox(slide,7.25,1.55,5.25,0.35,'Utilization comparison',15,NAVY,True)
bar_data=[('Milling/Mashing',54,GREEN),('Boiling/Cooling',63,GREEN),('Final filtration',75,BLUE),('Packaging',75,BLUE),('Maturation',87,ORANGE),('Fermentation',94,RED)]
maxw=3.8
for i,(name,val,col) in enumerate(bar_data):
    y=2.05+i*0.55
    add_textbox(slide,7.25,y,1.25,0.25,name,10,DARK,False,PP_ALIGN.RIGHT)
    add_box(slide,8.65,y+0.04,maxw,0.18,RGBColor(232,236,241),RGBColor(232,236,241),False)
    add_box(slide,8.65,y+0.04,maxw*val/100,0.18,col,col,False)
# red line marker 85%
marker_x=8.65+maxw*0.85
line=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(marker_x), Inches(1.95), Inches(0.02), Inches(3.55))
line.fill.solid(); line.fill.fore_color.rgb=RGBColor(120,120,120); line.line.color.rgb=RGBColor(120,120,120)
add_textbox(slide,marker_x-0.25,5.52,0.7,0.22,'85%',8,GRAY,False,PP_ALIGN.CENTER)

# value labels on top of bars (white-backed for LibreOffice rendering)
for i,(name,val,col) in enumerate(bar_data):
    y=2.05+i*0.55
    add_box(slide,12.02,y+0.01,0.48,0.26,WHITE,RGBColor(220,225,230),False)
    add_textbox(slide,12.05,y+0.04,0.42,0.18,f'{val}%',8,DARK,True,PP_ALIGN.CENTER)

add_box(slide,0.55,6.3,12.25,0.75,RGBColor(236,243,250),RGBColor(210,225,240),True)
add_textbox(slide,0.8,6.43,11.75,0.38,'Conclusion: upstream brewing and packaging have line-speed slack, but fermentation ties up tanks for 13–14 days and reaches ~94% utilization. The dominant bottleneck is the fermentation-centered cold block.',14,NAVY,True,PP_ALIGN.CENTER)

prs.save(OUT)
print(OUT)
