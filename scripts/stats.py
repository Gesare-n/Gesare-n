#!/usr/bin/env python3
"""Builds assets/stats.svg (contributions panel) in the same blueprint style as the rest of the profile.
Runs daily from .github/workflows/profile-stats.yml. Standard library only.
"""
import base64, datetime as dt, json, os, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Gesare-n")
TOKEN = os.environ.get("STATS_TOKEN") or os.environ["GITHUB_TOKEN"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG, PANEL, INK, DIM, FAINT = "#0b0b0c", "#0f0f11", "#ECEAE4", "#8a8984", "#2b2b2e"

Q = """query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date } } }
    totalCommitContributions totalPullRequestContributions totalIssueContributions restrictedContributionsCount }
  repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC, first:100){ totalCount
    nodes{ languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } } } } }"""


def gql():
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": Q, "variables": {"login": USER}}).encode(),
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["data"]["user"]


def fonts():
    out = []
    for fam, fn, w in [("NGHead", "head.woff2", 600), ("NGBody", "body.woff2", 400), ("NGMono", "mono.woff2", 400)]:
        p = os.path.join(ROOT, "assets", "fonts", fn)
        if os.path.exists(p):
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url(data:font/woff2;base64,{base64.b64encode(open(p,'rb').read()).decode()}) format('woff2');}}")
    return "".join(out)


def main():
    u = gql()
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    total = cc["contributionCalendar"]["totalContributions"]
    # streaks
    longest = cur = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    for d in reversed(days):
        if d["contributionCount"] > 0:
            cur += 1
        elif d["date"] == dt.date.today().isoformat():
            continue
        else:
            break
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]]
    langs = {}
    for n in u["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    tot = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda x: -x[1])[:6]

    W, H = 1200, 400
    css = f"""{fonts()}
.h{{font-family:'NGHead','Barlow Condensed','Arial Narrow',sans-serif;font-weight:600;fill:{INK}}}
.b{{font-family:'NGBody','Barlow',Arial,sans-serif;fill:{INK}}}
.m{{font-family:'NGMono',Consolas,monospace;fill:{DIM};letter-spacing:.12em}}
.mi{{font-family:'NGMono',Consolas,monospace;fill:{INK};letter-spacing:.12em}}
.grow{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:g .8s cubic-bezier(.6,.1,.2,1) forwards}}
@keyframes g{{to{{transform:scaleY(1)}}}}
.wide{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:w 1s cubic-bezier(.6,.1,.2,1) forwards}}
@keyframes w{{to{{transform:scaleX(1)}}}}
@media (prefers-reduced-motion:reduce){{.grow,.wide{{animation:none!important;transform:none!important}}}}"""
    b = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    b.append(f'<text class="m" x="40" y="44" font-size="11">CONTRIBUTIONS · LAST 12 MONTHS</text>')
    b.append(f'<text class="m" x="{W-40}" y="44" font-size="10" text-anchor="end">UPDATED {dt.date.today().isoformat()}</text>')
    b.append(f'<text class="h" x="36" y="150" font-size="112">{total:,}</text>')
    stats = [("CURRENT STREAK", f"{cur} D"), ("LONGEST STREAK", f"{longest} D"), ("COMMITS", f'{cc["totalCommitContributions"]:,}'),
             ("PUBLIC REPOS", str(u["repositories"]["totalCount"]))]
    for i, (k, v) in enumerate(stats):
        x = 40 + i * 140
        b.append(f'<text class="m" x="{x}" y="196" font-size="9">{k}</text><text class="h" x="{x}" y="230" font-size="30">{escape(v)}</text>')
    # languages
    b.append(f'<text class="m" x="700" y="84" font-size="10">LANGUAGES · BY CODE SIZE</text><path stroke="{FAINT}" d="M700 96H1160"/>')
    for i, (name, size) in enumerate(top):
        y = 126 + i * 26
        pct = size / tot
        b.append(f'<text class="b" x="700" y="{y}" font-size="14">{escape(name)}</text>'
                 f'<rect x="860" y="{y-8}" width="240" height="2" fill="{FAINT}"/>'
                 f'<rect class="wide" style="animation-delay:{.2+i*.1:.1f}s" x="860" y="{y-9}" width="{240*pct:.1f}" height="4" fill="{INK}"/>'
                 f'<text class="mi" x="1160" y="{y}" font-size="11" text-anchor="end">{pct*100:.0f}%</text>')
    # weekly bars
    mx = max(weeks) or 1
    bw = 1120 / len(weeks)
    b.append(f'<path stroke="{FAINT}" d="M40 370H1160"/>')
    for i, wv in enumerate(weeks):
        h = 52 * wv / mx
        x = 40 + i * bw
        b.append(f'<rect class="grow" style="animation-delay:{i*.015:.2f}s" x="{x+bw/2-1.5:.1f}" y="{370-max(h,1):.1f}" width="3" height="{max(h,1):.1f}" fill="{INK if wv else FAINT}"/>')
    b.append(f'<text class="m" x="40" y="390" font-size="9">52 WEEKS AGO</text><text class="m" x="1160" y="390" font-size="9" text-anchor="end">THIS WEEK</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year">'
           f"<title>{total} contributions in the last year</title><style>{css}</style>{''.join(b)}</svg>")
    open(os.path.join(ROOT, "assets", "stats.svg"), "w").write(svg)
    print("stats.svg written", total, cur, longest)


if __name__ == "__main__":
    main()
