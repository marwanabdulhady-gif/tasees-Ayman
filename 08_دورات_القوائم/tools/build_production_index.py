#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد فهرس إنتاج المهندس أيمن عبد الرحيم (دورات وسلاسل القوائم).

يقرأ `transcripts/production_catalogue.json` — وهو **بيانات مكتوبة بيدٍ من مصادر
الشبكة** (كل مدخل يحمل مصدره وتاريخ التحقق، والقوائم غير الرسمية معلَّمة) — وينتج:

  08_دورات_القوائم/03_فهرس_الإنتاج/فهرس_الإنتاج.md
  08_دورات_القوائم/03_فهرس_الإنتاج/production.json

قاعدة ثابتة: الفهرس **لا يخترع** قائمة ولا رقمًا. أي قائمة غير متحقَّقة تُكتب في
`to_verify` ولا تدخل جدول الإنتاج.

الاستعمال:
  python3 08_دورات_القوائم/tools/build_production_index.py
  python3 08_دورات_القوائم/tools/build_production_index.py --check   # exit 1 = المخرج قديم
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "transcripts" / "production_catalogue.json"
OUT_DIR = ROOT / "08_دورات_القوائم" / "03_فهرس_الإنتاج"
OUT_MD = OUT_DIR / "فهرس_الإنتاج.md"
OUT_JSON = OUT_DIR / "production.json"
TRANSCRIPTS = ROOT / "transcripts"

AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def ar(n) -> str:
    return str(n).translate(AR)


def folder_files(folder: str | None) -> int:
    if not folder:
        return 0
    p = TRANSCRIPTS / folder
    if not p.is_dir():
        return 0
    return len([f for f in p.glob("*.md") if f.name.lower() != "readme.md"])


def lessons_written() -> int:
    """عدد الدروس المكتوبة فعلًا = مجموع دروس كل ملفات course.json."""
    total = 0
    for cj in sorted((ROOT / "08_دورات_القوائم").glob("*/course.json")):
        try:
            total += len(json.loads(cj.read_text(encoding="utf-8")).get("lessons", []))
        except Exception:
            pass
    return total


def tx_count(p: dict) -> int:
    """عدد الحلقات المفرَّغة: حقل صريح إن وُجد، وإلا عدد ملفات المجلد."""
    if p.get("transcript_episodes") is not None:
        return int(p["transcript_episodes"])
    return folder_files(p.get("transcripts_folder"))


