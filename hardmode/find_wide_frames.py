import re
import sys
import zipfile

apk = sys.argv[1]
z = zipfile.ZipFile(apk)
for name in [n for n in z.namelist() if n.endswith('.plist') and 'HD/Atlas' in n]:
    text = z.read(name).decode('utf-8', 'ignore')
    frames = re.findall(
        r'<key>([^<]+)</key>\s*<dict>.*?<key>spriteSourceSize</key>\s*<string>\{([^}]+)\}</string>.*?</dict>',
        text, re.S)
    big = []
    for key, size in frames:
        try:
            w, h = [int(v.strip()) for v in size.split(',')]
        except Exception:
            continue
        if w >= 900 or h >= 500:
            big.append((key, w, h))
    if big:
        print('===', name, '===')
        for key, w, h in big:
            print(f'{w}x{h}  {key}')
