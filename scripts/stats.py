#!/usr/bin/env python3
"""Builds the live contributions charts for the profile README, in the same blueprint style:
  assets/stats.svg    headline numbers + contribution-type donut + 52-week line graph
  assets/langs.svg    languages donut
  assets/weekday.svg  contributions by day of the week
Runs daily from .github/workflows/profile-stats.yml. Standard library only.
"""
import base64, datetime as dt, json, math, os, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Gesare-n")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG, PANEL, INK, DIM, FAINT = "#0b0b0c", "#0f0f11", "#ECEAE4", "#8a8984", "#2b2b2e"
IGNORE_LANGS = {"ShaderLab", "HLSL", "Batchfile", "Procfile"}

# Monochrome categorical styles: identity = lightness + texture + direct label (never shade alone).
STYLES = ["s0", "s1", "s2", "s3", "s4", "s5"]
FIXED = {"Python": "s0", "Jupyter Notebook": "s1", "C#": "s2", "TypeScript": "s3", "JavaScript": "s4", "C++": "s5"}

Q = """query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date weekday } } }
    totalCommitContributions totalPullRequestContributions totalPullRequestReviewContributions totalIssueContributions
    totalRepositoryContributions restrictedContributionsCount }
  repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC, first:100){ totalCount
    nodes{ languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } } } } }"""


def gql():
    token = os.environ.get("STATS_TOKEN") or os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": Q, "variables": {"login": USER}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["data"]["user"]


def fonts():
    out = []
    for fam, fn, w in [("NGHead", "head.woff2", 600), ("NGBody", "body.woff2", 400), ("NGMono", "mono.woff2", 400)]:
        p = os.path.join(ROOT, "assets", "fonts", fn)
        if os.path.exists(p):
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(data:font/woff2;base64,{base64.b64encode(open(p,'rb').read()).decode()}) format('woff2');}}")
    return "".join(out)


CSS = f"""{fonts()}
.h{{font-family:'NGHead','Barlow Condensed','Arial Narrow',sans-serif;font-weight:600;fill:{INK}}}
.b{{font-family:'NGBody','Barlow',Arial,sans-serif;fill:{INK}}}
.m{{font-family:'NGMono',Consolas,monospace;fill:{DIM};letter-spacing:.12em}}
.mi{{font-family:'NGMono',Consolas,monospace;fill:{INK};letter-spacing:.12em}}
.grow{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:g .8s cubic-bezier(.6,.1,.2,1) forwards}}
@keyframes g{{to{{transform:scaleY(1)}}}}
.draw{{stroke-dasharray:1;stroke-dashoffset:1;animation:d 2.2s cubic-bezier(.6,.1,.2,1) forwards}}
@keyframes d{{to{{stroke-dashoffset:0}}}}
.fade{{opacity:0;animation:f .8s ease forwards}}
@keyframes f{{to{{opacity:1}}}}
.spinin{{transform-box:view-box;animation:r 1.2s cubic-bezier(.6,.1,.2,1) forwards;opacity:0}}
@keyframes r{{from{{opacity:0;transform:rotate(-20deg) scale(.92)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{.grow,.draw,.fade,.spinin{{animation:none!important;transform:none!important;opacity:1!important;stroke-dashoffset:0!important}}}}
.s0{{fill:{INK}}}.s1{{fill:url(#hatchA)}}.s2{{fill:#9a9aa0}}.s3{{fill:url(#hatchB)}}.s4{{fill:#5a5a60}}.s5{{fill:url(#dots)}}.s6{{fill:#2f2f33}}
"""

DEFS = (f'<defs>'
        f'<pattern id="hatchA" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{BG}"/><rect width="3" height="6" fill="{INK}"/></pattern>'
        f'<pattern id="hatchB" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(135)"><rect width="6" height="6" fill="{BG}"/><rect width="2" height="6" fill="#9a9aa0"/></pattern>'
        f'<pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="{BG}"/><circle cx="3" cy="3" r="1.4" fill="{INK}"/></pattern>'
        f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}" stop-opacity=".22"/><stop offset="1" stop-color="{INK}" stop-opacity="0"/></linearGradient>'
        f'</defs>')


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title><style>{CSS}</style>{DEFS}<rect width=\"{w}\" height=\"{h}\" fill=\"{BG}\"/>{body}</svg>")


def write(name, s):
    open(os.path.join(ROOT, "assets", name), "w").write(s)


