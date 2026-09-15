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
import json, re, shutil, sys, html, zipfile, hashlib
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
    global NAV
    if NAV is None: NAV = nav_html()
    return write(rel, render(
        BASE, nav=NAV,
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
def asset_version(rel):
    return hashlib.sha1((ROOT / "static" / rel).read_bytes()).hexdigest()[:10]

BASE = (read("templates/base.html")
        .replace('href="/css/site.css"', f'href="/css/site.css?v={asset_version("css/site.css")}"')
        .replace('src="/js/site.js"', f'src="/js/site.js?v={asset_version("js/site.js")}"'))
GAMES = load("games")
OCCASIONS = load("occasions")
FAQ = load("faq")
AREAS = load("areas")
BY_SLUG = {g["slug"]: g for g in GAMES}
PACKAGES = [  # mirrors the cards in templates/home.html
    ("Option 1", 1550, ["Any 2 Available Big Games", "Any 2 Available Medium Games", "Any 2 Available Small Games"]),
    ("Option 2", 1350, ["Any 2 Available Big Games", "Any 2 Available Medium Games", "Any 1 Available Small Game"]),
    ("Option 3", 1000, ["Any 1 Available Big Game", "Any 2 Available Medium Games", "Any 2 Available Small Games"]),
    ("Option 4",  800, ["Any 1 Available Big Game", "Any 1 Available Medium Game", "Any 1 Available Small Game"]),
]
for g in GAMES:
    g["url"] = f"/games/{g['page']}/"
for o in OCCASIONS:
    o["url"] = f"/{o['slug']}/"

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

def faq_html(pairs, indent="        "):
    return "\n".join(f'{indent}<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in pairs)

def faq_schema(pairs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}

def breadcrumb(*items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE_URL + u} for i, (n, u) in enumerate(items)]}

def related_cards(games):
    return "\n".join(
        f'        <a class="related-card" href="{o["url"]}">'
        f'<img src="/{o["image"]}-400.webp" alt="" width="400" height="{round(400 * o["img_h"] / o["img_w"])}" loading="lazy">'
        f'<div><strong>{esc(o["name"])}</strong><span>R{o["price"]} · {o["size"].split()[0]}</span></div></a>'
        for o in games)

CHEVRON = ('<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
           '<path d="M3 6l5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>')

def nav_html():
    def sub_toggle(label):
        return (f'<button class="sub-toggle" type="button" aria-expanded="false" aria-label="Show {label}">'
                f'{CHEVRON}</button>')
    games = "\n".join(f'          <li><a href="{g["url"]}">{esc(g["name"])}</a></li>' for g in GAMES)
    occasions = "\n".join(f'          <li><a href="{o["url"]}">{esc(o["name"])}</a></li>' for o in OCCASIONS)
    return f'''    <nav id="primary-nav" aria-label="Main">
      <ul>
        <li><a href="/#home">Home</a></li>
        <li><a href="/#about">About</a></li>
        <li class="has-sub">
          <a href="/#games">The Games</a>{sub_toggle("all games")}
          <ul class="sub sub-games">
            <li class="sub-all"><a href="/#games">All lawn games for hire</a></li>
{games}
          </ul>
        </li>
        <li class="has-sub">
          <a href="/#occasions">Occasions</a>{sub_toggle("occasions")}
          <ul class="sub">
{occasions}
          </ul>
        </li>
        <li><a href="/#packages">Event Packages</a></li>
        <li><a href="/#design">Design Services</a></li>
        <li><a href="/#info">Guidelines</a></li>
        <li><a href="/#contact" class="nav-cta">Book Online</a></li>
      </ul>
    </nav>'''

NAV = None

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
    occasion_cards = "\n".join(
        f'        <a class="occasion-card" href="{o["url"]}"><h3>{esc(o["name"])}</h3><p>{esc(o["lead"].split(". ")[0])}.</p>'
        f'<span>{esc(o["short"])} →</span></a>' for o in OCCASIONS)
    areas = '          <div class="areas">\n' + "\n".join(
        f'            <div><strong>{esc(k)}:</strong> {esc(", ".join(v))}</div>' for k, v in AREAS.items()) + '\n          </div>'
    content = render(read("templates/home.html"), game_cards="\n".join(cards),
                     occasion_cards=occasion_cards, areas=areas, faqs=faq_html(FAQ))
    head_extra = '''<!-- Hero photo: tell the browser before it reads the CSS, so it starts first. -->
<link rel="preload" as="image" href="/images/bg_4.webp" type="image/webp" media="(min-width: 700px)">
<link rel="preload" as="image" href="/images/bg_4-mobile.webp" type="image/webp" media="(max-width: 699px)">'''
    return page("index.html",
        title="Lawn Game Hire Pretoria & Johannesburg | Lawn Game Rentals",
        og_title="Giant Lawn Game Hire in Pretoria & Johannesburg | Lawn Game Rentals",
        description="Hire giant lawn games - cornhole, croquet, 4-in-a-row and more - for weddings, parties and corporate events in Pretoria, Johannesburg and Gauteng.",
        canonical_path="/", content=content, jsonld=[local_business(with_catalog=True), faq_schema(FAQ)],
        body_class="page-home", head_extra=head_extra)

def build_game(g):
    size_word = g["size"].split()[0].lower()          # "Big (B)" -> "big"
    h1 = f'{g["name"]} Hire' if g["common"] in g["name"].lower() else f'{g["name"]} ({g["common"].split(" / ")[0].title()}) Hire'
    intro = "\n".join(f"        <p>{esc(p)}</p>" for p in g["intro"])
    rules = "\n".join(f"          <li>{esc(r)}</li>" for r in g["rules"])
    faqs = faq_html(g["faqs"])
    # Three other games, preferring the same size class so packages make sense.
    others = [o for o in GAMES if o is not g]
    others.sort(key=lambda o: (o["size"] != g["size"], GAMES.index(o)))
    related = related_cards(others[:3])

    content = render(read("templates/game.html"),
        name=esc(g["name"]), h1=esc(h1), size=g["size"].split()[0], size_word=size_word, price=g["price"],
        picture=picture(g, sizes="(max-width: 800px) 100vw, 640px", loading="eager"),
        players=esc(g["players"]), ages=esc(g["ages"]), space=esc(g["space"]), surface=esc(g["surface"]),
        duration=esc(g["duration"]), weather=esc(g["weather"]),
        intro=intro, rules=rules, includes=esc(g["includes"]), faqs=faqs, related=related, wa_link=WA_LINK)

    jsonld = [
        {"@context": "https://schema.org", "@type": "Product",
         "name": g["name"], "alternateName": g["common"], "description": g["intro"][0],
         "image": BASE_URL + "/" + g["image"] + ".webp", "url": BASE_URL + g["url"],
         "brand": {"@type": "Brand", "name": "Lawn Game Rentals"},
         "offers": {"@type": "Offer", "price": str(g["price"]), "priceCurrency": "ZAR",
                    "availability": "https://schema.org/InStock", "url": BASE_URL + g["url"],
                    "businessFunction": "http://purl.org/goodrelations/v1#LeaseOut",
                    "areaServed": ["Pretoria", "Johannesburg", "Centurion", "Midrand", "Gauteng"],
                    "seller": {"@id": BASE_URL + "/#business"}}},
        breadcrumb(("Home", "/"), ("Lawn Games for Hire", "/#games"), (g["name"], g["url"])),
        faq_schema(g["faqs"]),
        local_business(with_catalog=False),
    ]
    return page(g["url"].lstrip("/") + "index.html",
        title=g["title"], description=g["description"], canonical_path=g["url"],
        og_image="/" + g["image"] + ".webp", og_alt=g["alt"],
        content=content, jsonld=jsonld, body_class="page-game")

def build_occasion(o):
    sections = "\n".join(f"        <h2>{esc(h)}</h2>\n        <p>{body}</p>" for h, body in o["sections"])
    content = render(read("templates/occasion.html"),
        name=esc(o["name"]), h1=esc(o["h1"]), lead=esc(o["lead"]), sections=sections,
        games=related_cards([BY_SLUG[s] for s in o["games"]]), faqs=faq_html(o["faqs"]))
    jsonld = [breadcrumb(("Home", "/"), (o["name"], o["url"])), faq_schema(o["faqs"]), local_business(with_catalog=False)]
    return page(o["url"].lstrip("/") + "index.html", title=o["title"], description=o["description"],
                canonical_path=o["url"], content=content, jsonld=jsonld, body_class="page-occasion")

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
    for g in GAMES:
        build_game(g); paths.append(g["url"])
    for o in OCCASIONS:
        build_occasion(o); paths.append(o["url"])
    build_sitemap(paths)
    n = sum(1 for p in DIST.rglob("*") if p.is_file())
    print(f"built {len(paths)} page(s), {n} files -> dist/")
    if "--zip" in sys.argv:
        print("wrote", make_zip().name)

if __name__ == "__main__":
    main()
