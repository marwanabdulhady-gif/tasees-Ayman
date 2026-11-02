# تدقيق استرجاع القوائم العشر — فحص بنيوي

> **PASS هنا فحص بنيوي فقط.** يثبت مطابقة البايتات المحلية، وعدد المصادر، وعزل `--playlist`، وعشرة مواضع معروفة مختارة. لا يثبت دلالة، ولا صحة إجابة، ولا التسجيل، ولا المتحدث، ولا المراجع، ولا موافقة المالك.

- المصادر: **383**، منها **225** للقوائم العشر و**158** ملف Drive غير منسوب.
- بصمة الكتالوج: `86f97dfa45ce83ce0639656ab15eba15de0f2f1c5faa6d6b3147fd9d4e1afabc`
- المواضع المعروفة: **10/10** ضمن أول 5 نتائج.

## الفحوص

| الفحص | النتيجة | التفصيل |
|---|---|---|
| `catalog_bytes_and_counts` | pass | 383 checksum-verified sources; 225 playlist sources; 158 unassigned Drive sources. |
| `filter_isolation` | pass | Each of the ten probes returns only its requested playlist and its target source. |
| `cross_playlist_leakage` | pass | No target source appears when its query is filtered to a different playlist. |
| `unknown_playlist_slug` | pass | An unknown exact slug returns zero results. |
| `negative_control` | pass | A nonsense lexical query returns zero results. |
| `known_location_hits` | pass | 10/10 selected locations in the top 5. |

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
| `cognitive-foundation-2` | 1 | 5 | `ayman-umayyad-abbasid` | لا |

## حدود صارمة

- FTS5/BM25 retrieval is lexical, not semantic; the ten probes echo their source wording.
- Other retrieved passages are unjudged; a hit does not prove the passage answers a question.
- Exact --playlist isolation is a metadata/plumbing check, not proof of attribution or content truth.
- No audio, speaker, edition, transcription, independent reference, safety or owner approval is established.
- The default Drive index and the psychology-only index are unchanged; this report concerns the optional unified index.

الأوامر والتفاصيل في [`README.md`](README.md). البيانات الكاملة في [`playlist_retrieval_audit.json`](playlist_retrieval_audit.json).