def donut(cx, cy, r_out, r_in, parts):
    """parts: [(label, value, style)] -> segments separated by a 2px surface gap."""
    tot = sum(v for _, v, _ in parts) or 1
    a0, out = -math.pi / 2, []
    for i, (lab, v, st) in enumerate(parts):
        a1 = a0 + 2 * math.pi * v / tot
        large = 1 if a1 - a0 > math.pi else 0
        if v / tot > .9999:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{(r_out+r_in)/2}" fill="none" stroke-width="{r_out-r_in}" class="{st}" style="stroke:{INK}"/>')
        else:
            p = lambda a, r: (cx + r * math.cos(a), cy + r * math.sin(a))
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p(a0, r_out), p(a1, r_out), p(a1, r_in), p(a0, r_in)
            out.append(f'<path class="{st}" stroke="{BG}" stroke-width="2.5" stroke-linejoin="round" d="M{x0:.2f} {y0:.2f}A{r_out} {r_out} 0 {large} 1 {x1:.2f} {y1:.2f}'
                       f'L{x2:.2f} {y2:.2f}A{r_in} {r_in} 0 {large} 0 {x3:.2f} {y3:.2f}Z"><title>{escape(lab)}: {v}</title></path>')
        a0 = a1
    return f'<g class="spinin" style="transform-origin:{cx}px {cy}px">{"".join(out)}</g>'


def legend(x, y, parts, fmt):
    tot = sum(v for _, v, _ in parts) or 1
    out = []
    for i, (lab, v, st) in enumerate(parts):
        yy = y + i * 30
        out.append(f'<g class="fade" style="animation-delay:{.4+i*.08:.2f}s"><rect x="{x}" y="{yy-12}" width="16" height="16" class="{st}" stroke="{FAINT}"/>'
                   f'<text class="b" x="{x+28}" y="{yy+1}" font-size="15">{escape(lab)}</text>'
                   f'<text class="mi" x="{x+250}" y="{yy+1}" font-size="12" text-anchor="end">{fmt(v, tot)}</text></g>')
    return "".join(out)


