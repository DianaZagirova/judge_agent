PROMPT = """Identify if given text of paper is aging-theory-related: 

# Theory of Aging:
- includes proposal, review, idea, mechanisms, or models that aim to explain why or how aging (biological or psychosocial) occurs.
- general, explanatory proposal, review, or synthesis of an aging mechanism, framework, idea, model, or hypothesis could be counted as 'theory-related', even if not called a theory. 
“General” means it is not confined to a single disease, pathway, organ, tissue, or clinical/cosmetic context and it makes claims about the causes, organizing principles, or evolutionary logic of senescence/lifespan broadly.

# Distinction from related concepts
- Model of the specific case: a formal representation (mathematical/computational/etc) of specific processes or consequences under a theory’s assumptions. But general models counted as valid.
- Narrow frameworks: present organizing principles or research directions. It qualifies as a theory only if it specifies general causal mechanisms of senescence as above.  

## Some examples of valid articles: 
- Introduce, synthesize, formalize, or evaluate general explanatory models or frameworks of aging (biological or psychosocial), including but not limited to those called 'theory', 'model', or 'framework', are generally valid. Reviews or conceptual syntheses that clarify, extend, or critique such frameworks also qualify.
- For research articles: - Tests explicit predictions of an aging theory or compares theories using data, models, or simulations (e.g., cross-species lifespan patterns).
- Provides a formalization of aging (mathematical/computational/evolutionary models) with general (not specific case) implications for aging.
- "Redox theory of aging" or reviews of redox mechanisms as overall explanations for aging, "Epigenetic clock theory" or broad reviews of epigenetic clocks as causes/markers of aging, Reviews, critiques, or discussions of established psychosocial theories (disengagement, continuity, etc.), General systems/mechanistic frameworks (entropy, protein turnover, "metabolaging," etc.)

# Exclusions:
- Disease-centric or organ/tissue/cell-type-specific pathogenesis or therapeutics (e.g., cancer, AD, CVD), unless the paper explicitly generalizes the mechanism as a broad causal driver of aging across contexts or tests predictions of general aging theories.
- Narrow focus: 1 gene, pathway, ion, with no connection to general aging mechanisms.
- Clinical geriatrics, nursing, care delivery, or health services.
- Demography/economics/sociology of population aging, workforce, policy.
- Aging of materials, substrates, and other topics related to material sciences.
- Cosmetic or skin, facial aging, aesthetics.
- Biomarkers/clocks as predictors/outcomes only (no causal/theoretical framing).
- Single-pathway/tissue/organ/system studies with no generalizable aging claims.
- Ecology or life-history work on lifespan that lacks a connection to aging mechanisms.
- Public health, healthy aging, resilience, wellbeing, care delivery, or policy.
- Phenomenological mortality models unless they explicitly develop or test general biological/evolutionary mechanisms of aging.
- Facial/skin aesthetics topics are not valid even if they use “theory” language.
- Editorials, commentaries, special-issue overviews, or perspectives that only call for theory or present an integrative “approach” without proposing/reviewing a specific, general causal mechanism of aging.

## Assessment
Step 1: Check Scope and Exclusions. Is the general subject broad (organism/species-level): inclusion; or narrowly focused on a single disease/organ (for example, skin)? Does it fall into other exclusion categories like public health, 'healthy aging', or cosmetic applications? Term "aging" should be considered as wide term. If paper fall into exlusino criteria here, consider not valid.
Step 2: Assess Core Contribution. Is the paper's main goal to propose, review, critique, or synthesize a general (not organ/disease-specific) understanding of why/how aging occurs? If yes, it is valid, regardless of the precise label (theory, model, framework, or mechanism).
Step 3: Evaluate Theoretical Subject. If the paper introduces, develops, tests, or discusses a broadly applicable explanation or organizing mechanism for aging, it should be counted as aging-theory-related.
Step 4: Word choice. If the title, abstract, or topic discusses a considerably broad explanation of aging (redox, entropy, disengagement, epigenetic clock, system collapse, etc.), count as valid.
Step 5: Other notes: review other given detailes/exlusion criteria previously, consider their info for final verdict. You may be a bit flexible as there are no direclt rules on what are aging papers.
Step 6: Final Verdict. Based on your step-by-step analysis, provide a final classification. 


#Output Format
Return a strict JSON object:

{
  "result": "valid" or "not_valid",
  "aging_theory": "name of theory, if applicable, or null. Example - redox theory",
  "type": "research", "review", "discussion", or "other",
  "reasoning": "<stepwise reasoning on each criteria, what reasoning behind each step>",
  "confidence_score": <integer 0-10 where 10 - means 100% sure in the 'result' status selected, 0 - not sure at all>
}


"""
