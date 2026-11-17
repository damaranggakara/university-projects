# Symbolic AI

Classical, non-statistical artificial intelligence: logical inference, automated planning
and fuzzy reasoning, each implemented from first principles in plain Python and NumPy,
with no AI library doing the work. Coursework for Kecerdasan Buatan (Artificial
Intelligence), Semester 5.

A deliberate counterweight to the rest of this portfolio, which is almost entirely
statistical machine learning.

## 1. First-order logic: diabetes risk reasoning

`notebooks/first_order_logic_diabetes.ipynb`

A forward-chaining inference engine built from scratch: `add_fact`, `add_rule`, `unify`,
`substitute`, `forward_chain`. Facts about a patient are asserted as predicates, rules fire
by unification, and the engine derives a diagnosis plus the chain of indicators that
supported it.

Running it over the sample patients:

```
nama: alice          nama: bob
indicators met: 6/7  indicators met: 0/7
  low_income
  female
  stressed
  age_over_45
  hypertensive
  high_bmi
diagnosis: has diabetes
```

The value here is that the output is an *explanation*, not a score. Every conclusion names
the facts that produced it, the property that statistical classifiers in this portfolio
(projects 05, 10, 14) do not have, and the reason symbolic methods still matter in
regulated domains like clinical decision support.

## 2. Nonlinear planning: partial-order planner

`notebooks/nonlinear_planning.ipynb`

A partial-order planner over a small STRIPS-style domain (making coffee). Operators declare
preconditions and effects; the planner adds steps to satisfy open goals and inserts
ordering constraints, *promotions*, to resolve threats between them.

```
=== NONLINEAR PLAN: PEMBUATAN KOPI ===
1. Pickup(spoon)              5. Pickup(hot_water)
2. Add(coffee_powder, cup)    6. Pour(hot_water, cup)
3. Add(sugar, cup)            7. Putdown(hot_water)
4. Putdown(spoon)

=== PROMOTIONS (Ordering Constraints) ===
- Pickup(spoon) must precede Add(coffee_powder, cup)
...
```

"Nonlinear" means the plan is a partial order, not a fixed sequence: steps 2 and 3 are
genuinely unordered with respect to each other, and the planner commits to an ordering only
where a threat forces it. Least-commitment planning.

## 3. Fuzzy inference and relational reasoning

`notebooks/fuzzy_logic_inference.ipynb`

Two exercises:

**Relational reasoning**: a small predicate base over world regions (`northOf`, `southOf`,
`eastOf`, `westOf`) with queries over the relations.

**Fuzzy inference system**: a Mamdani-style controller assessing driving risk from vehicle
speed and road condition. Triangular and trapezoidal membership functions, a 9-rule base
over (speed x road), min-implication, aggregation, and centroid defuzzification, all
hand-written.

| Case | Speed (km/h) | Road quality (0-10) | Crisp risk |
|---|---|---|---|
| A | 20 | 9 | **22.5** (low) |
| B | 45 | 6 | **39.0** (moderate) |
| C | 180 | 1 | **67.5** (high) |

Risk rises monotonically as speed increases and road quality falls, which is the behaviour
the rule base should produce. Membership functions and per-case aggregation plots are in
`figures/`.

## Verification, and what it found

`test_reasoners.py` loads the functions these notebooks define and asserts properties that
must hold for *any* input, rather than trusting the single worked example each notebook
shows. All ten properties hold. Two of them pin design weaknesses rather than successes, and
those are worth reading.

```
OK  FOL: sound on no evidence     no indicators -> no diagnosis
OK  FOL: derives on evidence      indicators present -> diagnosis derived
OK  FOL: unification              binds variables, rejects constant and predicate clashes
OK  FOL: rule base shape          14/14 rules single-antecedent
OK  plan: validity and goal       10 steps found by search, preconditions hold, goal achieved
OK  plan: reports unreachable goal unreachable goal correctly reported as failure
OK  plan: causal links derived    16 links, each a verified producer/consumer pair
OK  fuzzy: membership bounds      all degrees within [0, 1]
OK  fuzzy: domain coverage        total degree ranges 0.00-1.00
OK  fuzzy: broad monotonicity     speed 20->180: 21.8->69.8; road 1->10: 67.0->0.0
```

### The planner did not plan - now fixed

The original version of this notebook printed a plan rather than finding one:

