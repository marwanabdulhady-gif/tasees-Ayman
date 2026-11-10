# تدقيق استرجاع القوائم الإحدى عشرة — فحص بنيوي

> **PASS هنا فحص بنيوي فقط.** يثبت مطابقة البايتات المحلية، وعدد المصادر، وعزل `--playlist`، وأحد عشر موضعًا معروفًا مختارًا. لا يثبت دلالة، ولا صحة إجابة، ولا التسجيل، ولا المتحدث، ولا المراجع، ولا المراجعات المتخصصة. قرار المالك بالاعتماد موثق في `00_قرارات_المالك.json`، لكن هذا التدقيق لا يثبته آليًا.

- المصادر: **398**، منها **240** للقوائم الإحدى عشرة و**158** ملف Drive غير منسوب.
- بصمة الكتالوج: `31d43c7c982857dc4554155d96d99861325db7061b462b8854cc936097cd4a74`
- المواضع المعروفة: **11/11** ضمن أول 5 نتائج.

## الفحوص

| الفحص | النتيجة | التفصيل |
|---|---|---|
| `catalog_bytes_and_counts` | pass | 398 checksum-verified sources; 240 playlist sources; 158 unassigned Drive sources. |
| `filter_isolation` | pass | Each of the eleven probes returns only its requested playlist and its target source. |
| `cross_playlist_leakage` | pass | No target source appears when its query is filtered to a different playlist. |
| `unknown_playlist_slug` | pass | An unknown exact slug returns zero results. |
| `negative_control` | pass | A nonsense lexical query returns zero results. |
| `known_location_hits` | pass | 11/11 selected locations in the top 5. |

## عزل كل قائمة

| القائمة | رتبة الهدف تحت الفلتر | نتائج الفلتر | قائمة أخرى فُحصت | تسريب الهدف |
|---|---:|---:|---|---|
| `ayman-umayyad-abbasid` | 1 | 5 | `ayman-linguistic-awareness` | لا |
| `ayman-linguistic-awareness` | 1 | 5 | `ayman-psychology` | لا |
| `ayman-psychology` | 1 | 5 | `ayman-seerah-makkah` | لا |
| `ayman-seerah-makkah` | 1 | 5 | `ayman-reestablishing-awareness` | لا |
| `ayman-reestablishing-awareness` | 1 | 5 | `ayman-tasees` | لا |
| `ayman-tasees` | 1 | 5 | `q100-history` | لا |
| `q100-history` | 1 | 5 | `rihlat-alyaqeen` | لا |
| `rihlat-alyaqeen` | 4 | 5 | `cognitive-foundation-1` | لا |
| `cognitive-foundation-1` | 1 | 5 | `cognitive-foundation-2` | لا |
| `cognitive-foundation-2` | 1 | 5 | `ayn-al-tariq` | لا |
| `ayn-al-tariq` | 1 | 5 | `ayman-umayyad-abbasid` | لا |

## حدود صارمة

- FTS5/BM25 retrieval is lexical, not semantic; the eleven probes echo their source wording.
- Other retrieved passages are unjudged; a hit does not prove the passage answers a question.
- Exact --playlist isolation is a metadata/plumbing check, not proof of attribution or content truth.
- The owner approval is administrative; audio, speaker, edition, transcription, independent references, clinical/scientific/historical review and external publication are not automatically established.
- The default Drive index and the psychology-only index are unchanged; this report concerns the optional unified index.

الأوامر والتفاصيل في [`README.md`](README.md). البيانات الكاملة في [`playlist_retrieval_audit.json`](playlist_retrieval_audit.json).
