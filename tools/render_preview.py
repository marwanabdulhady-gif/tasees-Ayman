import pymupdf, os, sys
from PIL import Image, ImageOps, ImageDraw
os.makedirs('.cache/preview', exist_ok=True)
BIG='google_drive/الأطلس التاريخي لسيرة الرسول.pdf'
SMALL='google_drive/خرائط التاريخ الإسلامي مجمع.pdf'

def render(doc, i, scale=1.6):
    p=doc[i]
    pm=p.get_pixmap(matrix=pymupdf.Matrix(scale,scale), alpha=False)
    return Image.frombytes('RGB',(pm.width,pm.height),pm.samples)

def contact(doc, indices, out, cols=6, tw=170, th=240):
    rows=(len(indices)+cols-1)//cols
    sheet=Image.new('RGB',(cols*tw,rows*(th+22)), '#e8e4dc')
    d=ImageDraw.Draw(sheet)
    for k,i in enumerate(indices):
        im=render(doc,i,scale=1.0)
        im.thumbnail((tw-8,th-8))
        x=(k%cols)*tw+(tw-im.width)//2; y=(k//cols)*(th+22)+4
        sheet.paste(im,(x,y))
        d.text(((k%cols)*tw+6,(k//cols)*(th+22)+th+2),f'p{i+1}',fill='#222')
    sheet.save(out,quality=82)
    print(out, sheet.size)

if __name__=='__main__':
    big=pymupdf.open(BIG); small=pymupdf.open(SMALL)
    for i in [0,10,12,14,30,50,70,82,120,210,222,254,255,256,257,258,259,260,261,262,263]:
        im=render(big,i,1.6); im.save(f'.cache/preview/big-{i+1:03d}.jpg',quality=85)
    for i in range(8):
        im=render(small,i,1.6); im.save(f'.cache/preview/small-{i+1:03d}.jpg',quality=85)
    contact(big, list(range(0,264,4)), '.cache/preview/contact-big.jpg', cols=10, tw=120, th=170)
    contact(small, list(range(8)), '.cache/preview/contact-small.jpg', cols=4, tw=220, th=310)