- `ordered_steps` was a **hardcoded list** of seven action names
- the ordering constraints were a **hardcoded list** of pairs
- the goal literal was inserted into the state by hand: `state.add("mixed(cup)")`
- the final check printed the goal it had been *given*, not the state reached, so it
  reported `GOAL STATE TERCAPAI` unconditionally

And the goal was genuinely unreachable: **no action produced `mixed(cup)`**. The domain had
`Pickup`, `Add`, `Putdown` and `Pour`, with no `Stir` operator. The hand-inserted literal
was concealing that.

Three changes:

1. **`search_plan` does breadth-first forward state-space search** and returns the shortest
   plan it finds, or `None` when the goal is unreachable.
2. **A `Stir(cup)` operator** was added, requiring a held spoon and all three ingredients,
   so `mixed(cup)` has a producer.
3. **Causal links and threats are derived from the plan** search returns, and
   `nonlinear_plan` returns `(plan, final_state, achieved)` instead of printing and
   returning `None`.

Search finds a 10-step plan and the goal is now actually achieved:

```
1. Pickup(spoon)        6. Pour(hot_water,cup)
2. Add(coffee_powder,cup)   7. Putdown(hot_water)
3. Add(sugar,cup)       8. Pickup(spoon)
4. Putdown(spoon)       9. Stir(cup)
5. Pickup(hot_water)   10. Putdown(spoon)

goal     : ['handempty', 'mixed(cup)']
achieved : ['handempty', 'mixed(cup)']
missing  : none
```

The spoon is put down and picked up again because only one object can be held at a time,
`Pour` needs the kettle, `Stir` needs the spoon, so the detour is forced by the
preconditions, not a search failure.

Sixteen causal links are derived, each a verified producer/consumer pair, and no threats
exist because the one condition that is deleted (`holding(spoon)` at step 4) is
re-established at step 8 before `Stir` needs it.

The last cell removes `Stir` again to reproduce the original domain, and the planner
correctly reports failure:

```
=== NO PLAN FOUND ===
unreachable goal literals: ['mixed(cup)']
```

`test_reasoners.py` asserts all of this: that a plan is found, that an independent replay
of it achieves the goal, that an unreachable goal is reported as a failure, and that every
causal link is a real producer/consumer pair.

### The fuzzy membership functions do not partition the domain

A well-formed fuzzy partition sums to roughly 1 everywhere, with adjacent sets crossing at
0.5. These do not:

| Speed (km/h) | 0 | 40 | 80 | 120 | 140 | 180 | 190+ |
|---|---|---|---|---|---|---|---|
| Total membership | 1.00 | 0.33 | 0.80 | 0.40 | 0.33 | 1.00 | **0.00** |

`medium` is `tri(40, 90, 140)` and `fast` is `tri(120, 180, 180)`: medium reaches zero at
140 while fast has only climbed to 0.33. That leaves troughs where the rule base barely
fires, and **above 180 km/h nothing fires at all**: the controller has no opinion about the
fastest inputs it is meant to judge.

That coverage gap is what makes risk non-monotone: it dips by 1.87 at 120 km/h and 0.32 at
140 as speed *increases*. The test allows those known dips and fails if they grow.

### The rule base is purely disjunctive

All **14 of 14** rules have a single antecedent, `([('hypertensive','X')],
('has_diabetes','X'))` and thirteen of the same shape. Any one indicator is therefore
sufficient for a diagnosis, confirmed by running a patient with only high blood pressure.
The inference engine is sound with respect to its rules; it is the rules that are weak.
Conjunctive rules, or a score threshold, would reflect the domain better.

## Running it

```bash
pip install -r requirements.txt
python test_reasoners.py        # the property tests above
jupyter notebook notebooks/
```

No datasets and no external services; everything is self-contained.

## Notes

Projects 1 and 3 began as group work (Tugas Kelompok); project 2 is individual. The
inference engine, planner and fuzzy controller are all original implementations rather than
library calls.

**One fix was required to run on current NumPy.** `fuzzify_speed` and `fuzzify_road` called
`float()` on a size-1 array, which NumPy 2.0 no longer permits:

```python
float(mf(v))                            # TypeError on NumPy >= 2
float(np.asarray(mf(v)).ravel()[0])     # explicit element access
```

The notebook was written against NumPy 1.x, where the implicit conversion was merely
deprecated. This is the only behavioural change made to the original code.