def main(u=None):
    u = u or gql()
    cc = u["contributionsCollection"]
    weeks_raw = cc["contributionCalendar"]["weeks"]
    days = [d for w in weeks_raw for d in w["contributionDays"]]
    total = cc["contributionCalendar"]["totalContributions"]
    today = dt.date.today().isoformat()
    longest = cur = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif d["date"] == today:
            continue
        else:
            break
    active_days = sum(1 for d in days if d["contributionCount"] > 0)

    # ---------------- stats.svg: numbers + type donut + 52-week line graph
    W, H = 1200, 520
    b = [f'<text class="m" x="40" y="44" font-size="11">CONTRIBUTIONS · LAST 12 MONTHS</text>',
         f'<text class="m" x="{W-40}" y="44" font-size="10" text-anchor="end">UPDATED {today}</text>',
         f'<text class="h fade" x="36" y="150" font-size="112">{total:,}</text>']
    stats = [("CURRENT STREAK", f"{cur} D"), ("LONGEST STREAK", f"{longest} D"), ("ACTIVE DAYS", str(active_days)), ("PUBLIC REPOS", str(u["repositories"]["totalCount"]))]
    for i, (k, v) in enumerate(stats):
        x = 40 + i * 132
        b.append(f'<g class="fade" style="animation-delay:{.2+i*.08:.2f}s"><text class="m" x="{x}" y="196" font-size="9">{k}</text><text class="h" x="{x}" y="230" font-size="30">{escape(v)}</text></g>')
    types = [("Commits", cc["totalCommitContributions"], "s0"), ("Pull requests", cc["totalPullRequestContributions"], "s1"),
             ("Code reviews", cc["totalPullRequestReviewContributions"], "s2"), ("Issues", cc["totalIssueContributions"], "s3"),
             ("New repos", cc["totalRepositoryContributions"], "s4"), ("Private work", cc["restrictedContributionsCount"], "s5")]
    types = [t for t in types if t[1] > 0] or [("No activity yet", 1, "s6")]
    b.append(f'<text class="m" x="640" y="84" font-size="10">CONTRIBUTION TYPES</text>')
    b.append(donut(745, 168, 74, 46, types))
    b.append(f'<text class="h" x="745" y="176" font-size="24" text-anchor="middle">{sum(t[1] for t in types):,}</text>')
    b.append(legend(860, 108, types, lambda v, t: f"{v:,} · {v/t*100:.0f}%"))
    # line graph of weekly totals
    weeks = [(w["contributionDays"][0]["date"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in weeks_raw]
    gx, gy, gw, gh = 70, 300, 1090, 170
    mx = max(max(v for _, v in weeks), 1)
    step = 5 if mx <= 20 else 10 if mx <= 50 else 25 if mx <= 125 else 50
    top = math.ceil(mx / step) * step
    b.append(f'<text class="m" x="40" y="{gy-14}" font-size="10">WEEKLY CONTRIBUTIONS</text>')
    for k in range(0, top + 1, step):
        y = gy + gh - gh * k / top
        b.append(f'<path stroke="{FAINT if k else DIM}" stroke-width="{1 if k else 1.2}" d="M{gx} {y:.1f}H{gx+gw}"/><text class="m" x="{gx-10}" y="{y+4:.1f}" font-size="9" text-anchor="end">{k}</text>')
    pts = [(gx + gw * i / (len(weeks) - 1), gy + gh - gh * v / top) for i, (_, v) in enumerate(weeks)]
    line = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    b.append(f'<path class="fade" fill="url(#area)" d="{line}L{pts[-1][0]:.1f} {gy+gh}L{pts[0][0]:.1f} {gy+gh}Z"/>')
    b.append(f'<path class="draw" pathLength="1" fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round" d="{line}"/>')
    pk = max(range(len(weeks)), key=lambda i: weeks[i][1])
    if weeks[pk][1] > 0:
        px, py = pts[pk]
        b.append(f'<g class="fade" style="animation-delay:1.6s"><circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{INK}" stroke="{BG}" stroke-width="2"/>'
                 f'<path stroke="{DIM}" stroke-dasharray="2 3" d="M{px:.1f} {py+8:.1f}V{gy+gh}"/>'
                 f'<text class="mi" x="{min(max(px, gx+60), gx+gw-60):.1f}" y="{py-12:.1f}" font-size="11" text-anchor="middle">PEAK {weeks[pk][1]}</text></g>')
    last_m = None
    for i, (d0, _) in enumerate(weeks):
        m = d0[:7]
        if m != last_m and i > 0:
            x = gx + gw * i / (len(weeks) - 1)
            label = dt.date.fromisoformat(d0).strftime("%b").upper()
            b.append(f'<path stroke="{DIM}" d="M{x:.1f} {gy+gh}v5"/><text class="m" x="{x:.1f}" y="{gy+gh+20}" font-size="9" text-anchor="middle">{label}</text>')
        last_m = m
    write("stats.svg", svg(W, H, "".join(b), f"{total} contributions in the last 12 months; current streak {cur} days, longest {longest} days"))

    # ---------------- langs.svg
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            nm = e["node"]["name"]
            if nm not in IGNORE_LANGS:
                langs[nm] = langs.get(nm, 0) + e["size"]
    ranked = sorted(langs.items(), key=lambda x: -x[1])
    top5, rest = ranked[:5], sum(v for _, v in ranked[5:])
    pool = [s for s in STYLES if s not in {FIXED.get(n) for n, _ in top5}]
    parts = []
    for n, v in top5:
        st = FIXED.get(n) or pool.pop(0)
        parts.append(("Jupyter (Python)" if n == "Jupyter Notebook" else n, v, st))
    if rest:
        parts.append(("Other", rest, "s6"))
    W2, H2 = 590, 360
    b = [f'<text class="m" x="32" y="44" font-size="11">LANGUAGES · SHARE OF CODE</text>',
         f'<text class="m" x="{W2-32}" y="44" font-size="10" text-anchor="end">PUBLIC REPOS</text>',
         donut(150, 200, 108, 66, parts),
         f'<text class="h" x="150" y="196" font-size="26" text-anchor="middle">{len(langs)}</text><text class="m" x="150" y="216" font-size="9" text-anchor="middle">LANGUAGES</text>',
         legend(300, 112, parts, lambda v, t: f"{v/t*100:.0f}%")]
    write("langs.svg", svg(W2, H2, "".join(b), "Languages by share of code: " + ", ".join(f"{p[0]} {p[1]/max(sum(q[1] for q in parts),1)*100:.0f}%" for p in parts)))

    # ---------------- weekday.svg
    names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    wk = [0] * 7
    for d in days:
        wk[d["weekday"]] += d["contributionCount"]
    order = [1, 2, 3, 4, 5, 6, 0]
    vals = [wk[i] for i in order]
    mxv = max(max(vals), 1)
    b = [f'<text class="m" x="32" y="44" font-size="11">WHEN I BUILD · BY WEEKDAY</text>',
         f'<text class="m" x="{W2-32}" y="44" font-size="10" text-anchor="end">LAST 12 MONTHS</text>']
    bx, by, bh, bw = 60, 300, 210, 46
    b.append(f'<path stroke="{DIM}" d="M{bx-10} {by}H{W2-40}"/>')
    best = vals.index(max(vals))
    for i, v in enumerate(vals):
        x = bx + i * 70
        h = bh * v / mxv
        if v:
            b.append(f'<path class="grow" style="animation-delay:{.1+i*.07:.2f}s" fill="{INK if i == best else "#5a5a60"}" '
                     f'd="M{x} {by}V{by-h+4:.1f}Q{x} {by-h:.1f} {x+4} {by-h:.1f}H{x+bw-4}Q{x+bw} {by-h:.1f} {x+bw} {by-h+4:.1f}V{by}Z"><title>{names[order[i]]}: {v}</title></path>')
        b.append(f'<text class="m" x="{x+bw/2}" y="{by+22}" font-size="10" text-anchor="middle">{names[order[i]]}</text>')
    if max(vals):
        x = bx + best * 70
        b.append(f'<text class="mi fade" style="animation-delay:.9s" x="{x+bw/2}" y="{by-bh*vals[best]/mxv-12:.1f}" font-size="12" text-anchor="middle">{vals[best]}</text>')
    write("weekday.svg", svg(W2, H2, "".join(b), "Contributions by weekday: " + ", ".join(f"{names[order[i]]} {v}" for i, v in enumerate(vals))))
    print("charts written", total, cur, longest)


if __name__ == "__main__":
    main()
