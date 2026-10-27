# PRISM Ground-Truth Annotation Guide & Protocol

> **Specification Version**: 1.0.0  
> **Target Corpus**: Amazon Reviews'23 (Appliances Category, UCSD McAuley Lab)  
> **Task**: Human Forensic Ground-Truth Annotation for PRISM ML Evaluation  
> **Status**: Living Standard Protocol  

---

## 1. Principles & Ground-Truth Invariants

1. **Textual Primacy**: Ground truth must reflect what is explicitly written in the customer review text.
2. **Independence from Model Predictions**: Never copy, infer, or "correct" a ground-truth label to match PRISM's output, star ratings, or automated heuristics.
3. **Exact Evidence Spans**: Every specific attribution (hazard, sarcasm, feature mention) must be backed by an exact character-for-character substring existing verbatim in the review text.
4. **Decoupled Star Ratings**: Star ratings are user-supplied subjective signals; they are recorded separately as metadata and must **never** be used as the ground-truth label for sentiment or safety.
5. **No Speculation**: If the text is contradictory, vague, or provides insufficient evidence, label it `unclear` or `other/unknown`. Never force consensus or fabricate annotations.

---

## 2. Safety Hazard Annotation Standard

### 2.1 Primary Labels (Mutually Exclusive)
Assign exactly one primary label per review:
- `hazard`: The review describes an actual, occurring, or directly present physical danger, bodily injury, or severe hazardous event resulting from the appliance.
- `no_hazard`: The review does not describe such a physical risk (includes ordinary malfunctions, leaks, breakage, or performance issues).
- `unclear`: The review text is too ambiguous, contradictory, or lacks context to determine whether a physical hazard occurred.

### 2.2 Hazard Types (Required if `hazard`)
When `hazard` is assigned, record the specific hazard type:
- `fire`: Active flames, combustion, ignition, catching fire.
- `smoke`: Noxious smoke, billowing smoke from motor/electronics, smoldering.
- `burn`: Thermal burns to human skin, severe blistering, scalding.
- `electric_shock`: Electrical shocks to humans or pets, live current exposure, sparking from internal circuits.
- `injury`: Lacerations, cuts from shattered glass/metal, severe puncture wounds, broken bones.
- `dangerous_overheating`: Extreme thermal runaway melting the external housing, scorching adjacent walls or countertops.
- `chemical_hazard`: Battery acid leakage, corrosive chemical discharge, toxic gas emissions.
- `other`: A genuine physical safety hazard that does not fit the above categories.
- `unknown`: A hazard is described but the specific physical mechanism is unspecified.

### 2.3 Strict Safety Ground-Truth Rules
1. **Ordinary Defects are NOT Hazards**:
   - Water leaks, hose drips, ice melting quickly, food spoilage, compressor noise, bad odor, slow freezing, or cracked cosmetic plastic are **`no_hazard`**.
   - A defect is only a hazard if it presents a direct, credible risk of physical harm or property destruction (e.g., water leaking directly into an unshielded 240V power outlet creating a short circuit).
2. **Sparks and Flames Require Credible Real Events**:
   - A normal ignitor clicking spark on a gas stove burner is not a hazard.
   - An electrical arc throwing sparks across a kitchen counter is a `hazard` (`electric_shock` or `fire`).
   - A tiny, ambiguous spark with no stated danger or consequence should be labeled `unclear` if the risk cannot be verified.
3. **Negated Events are NOT Hazards**:
   - Statements explicitly confirming a hazard did *not* happen (e.g., *"Did not catch fire"*, *"No electric shock occurred"*, *"Didn't burn the counter"*) must be labeled **`no_hazard`**.
4. **Hypotheticals, Fears, and Warnings are NOT Events**:
   - Subjective fears, warnings, or hypotheticals (e.g., *"I was afraid it might catch fire"*, *"Could easily shock an unsuspecting child"*, *"Warning: keep away from water"*) did not actually happen. Label as **`no_hazard`** with a note explaining the hypothetical nature.
5. **Reported or Quoted Incidents**:
   - If the reviewer reports a real incident experienced by a household member, technician, or quoted from an official notice (e.g., *"My husband received a severe shock when touching the casing"*), label as **`hazard`** and mark `is_reported_or_quoted: true`.
6. **Slang and Figurative Expressions**:
   - Hyperbolic or slang expressions (e.g., *"This air fryer is straight fire 🔥"*, *"smoking hot deal"*, *"had a blast with this blender"*) are **`no_hazard`**.
7. **Hazard vs. Harmless Contradiction**:
   - If the reviewer states an event occurred but clarifies it was harmless (e.g., *"It caught fire but it was just a tiny crumb burning off"*), label as `hazard` only if an actual appliance hazard occurred; otherwise label `unclear`.

---

## 3. Sarcasm Annotation Standard

### 3.1 Primary Labels (Mutually Exclusive)
Assign exactly one label per review:
- `sarcasm`: Clear textual evidence that the reviewer intends the opposite of the literal words, conveyed through irony, sneer, or unmistakable sarcastic juxtaposition.
- `not_sarcasm`: Sincere praise, sincere criticism, literal statements, jokes without meaning reversal, or mixed reviews.
- `unclear`: Insufficient textual evidence to reliably distinguish sarcasm from sincere confusion or poor phrasing.

### 3.2 Rating/Text Disagreement (Annotated Separately)
Rating/text disagreement is an independent variable and **must never** be used as the sole basis for the sarcasm label:
- `present`: The star rating contradicts the text (e.g., 5.0★ rating with a scathing defect complaint, or 1.0★ rating with unqualified praise).
- `absent`: The star rating is directionally aligned with the text tone.
- `unclear`: Rating or text tone is ambiguous.
- *Requirement*: Always provide a short explanation for the rating/text relationship.