def build() -> tuple[str, dict]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    prods = data["productions"]
    fams = {f["key"]: f for f in data["families"]}

    official = [p for p in prods if p["official"]]
    unofficial = [p for p in prods if not p["official"]]
    with_tx = [p for p in prods if tx_count(p) and p.get("transcripts_folder")]

    L: list[str] = []
    L.append("# فهرس إنتاج م. أيمن عبد الرحيم — الدورات والسلاسل على الشبكة")
    L.append("")
    L.append(f"> مولَّد بـ`tools/build_production_index.py` من `transcripts/production_catalogue.json` — **لا يُحرَّر بيد**.")
    L.append(f"> القناة: [{data['channel_title']}]({data['channel']}) · تاريخ التحقق: **{data['verified_on']}**.")
    L.append("")
    L.append("| البند | العدد |")
    L.append("|---|---|")
    L.append(f"| قوائم رسمية على قناة المهندس (معرّفات مميَّزة) | {ar(len({p['playlist_id'] for p in official}))} |")
    L.append(f"| صفوف الفهرس الرسمية (المستويات مفصولة) | {ar(len(official))} |")
    L.append(f"| فيديوهات في القوائم الرسمية | {ar(sum(p['videos'] for p in official))} |")
    L.append(f"| قوائم/تجميعات غير رسمية (قنوات أخرى) | {ar(len(unofficial))} |")
    L.append(f"| مصادر خارجية موجودة في المشروع (ليست للمهندس) | {ar(len(data.get('external_corpora', [])))} |")
    L.append(f"| **قوائم عندنا تفريغها** | **{ar(len(with_tx))}** |")
    L.append(f"| **دروس مكتوبة** | **{ar(lessons_written())}** (دورة علم النفس وحدها) |")
    L.append("")
    folders = [f for f in sorted(TRANSCRIPTS.iterdir()) if f.is_dir() and folder_files(f.name)]
    eps = sum(folder_files(f.name) for f in folders)
    L.append(f"> **الفرق بين الملفين:** `01_سجل_الحلقات/` يسجّل **ما عندنا تفريغه** ({ar(len(folders))} قوائم · {ar(eps)} حلقة)، وهذا الفهرس يسجّل **كل إنتاج المهندس على الشبكة**؛ فمنه يُعرف ما ينقص التفريغ قبل الكتابة.")
    L.append("")
    L.append("## العائلات")
    L.append("")
    L.append("| العائلة | قوائم | فيديوهات (رسمية) | تفريغ عندنا |")
    L.append("|---|---|---|---|")
    for key, fam in fams.items():
        rows = [p for p in prods if p["family"] == key]
        if not rows:
            continue
        L.append(
            f"| {fam['title']} | {ar(len(rows))} | "
            f"{ar(sum(p['videos'] for p in rows if p['official']))} | "
            f"{ar(len([p for p in rows if folder_files(p['transcripts_folder'])]))} |"
        )
    L.append("")

    for key, fam in fams.items():
        rows = [p for p in prods if p["family"] == key]
        if not rows:
            continue
        L.append(f"## {fam['title']}")
        L.append("")
        if fam.get("note"):
            L.append(fam["note"])
            L.append("")
        L.append("| القائمة | النوع | فيديوهات | القناة | التفريغ | الحالة |")
        L.append("|---|---|---|---|---|---|")
        for p in rows:
            files = tx_count(p)
            if files:
                tx = f"`{p['transcripts_folder']}` ({ar(files)})"
                status = "✅ عندنا تفريغ"
            else:
                tx = "—"
                status = "⬜ يحتاج تفريغًا"
            chan = ("رسمية · " if p["official"] else "غير رسمية · ") + p["channel"]
            L.append(
                f"| {p['title']} | {p['kind']} | {ar(p['videos'])} | {chan} | {tx} | {status} |"
            )
        L.append("")

    L.append("## ما يمكن كتابته الآن (تفريغ موجود)")
    L.append("")
    for p in with_tx:
        L.append(f"- **{p['title']}** — {ar(tx_count(p))} حلقة في `transcripts/{p['transcripts_folder']}/`. {p['notes']}")
    L.append("")

    L.append("## ما يحتاج تفريغًا قبل أي درس")
    L.append("")
    for p in prods:
        if not tx_count(p):
            kind = "رسمية" if p["official"] else "غير رسمية"
            L.append(f"- **{p['title']}** — {ar(p['videos'])} فيديو · قائمة {kind} · `{p['playlist_id']}`")
    L.append("")

    ext = data.get("external_corpora", [])
    if ext:
        L.append("## مصادر خارجية موجودة عندنا — ليست للمهندس")
        L.append("")
        L.append("تفريغها موجود في المشروع كمصدر خام (ومُدمج في مخطط v0.3)، لكنها **ليست من إنتاج المهندس** ولا تدخل «دورات القوائم».")
        L.append("")
        L.append("| العمل | صاحبه | حلقات | الصيغة | المسار |")
        L.append("|---|---|---|---|---|")
        for e in ext:
            L.append(f"| {e['title']} | {e['owner']} | {ar(e['episodes'])} | {e['format']} | `{e['local_path']}` |")
        L.append("")

    L.append("## ليست من إنتاج المهندس — ولا تدخل هذا المشروع")
    L.append("")
    L.append("| العمل | صاحبه | القائمة | لماذا هي هنا |")
    L.append("|---|---|---|---|")
    for n in data["not_his"]:
        pl = f"`{n['playlist_id']}`" if n["playlist_id"] else "—"
        L.append(f"| {n['title']} | {n['owner']} | {pl} | {n['reason']} |")
    L.append("")

    L.append("## قيد التحقق (لا يُبنى عليها شيء)")
    L.append("")
    for t in data["to_verify"]:
        L.append(f"- {t}")
    L.append("")

    L.append("## المصادر")
    L.append("")
    for s in data["sources"]:
        L.append(f"- {s}")
    L.append("")

    produced = {
        "channel": data["channel"],
        "verified_on": data["verified_on"],
        "totals": {
            "official_playlists": len({p["playlist_id"] for p in official}),
            "official_rows": len(official),
            "official_videos": sum(p["videos"] for p in official),
            "unofficial": len(unofficial),
            "with_transcripts": len(with_tx),
            "external_corpora": len(data.get("external_corpora", [])),
            "lessons_written": lessons_written(),
        },
        "productions": [
            {
                "id": p["id"],
                "title": p["title"],
                "family": p["family"],
                "kind": p["kind"],
                "playlist_id": p["playlist_id"],
                "videos": p["videos"],
                "official": p["official"],
                "channel": p["channel"],
                "transcripts_folder": p["transcripts_folder"],
                "transcript_episodes": tx_count(p),
            }
            for p in prods
        ],
        "external_corpora": data.get("external_corpora", []),
        "not_his": data["not_his"],
        "to_verify": data["to_verify"],
    }
    return "\n".join(L), produced


def main(argv: list[str]) -> int:
    md, produced = build()
    js = json.dumps(produced, ensure_ascii=False, indent=1) + "\n"
    if "--check" in argv:
        old_md = OUT_MD.read_text(encoding="utf-8") if OUT_MD.exists() else ""
        old_js = OUT_JSON.read_text(encoding="utf-8") if OUT_JSON.exists() else ""
        if old_md != md or old_js != js:
            print("✗ الفهرس قديم — أعد توليده: python3 08_دورات_القوائم/tools/build_production_index.py")
            return 1
        print("ok: فهرس الإنتاج مطابق للبيانات")
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(js, encoding="utf-8")
    t = produced["totals"]
    print(
        f"ok: {ar(t['official_playlists'])} قائمة رسمية · {ar(t['official_videos'])} فيديو · "
        f"{ar(t['unofficial'])} قائمة غير رسمية · تفريغ عندنا: {ar(t['with_transcripts'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
