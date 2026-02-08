# DeduplicationEngine.check_batch

- Source Note: Representative implementation block for candidate evaluation and thresholding
- Why Relevant: Captures the core per-item scoring and accept/reject flow

```python
for text, emb, item_id in zip(items, embeddings, ids):
    score_max = 0.0
    matched_text: str | None = None
    matched_id: str | None = None

    # Check against stored history
    for record in stored:
        sim = _cosine_similarity(emb, record.embedding)
        if sim > score_max:
            score_max = sim
            matched_text = record.text
            matched_id = record.record_id

    # Check against within-batch items that already passed
    for bp_text, bp_emb, bp_id in batch_passed:
        sim = _cosine_similarity(emb, bp_emb)
        if sim > score_max:
            score_max = sim
            matched_text = bp_text
            matched_id = bp_id

    similarity_scores.append(score_max)

    if score_max >= threshold:
        match = SimilarityMatch(
            score=score_max,
            matched_text=matched_text,
            matched_id=matched_id,
        )
        verdict = UniquenessVerdict(
            text=text,
            is_unique=False,
            embedding=emb,
            similarity_max=score_max,
            match=match,
            item_id=item_id,
        )
        failed.append(verdict)
    else:
        verdict = UniquenessVerdict(
            text=text,
            is_unique=True,
            embedding=emb,
            similarity_max=score_max,
            item_id=item_id,
        )
        passed.append(verdict)
        batch_passed.append((text, emb, item_id))
```