### 3.3 Strict Sarcasm Ground-Truth Rules
1. **Complaints and Anger are NOT Sarcasm**: Sincere venting, furious complaints, and negative reviews are sincere criticism (`not_sarcasm`).
2. **Litotes and Understatement**: Phrases like *"Not the best appliance I ever owned"* or *"Quality could be better"* are literal negative assessments, not sarcasm.
3. **Evidence Span Requirement**: For every review marked `sarcasm`, you must quote the exact substring displaying the ironic reversal (e.g., *"Brilliant engineering—broke after 12 minutes"* or *"Great job Whirlpool, love having water all over my floor"*). If no textual span supports ironic reversal, label as `not_sarcasm`.

---

## 4. Sentiment Annotation Standard

Annotated at two distinct structural tiers:

### 4.1 Overall Review Sentiment
Represents the reviewer's holistic evaluation of the product or ownership experience:
- `positive`: The reviewer is generally satisfied, pleased, or endorses the product.
- `negative`: The reviewer is dissatisfied, disappointed, or condemns the product.
- `mixed`: The reviewer explicitly expresses both positive and negative opinions about the same product overall (e.g., *"Love the look and feel, but the motor failed in 2 weeks"*).
- `neutral`: Purely factual, objective, or descriptive statements with no discernible emotional or evaluative stance (e.g., *"This is a 12-cup replacement carafe made of glass"*).
- `unclear`: The overall tone is impenetrable, contradictory without resolution, or gibberish.

### 4.2 Feature-Level Sentiment
Annotated for every distinct product attribute explicitly evaluated in the text:
- `positive`: Favorable assessment of that specific attribute.
- `negative`: Unfavorable assessment of that specific attribute.
- `mixed`: Both praise and criticism directed at the same attribute (e.g., *"The rack is sturdy but too narrow"*).
- `neutral`: Factual statement regarding the attribute without evaluative polarity.
- `unclear`: Attribute opinion cannot be reliably deciphered.

### 4.3 Negation & Linguistic Scope Rules
- **Context-Sensitive Negation**: Scope negation strictly to the semantic target.
  - *"Not bad"* $\rightarrow$ Mildly positive / acceptable.
  - *"Not great"* $\rightarrow$ Mildly negative.
  - *"Not disappointed"* $\rightarrow$ Positive.
  - *"Not working"* $\rightarrow$ Strongly negative.
- **Rating Decoupling**: If a customer leaves a 5-star rating but writes *"Worst product ever, arrived shattered"*, the overall text sentiment is **`negative`**, with `rating_text_disagreement: "present"`.

---

## 5. Feature & Aspect Extraction Standard

### 5.1 Category Taxonomy (Mutually Exclusive per Aspect Mention)
When a review discusses an aspect, assign the most specific category:
1. `product_performance`: Core operational capability (cooling speed, heating, ice making, wash cycles, power).
2. `build_material_quality`: Structural durability, materials (stainless steel, plastic, glass), hinges, knobs, door gaskets, sturdiness.
3. `reliability`: Longevity, failure rate over time, breakdown frequency, lifespan.
4. `usability`: Ease of use, controls, ergonomics, cleaning difficulty, noise level, display clarity.
5. `price_value`: Cost, affordability, bang for buck, overpriced, expensive replacement parts.
6. `packaging`: Retail box, interior foam, protective film, damage sustained inside packaging.
7. `delivery_shipping`: Courier speed, delivery delays, carrier mishandling, box transit damage.
8. `installation`: Ease of setup, mounting, plumbing hookup, instruction manual clarity, technician visit.
9. `customer_support`: Warranty service, manufacturer responsiveness, replacement parts availability, refund handling.
10. `safety`: Thermal runaway, sparks, shocks, smoke, cuts, hazardous structural failure.
11. `other`: A genuine, distinct product aspect not captured above (e.g., aesthetics/color, size/dimensions).
12. `unclear`: Aspect reference is ambiguous or unrecognizable.

### 5.2 Strict Aspect Boundary Rules
1. **Never conflate delivery or packaging with product build quality**: If a box arrives crushed but the refrigerator inside is intact, `packaging` is negative, not `build_material_quality`.
2. **Clause Splitting**: Opposing sentiments in a single sentence must be separated into distinct aspect mentions (e.g., *"Cooling is superb, but the compressor is terribly loud"* $\rightarrow$ Aspect 1: `cooling_performance` (positive); Aspect 2: `noise_level` (negative)).
3. **No Redundant Overlapping Mentions**: Do not create multiple records for the exact same phrase and aspect.
4. **Parts and Components**: Specific parts (knob, gasket, filter, rack, motor) must be mapped to their functional category (`build_material_quality` or `product_performance`) rather than generic tags.

---

## 6. Adjudication & Disagreement Resolution Workflow

1. **Independent Dual Annotation**: Annotator 1 and Annotator 2 independently annotate identical review records without viewing the other's outputs.
2. **Diff Identification**: An automated comparison script highlights discrepancies in:
   - Safety primary label and hazard type
   - Sarcasm primary label
   - Overall sentiment
   - Extracted feature spans and categories
3. **Adjudication Conference**: A lead annotator / adjudicator reviews all discrepancies alongside the written guidelines:
   - Check text verbatim against the negative/positive rules.
   - If ambiguity persists under the strict rules, finalize as `unclear`.
   - Record `annotator_1`, `annotator_2`, `final_adjudicated`, and `adjudication_reason`.
