# Rebuilds the whole Battle of Spades project folder from one game file (battleofspades.html).
# Usage: python3 tools/restore.py GAMEFILE.html OUTDIR
# The game file holds every source module of the page (marked "// ==== path ===="), the styles, the page,
# the patch notes, and a compressed bundle of everything else (launcher, tools, notes, the dedicated
# server's src/server/ files, modules only the server uses, README and LICENSE). It also carries the built
# headless server (id="bos-server"), which isn't needed here: tools/build.js makes it again.
# Icons (launcher/icons/*.png) are not in it: run `python3 launcher/make_icons.py` to draw them again.
# This is the inverse of tools/build.js: building the restored folder gives the same game file back.
import sys, os, re, json, gzip, base64, subprocess

src, out = sys.argv[1], sys.argv[2]
full = open(src, encoding='utf-8').read()
os.makedirs(out, exist_ok=True)
def write(rel, text):
    p = os.path.join(out, rel); os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    open(p, 'w', encoding='utf-8', newline='').write(text)

# 1. the bundled extras (and the built server, which is just dropped)
m = re.search(r'<script type="application/octet-stream" id="bos-sources"[^>]*>([^<]+)</script>\n', full)
if not m: sys.exit('No bundled sources in ' + src + ': is it a Battle of Spades game file?')
extras = json.loads(gzip.decompress(base64.b64decode(m.group(1))))
for rel, text in extras.items(): write(rel, text)
full = full[:m.start()] + full[m.end():]
m = re.search(r'<script type="application/octet-stream" id="bos-server"[^>]*>[^<]*</script>\n', full)
if m: full = full[:m.start()] + full[m.end():]
# 2. the page body: index.html with its markers, styles, patch notes, script
body = full[full.index('<body>\n') + 7: full.rindex('\n</body>')]
s1 = body.index('<style>') + len('<style>')
s2 = body.index('</style>', s1)
css = body[s1:s2]
n1 = body.index('<template id="bos-news">') + len('<template id="bos-news">')
n2 = body.index('</template>', n1)
j1 = body.index('<script>(function () {') + len('<script>')
j2 = body.rindex('})();</script>') + len('})();')
index = body[:s1] + '/*STYLES*/' + body[s2:n1] + '/*NEWS*/' + body[n2:j1] + '/*SCRIPT*/' + body[j2:]
write('src/index.html', index)
write('src/styles.css', css)
if not os.path.exists(os.path.join(out, 'launcher/news.html')): write('launcher/news.html', body[n1:n2] + '\n')
# 3. the modules
head, tail = "(function () {\n'use strict';\n", "\n})();"
js = body[j1:j2]
assert js.startswith(head) and js.endswith(tail), 'the script is not a Battle of Spades bundle'
js = js[len(head):-len(tail)]
parts = re.split(r'^// ==== (.+?) ====\n', js, flags=re.M)
names, texts = parts[1::2], parts[2::2]
for i, (n, t) in enumerate(zip(names, texts)):
    if i < len(names) - 1: t = t[:-1]
    write('src/js/' + n, t)
print('restored', len(names), 'modules and', len(extras), 'other files into', out)
# the module order must be the one tools/order.js gives the page (CLIENT_ORDER), or the rebuild differs
try:
    order = json.loads(subprocess.run(['node', '-e', 'console.log(JSON.stringify(require(process.argv[1]).CLIENT_ORDER))', os.path.abspath(os.path.join(out, 'tools/order.js'))],
                                      capture_output=True, text=True, check=True).stdout)
    if order != names: sys.exit('tools/order.js CLIENT_ORDER does not match the modules in the game file:\n  order.js: ' + ', '.join(order) + '\n  file:     ' + ', '.join(names))
    print('module order matches tools/order.js')
except (OSError, subprocess.CalledProcessError, ValueError):
    print('module order (check tools/order.js CLIENT_ORDER matches):', ', '.join(names))
