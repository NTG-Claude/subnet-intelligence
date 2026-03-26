# Contributing — How to Add a New Signal

## Steps

### 1. Add the signal function to `scorer/signals.py`

Each signal is a **pure function** that returns a `float` in `[0.0, 1.0]`.

```python
def my_new_score(
    raw_value: Optional[float],
    all_values: list[Optional[float]],
) -> float:
    return percentile_rank(raw_value, all_values)
```

Rules:
- `None` input → return `0.0` (pessimistic)
- Always percentile-rank against the full cross-subnet universe
- No side effects, no network calls

---

### 2. Register the signal in `scorer/composite.py`

**a)** Add the new cross-subnet list to `_CrossSubnetContext.__init__`:
```python
self.my_values: list[Optional[float]] = [
    raw.my_field for raw in all_raw
]
```

**b)** Call the signal inside `_score_one`:
```python
my = my_new_score(raw.my_field, ctx.my_values)
```

**c)** Update `_WEIGHTS` (must sum to 100):
```python
_WEIGHTS = {
    "capital": 20,   # reduced from 25
    ...
    "my_signal": 5,
}
```

**d)** Include the new score in `composite`:
```python
composite = (
    cap * _WEIGHTS["capital"]
    + ...
    + my * _WEIGHTS["my_signal"]
)
```

---

### 3. Extend `ScoreBreakdown` in `scorer/composite.py` and `api/models.py`

```python
# scorer/composite.py
class ScoreBreakdown(BaseModel):
    ...
    my_score: float

# api/models.py
class ScoreBreakdownResponse(BaseModel):
    ...
    my_score: float
```

---

### 4. Add a DB column in `scorer/database.py`

```python
class SubnetScoreRow(Base):
    ...
    my_score = Column(Float, nullable=False, default=0.0)
```

Then generate and apply a migration:
```bash
make migrate-new MSG="add my_score column"
make migrate
```

---

### 5. Add the signal to the frontend in `components/SignalBreakdown.tsx`

```typescript
const SIGNALS: Signal[] = [
  ...
  {
    key: 'my_score',
    label: 'My Signal',
    maxWeight: 5,
    description: 'What this signal measures and why it matters.',
  },
]
```

---

### 6. Write tests in `tests/test_signals.py`

```python
def test_my_new_score_output_in_range(subnets):
    all_vals = [s["my_field"] for s in subnets]
    for s in subnets:
        score = my_new_score(s["my_field"], all_vals)
        assert 0.0 <= score <= 1.0

def test_my_new_score_none_returns_zero():
    assert my_new_score(None, [1.0, 2.0]) == 0.0
```

---

### 7. Update `CHANGELOG.md`

Bump to the next minor version (e.g. `v1.1.0`) and describe the new signal.

---

## Code Style
- Python: standard library + project dependencies only
- No new dependencies without discussion
- All functions typed, no `Any` in signal code
- `pytest tests/ -v` must pass at ≥80% coverage before merging
