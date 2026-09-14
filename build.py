#!/usr/bin/env python3
"""
Builds the Lawn Game Rentals site into dist/.

    python3 build.py          # build
    python3 build.py --zip    # build and also write lawngamerentals-site.zip

Layout
    templates/   page shells; {{placeholders}} are filled from content/
    content/     the data: games, occasions, FAQ, areas served
    static/      copied to dist/ verbatim (images, css, js, .htaccess, robots.txt)
    dist/        the output; this is what gets deployed. Never edit it by hand.

No dependencies beyond the Python 3 standard library, on purpose.
"""
import json, re, shutil, sys, html, zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BASE_URL = "https://www.lawngamerentals.co.za"
TODAY = date.today().isoformat()

WA_NUMBER = "27817566989"
WA_LINK = f"https://wa.me/{WA_NUMBER}?text=Hi%20Lawn%20Game%20Rentals%2C%20I%27d%20like%20to%20enquire%20about%20a%20booking."

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def read(p): return (ROOT / p).read_text(encoding="utf-8")
def load(name): return json.loads(read(f"content/{name}.json"))
def esc(s): return html.escape(s, quote=True)

def render(template, **ctx):
    """Replace every {{key}}; a key the template needs but ctx lacks is a bug."""
    def sub(m):
        k = m.group(1)
        if k not in ctx: raise KeyError(f"template needs {{{{{k}}}}}")
        return str(ctx[k])
    return re.sub(r"\{\{(\w+)\}\}", sub, template)

def write(rel, text):
    p = DIST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return rel

def page(rel, *, title, description, canonical_path, content, jsonld, og_title=None,
         og_image="/images/og-image.jpg", og_alt="Lawn Game Rentals logo over a sunlit lawn",
         body_class="", head_extra=""):
    return write(rel, render(
        BASE,
        title=esc(title), description=esc(description),
        canonical=BASE_URL + canonical_path, og_title=esc(og_title or title),
        og_image=BASE_URL + og_image, og_alt=esc(og_alt),
        head_extra=head_extra, body_class=body_class, content=content,
        jsonld=json.dumps(jsonld, indent=2, ensure_ascii=False),
    ))

def picture(g, *, sizes, loading="lazy", cls=""):
    """<picture> with 400/800 WebP variants and the PNG fallback."""
    base = "/" + g["image"]
    return (
        f'<picture{(" class=" + chr(34) + cls + chr(34)) if cls else ""}>\n'
        f'  <source type="image/webp" srcset="{base}-400.webp 400w, {base}.webp 800w" sizes="{sizes}">\n'
        f'  <img src="{base}.png" alt="{esc(g["alt"])}" width="{g["img_w"]}" height="{g["img_h"]}" '
        f'loading="{loading}" decoding="async">\n'
        f'</picture>'
    )

# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
BASE = read("templates/base.html")
GAMES = load("games")
PACKAGES = [  # mirrors the cards in templates/home.html
    ("Option 1", 1550, ["Any 2 Available Big Games", "Any 2 Available Medium Games", "Any 2 Available Small Games"]),
    ("Option 2", 1350, ["Any 2 Available Big Games", "Any 2 Available Medium Games", "Any 1 Available Small Game"]),
    ("Option 3", 1000, ["Any 1 Available Big Game", "Any 2 Available Medium Games", "Any 2 Available Small Games"]),
    ("Option 4",  800, ["Any 1 Available Big Game", "Any 1 Available Medium Game", "Any 1 Available Small Game"]),
]
for g in GAMES:
    g["url"] = f"/games/{g['page']}/"

def offer(name, desc, price, image=None, url=None):
    item = {"@type": "Product", "name": name, "description": desc}
    if image: item["image"] = BASE_URL + image
    if url: item["url"] = BASE_URL + url
    return {"@type": "Offer", "itemOffered": item, "price": str(price), "priceCurrency": "ZAR",
            "availability": "https://schema.org/InStock",
            "businessFunction": "http://purl.org/goodrelations/v1#LeaseOut"}

