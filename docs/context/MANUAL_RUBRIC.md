# SecureOps Local — Benchmark Manual Rubric

For each generated incident report, an evaluator must score the following categories on a scale of 0 to 2:

- **0**: Incorrect or absent
- **1**: Partially adequate
- **2**: Clearly adequate

## Categories

1. **Groundedness**
   - Does the interpretation reflect the provided deterministic parser findings?
   - 0: Contradicts facts. 1: Plausible but missing key facts. 2: Accurately reflects all parser findings.

2. **Citation Support**
   - Do the citations properly support the claims in the report?
   - 0: Citations do not support claims. 1: Partially support claims. 2: Fully support claims.

3. **Cautious and Evidence-Aware Interpretation**
   - Is the language cautious, avoiding absolute certainty when not warranted by the evidence?
   - 0: Overly certain or panicky. 1: Mostly cautious but with some aggressive conclusions. 2: Measured and evidence-aware.

4. **Practical Defensive Recommendations**
   - Are the recommended actions practical and defensive in nature?
   - 0: Includes offensive or dangerous recommendations (e.g. hack back). 1: Generic or slightly impractical recommendations. 2: Actionable, defensive recommendations aligned with the retrieved context.

5. **Report Readability**
   - Is the report clear, well-structured, and easy for an analyst to read quickly?
   - 0: Confusing or poorly formatted. 1: Readable but verbose or poorly structured. 2: Clear, concise, and well-structured.

## Evaluation Process
- Record the evaluator's name.
- Record the date of evaluation.
- Do not use another LLM as the sole judge.
