#!/usr/bin/env python3
"""Generate lexical comparison of the two potentially overlapping Drive files."""
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ayman_rag.compare import compare_sources  # noqa: E402

OUT = ROOT / '08_دورات_القوائم/التأسيس_المعرفي/01_مقارنة_ملفي_المستوى_الثاني.md'
A = 'drive-57f2ce520d28eddf9f87'
B = 'drive-8d691d57543232ceb069'


def build():
    r = compare_sources(A, B, max_runs=10)
    def source(label):
        doc = r[label]
        rel = '../../' + doc['path']
        return f"[{doc['id']}]({quote(rel, safe='/')}) · SHA-256 `{doc['sha256']}`"
    def at(label, start, end):
        rel = '../../' + r[label]['path']
        return f"[السطر {start}–{end}]({quote(rel, safe='/')}#L{start})"
    lines = ['# مقارنة ملفي المستوى الثاني 006 و007', '',
             '> **ملف مولَّد** من `tools/build_foundation_overlap_report.py`. أعد توليده ولا تعدله يدويًا.', '',
             '**الغرض:** مساعدة المراجع على تحديد مواضع متشابهة في النصين كاملين. المقارنة آلية لفظية بعد تطبيع الحروف، لا تثبت أن التسجيل واحد، أو أن أي تفريغ أصح أو أكمل. احتفظ بالملفين ولا تدمجهما أو تستبعد أحدهما قبل مراجعة المصدر والتسجيل إن أمكن.', '',
             f'- ملف 006: {source("a")}', f'- ملف 007: {source("b")}',
             f'- الكلمات المفهرسة بعد التطبيع وإزالة روابط التوقيت: {r["a_tokens"]:,} و{r["b_tokens"]:,}.',
             f'- خماسيات الكلمات الفريدة: {r["a_unique_shingles"]:,} و{r["b_unique_shingles"]:,}؛ المشترك {r["shared_unique_shingles"]:,}.',
             f'- Jaccard للمجموعتين: {r["unique_jaccard"]:.1%}؛ المشترك ÷ المجموعة الأصغر: {r["shared_over_smaller"]:.1%}. هذان مقياسان للمجموعات، وليسا نسبة مطابقة التسجيل أو التغطية.', '',
             '## توزع الخماسيات المشتركة', '',
             'قُسم تسلسل كل ملف إلى عشرة أجزاء متساوية تقريبًا بعدد مواضع الخماسيات، لا بحسب الوقت أو السطور. كل خلية هي عدد الخماسيات التي ظهرت في أي مكان في الملف الآخر ÷ عدد الخماسيات في ذلك الجزء، ولا تعني محاذاة الموضعين أو تشابه المعنى.', '',
             '| الجزء | ملف 006 | ملف 007 |', '|---:|---:|---:|']
    for i, (a, b) in enumerate(zip(r['a_position_bins'], r['b_position_bins']), 1):
        lines.append(f"| {i} | {a['matched']}/{a['total']} | {b['matched']}/{b['total']} |")
    lines += ['', '## مواضع مقترحة للقراءة المتقابلة', '',
              f"وُجد {r['unique_anchor_run_count']} مقطعًا من 10 كلمات مطبّعة متتابعة أو أكثر، مبنية على خماسيات لا تتكرر داخل أي من الملفين؛ الجدول يعرض أطول عشرة فقط. قد تكون المقاطع مكسورة بسبب اختلاف التفريغ؛ غياب مقطع من الجدول لا يعني أنه مختلف أو مفقود. المعاينة مطبّعة وليست اقتباسًا حرفيًا؛ افتح المصدرين للتحقق.", '',
              '| كلمات متتابعة مطبّعة | ملف 006 | ملف 007 | بداية مطبّعة للمراجعة |', '|---:|---|---|---|']
    for run in r['unique_anchor_runs']:
        lines.append(f"| {run['words']} | {at('a',run['a_start_line'],run['a_end_line'])} | {at('b',run['b_start_line'],run['b_end_line'])} | {run['normalized_preview']} |")
    lines += ['', '## المطلوب قبل تقرير خريطة الدروس', '',
              '1. افحص المقاطع والسياق في الملفين، بما فيها المناطق غير المتطابقة، وقارن بالتسجيلات أو بيانات المصدر إن توفرت.',
              '2. تحقّق من المتحدث والطبعة وما إذا كانت الاختلافات محتوى إضافيًا أو أخطاء تفريغ أو تسجيلات مختلفة.',
              '3. بعد مراجعة صاحب المشروع، قرر تقسيم الدروس أو دمجها أو استبعاد جزء بسبب موثق. لا تنقل طوابع من مصدر آخر تلقائيًا.', '']
    return '\n'.join(lines)


def main():
    OUT.write_text(build(), encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