def local_business(with_catalog):
    lb = {
        "@context": "https://schema.org", "@type": "LocalBusiness", "@id": BASE_URL + "/#business",
        "name": "Lawn Game Rentals", "legalName": "Shaun's Events",
        "description": "Giant lawn game hire for weddings, parties and corporate events across Pretoria, Johannesburg and Gauteng.",
        "url": BASE_URL + "/", "logo": BASE_URL + "/images/logolgrw.svg", "image": BASE_URL + "/images/og-image.jpg",
        "email": "shaun@lawngamerentals.co.za", "telephone": "+27817566989",
        "contactPoint": [
            {"@type": "ContactPoint", "contactType": "customer service", "telephone": "+27817566989", "availableLanguage": "en"},
            {"@type": "ContactPoint", "contactType": "customer service", "telephone": "+27615107256", "availableLanguage": "en"},
            {"@type": "ContactPoint", "contactType": "customer service", "name": "WhatsApp", "telephone": "+27817566989",
             "url": f"https://wa.me/{WA_NUMBER}", "availableLanguage": "en"},
        ],
        "priceRange": "R150 - R1550", "currenciesAccepted": "ZAR",
        "areaServed": [{"@type": "City", "name": c} for c in ("Pretoria", "Johannesburg", "Centurion", "Midrand")]
                      + [{"@type": "AdministrativeArea", "name": "Gauteng"}],
        "address": {"@type": "PostalAddress", "addressRegion": "Gauteng", "addressCountry": "ZA"},
    }
    if with_catalog:
        lb["hasOfferCatalog"] = {"@type": "OfferCatalog", "name": "Lawn Game Hire", "itemListElement": [
            {"@type": "OfferCatalog", "name": "Individual Games",
             "itemListElement": [offer(g["name"], g["blurb"], g["price"], "/" + g["image"] + ".webp", g["url"]) for g in GAMES]},
            {"@type": "OfferCatalog", "name": "Event Packages",
             "itemListElement": [offer(f"Event Package {n}", ", ".join(items) + ". Includes a free custom WhatsApp invitation.", p)
                                 for n, p, items in PACKAGES]},
        ]}
    return lb

# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------
def build_home():
    cards = []
    for g in GAMES:
        cards.append(f'''
        <div class="game-card">
          <div class="game-img-placeholder">
            <span class="size-tag">{g["size"]}</span>
            {picture(g, sizes="(max-width: 600px) 100vw, 380px")}
          </div>
          <div class="game-content">
            <h3><a href="{g["url"]}">{esc(g["name"])}</a></h3>
            <div class="game-price">R{g["price"]} + R{g["price"]} Deposit</div>
            <p>{esc(g["blurb"])}</p>
            <div class="game-includes"><strong>Includes:</strong> {esc(g["includes"])}</div>
            <a class="game-more" href="{g["url"]}">Rules, sizes &amp; details <span aria-hidden="true">→</span></a>
          </div>
        </div>''')
    content = render(read("templates/home.html"), game_cards="\n".join(cards))
    head_extra = '''<!-- Hero photo: tell the browser before it reads the CSS, so it starts first. -->
<link rel="preload" as="image" href="/images/bg_4.webp" type="image/webp" media="(min-width: 700px)">
<link rel="preload" as="image" href="/images/bg_4-mobile.webp" type="image/webp" media="(max-width: 699px)">'''
    return page("index.html",
        title="Lawn Game Hire Pretoria & Johannesburg | Lawn Game Rentals",
        og_title="Giant Lawn Game Hire in Pretoria & Johannesburg | Lawn Game Rentals",
        description="Hire giant lawn games — cornhole, croquet, 4-in-a-row and more — for weddings, parties and corporate events in Pretoria, Johannesburg and Gauteng.",
        canonical_path="/", content=content, jsonld=local_business(with_catalog=True),
        body_class="page-home", head_extra=head_extra)

def build_sitemap(paths):
    urls = "\n".join(
        f"  <url>\n    <loc>{BASE_URL}{p}</loc>\n    <lastmod>{TODAY}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n    <priority>{'1.0' if p == '/' else '0.8'}</priority>\n  </url>"
        for p in paths)
    return write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n'
                 f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n')

def copy_static():
    for src in (ROOT / "static").rglob("*"):
        if src.is_file() and src.name != ".DS_Store":
            dst = DIST / src.relative_to(ROOT / "static")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

def make_zip():
    out = ROOT / "lawngamerentals-site.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DIST.rglob("*")):
            if p.is_file(): z.write(p, p.relative_to(DIST))
    return out

def main():
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir()
    copy_static()
    paths = ["/"]
    build_home()
    build_sitemap(paths)
    n = sum(1 for p in DIST.rglob("*") if p.is_file())
    print(f"built {len(paths)} page(s), {n} files -> dist/")
    if "--zip" in sys.argv:
        print("wrote", make_zip().name)

if __name__ == "__main__":
    main()
