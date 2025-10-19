PROMPT = """Identify if a given paper is related to aging theory based on its abstract and title.

## Definition of "Theory of Aging"
A theory of aging proposes, reviews, tests, discuss, critiques, etc causal explanations for why or how biological or psychosocial aging occurs at a general level.  
"General" means: even if the theory is demonstrated through a specific disease, pathway, or organ, it attempts to generalize, seeking to make claims about fundamental causes, organizing principles, or evolutionary logic of senescence/lifespan, etc., to make a general statement applicable to the whole organism.

## Aging Theory-Related Articles
These are papers that **propose, formalize, compare, synthesize, critique, contextualize, empirically test, engage with, or discuss general explanations** for aging theory (see definition above).

## Valid Papers Include:
- Propose new general causal mechanisms (e.g., damage accumulation, entropy generation, epigenetic drift).
- Review, synthesize, or compare existing aging theories.
- Test specific predictions of aging theories with data or models.
- Formalize aging processes mathematically or computationally with general causal implications.
- Propose a new aging theory.
- Critique or refine theoretical frameworks.
- Test explicit predictions of aging theory or compare theories using data, models, or simulations (e.g., cross-species lifespan patterns, trade-offs, force-of-selection dynamics).
- Provide a formalization of aging (mathematical, computational, or evolutionary models) with general implications for biological aging.
- Use evolutionary reasoning about aging (ultimate causes, selection, life-history trade-offs) to explain aging from an evolutionary perspective.
- etc.

## Valid Paper Examples:
- Entropy/thermodynamic theories of aging.
- Damage accumulation theories (potentially including mathematical formalization).
- Epigenetic theories (if discussing causal programs, not just prediction).
- Evolutionary theories (antagonistic pleiotropy, disposable soma).
- Systems theories (hallmarks of aging, network collapse).
- Historical or meta-theoretical analyses of aging theories.
- Psychosocial theories (disengagement, continuity)—if explaining aging processes.
- Papers testing whether interventions validate theoretical predictions.
- Mathematical formalizations of general aging processes (entropy, damage dynamics).
- Papers on known theories of aging (redox, etc).
- etc.

## Exclusions (and Similar Cases):
- Disease-specific pathogenesis (e.g., cancer, AD, CVD), unless the paper explicitly generalizes the mechanism as a broad causal driver of aging.
- Very narrow focus on one gene, pathway, or ion with no (even potential) connection to aging in general.
- Biomarker/clock development focused solely on prediction (not causal mechanisms).
- Clinical geriatrics, care delivery, or health services.
- Demography, policy, or workforce aging.
- Clearly unrelated topics: materials, cosmology, robotics aging, etc.
- Cosmetic or facial aging (aesthetic focus).
- “Healthy aging” programs that lack theoretical mechanisms.
- Phenomenological mortality models without discussed biological mechanisms.
- Intervention studies unless they explicitly test theoretical predictions.
- Ecology or life-history work on lifespan that lacks connection to aging mechanisms.
- Editorials, commentaries, special-issue overviews, or perspectives that only call for theory or present an integrative “approach” without proposing/reviewing a specific, general causal mechanism.
- Psychosocial theories only if they are recognized theories of aging (e.g., disengagement, continuity) and explain aging processes in psychosocial terms.
- General health theories.

## Edge Cases:
- “Hallmarks of aging” reviews: Valid aging-theory-related papers.
- Senolytics/senescence: Valid if the paper tests whether senescence is a causal driver of aging broadly.
- Epigenetic clocks: Valid if discussing whether clocks capture causal programs vs. damage, etc.; not valid if used solely for prediction.
- Psychosocial theories (e.g., disengagement, continuity): Valid if they fit the aging theory criteria above.
- If the paper discusses general aging and the title contains the word “theory” (or similar), or if authors claim to establish/review a biological theory, it is likely valid.
- Proposals for new frameworks intended to unify or explain aging (e.g., “metabolaging”) should be considered valid if positioned as organizing principles.
- Mathematical/computational models: Valid if they formalize general causal mechanisms (entropy, damage dynamics), NOT if just phenomenological descriptions.
- Papers about outdated or deprecated theories are valid.

## Think Step-by-Step:
Note: You are given the title and abstract; your task is to infer the intention of the whole article based on this information.

1. Main topic: Is the main focus biological or psychosocial aging?
2. Theory: Is the paper possibly about (in any sense) a relevant theory of aging, per the criteria above?
3. Scope: Is the focus only on a single gene/pathway/organ OR the concept it potentially generalizable/generilized by authors?
4. Exclusion check: Does it fall into any of the exclusion categories?
5. Not trivial cases: Analyze each case indivudually to assume other not stated criteria.
6. Based on your step-by-step analysis, provide a final classification. If uncertain, return "doubted."

## Output Format
Return a strict JSON object:
{    
  "type": "research"|"review"|"discussion"|"other",
  "reasoning": "<short reasoning>",
  "result": "valid"|"doubted"|"not_valid",
  "confidence_score": <0-10, where 10=completely certain in the decision>,
  "aging_theory": "<specific theory name or null>"
}
"""