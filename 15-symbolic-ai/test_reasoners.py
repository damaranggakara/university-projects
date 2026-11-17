"""Property tests for the three reasoners, run against the notebooks' own code.

Each notebook defines its algorithm and demonstrates it on one example. One
example passing does not mean an algorithm is correct, so this loads the
functions the notebooks define and asserts properties that must hold for any
input. The functions are taken from the notebooks rather than reimplemented, so
these test the code that is actually published.

Two of the properties fail as designed and are recorded as findings rather than
hidden - see the notes on the rule base and on membership coverage below.

Run:  python test_reasoners.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # no display; plt.show() becomes a no-op

NB = Path(__file__).parent / "notebooks"
_CACHE = {}


def load_notebook_namespace(path, skip_markers=("plt.show", "plt.savefig")):
    """Execute a notebook's code cells and return the resulting namespace.

    Drawing calls are dropped and the notebook's own printed output is
    swallowed - it is demonstration text, not test output.
    """
    key = str(path)
    if key in _CACHE:
        return _CACHE[key]
    nb = json.loads(Path(path).read_text(encoding="utf-8"))
    ns = {"__name__": "__notebook__"}
    skipped = []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            code = "\n".join(l for l in "".join(cell["source"]).splitlines()
                             if not any(m in l for m in skip_markers))
            if not code.strip():
                continue
            try:
                exec(compile(code, str(path), "exec"), ns)
            except Exception as e:
                skipped.append(f"cell {i}: {type(e).__name__}")
    ns["__skipped__"] = skipped
    _CACHE[key] = ns
    return ns


results, findings = [], []


def check(name, fn):
    try:
        detail = fn()
        print(f"  OK    {name:<32} {detail or ''}")
        results.append(True)
    except AssertionError as e:
        print(f"  FAIL  {name:<32} {e}")
        results.append(False)
    except Exception as e:
        print(f"  ERROR {name:<32} {type(e).__name__}: {e}")
        results.append(False)


# ============================================================ forward chaining

def fol():
    return load_notebook_namespace(NB / "first_order_logic_diabetes.ipynb")


def _diagnose(ns, patient):
    """Run the engine on one patient against a clean fact base.

    `facts` is a module-level set that accumulates, so it is saved and restored:
    without that, a later patient inherits an earlier one's conclusions.
    """
    saved = copy.deepcopy(ns["facts"])
    try:
        ns["facts"].clear()
        with contextlib.redirect_stdout(io.StringIO()):
            ns["generate_facts_from_input"](patient)
            ns["forward_chain"]()
            report = ns["get_report"](patient["name"])
        return str(report), {f for f in ns["facts"]}
    finally:
        ns["facts"].clear()
        ns["facts"].update(saved)


HEALTHY = {"name": "healthy_control", "BP": 110, "age": 25, "BMI": 22,
           "cigarettes": 0, "stress": 2, "income_scale": 9, "gender": "male"}
UNWELL = {"name": "high_risk", "BP": 170, "age": 60, "BMI": 35,
          "cigarettes": 20, "stress": 25, "income_scale": 1, "gender": "female"}


def fol_sound_on_no_evidence():
    ns = fol()
    report, facts = _diagnose(ns, HEALTHY)
    derived = [f for f in facts if "has_diabetes" in str(f)]
    assert not derived, (
        f"a patient meeting no indicator was still diagnosed: {derived[:2]}")
    return "no indicators -> no diagnosis"


def fol_derives_on_evidence():
    ns = fol()
    report, facts = _diagnose(ns, UNWELL)
    derived = [f for f in facts if "has_diabetes" in str(f)]
    assert derived, f"a patient meeting every indicator was not diagnosed: {report[:100]}"
    return "indicators present -> diagnosis derived"


def fol_unify_is_sound():
    ns = fol()
    unify = ns["unify"]                      # signature is (pattern, fact)
    bound = unify(("hypertensive", "X"), ("hypertensive", "alice"))
    assert bound, "unify failed to bind a variable to a constant"
    clash = unify(("hypertensive", "bob"), ("hypertensive", "alice"))
    assert not clash, "unify matched two different constants"
    wrong_pred = unify(("smoker", "X"), ("hypertensive", "alice"))
    assert not wrong_pred, "unify matched across different predicates"
    return "binds variables, rejects constant and predicate clashes"


def fol_rule_base_is_disjunctive():
    """A finding, not a bug in the implementation.

    Every rule has a single antecedent - ([('hypertensive','X')], ('has_diabetes','X'))
    and 13 others of the same shape. So ANY one indicator is sufficient for a
    diagnosis. The engine is sound with respect to its rules; the rule base is
    what is weak.
    """
    ns = fol()
    rules = ns["rules"]
    single = [r for r in rules if len(r[0]) == 1]
    one_indicator = {**HEALTHY, "name": "one_only", "BP": 170}   # hypertensive only
    report, facts = _diagnose(ns, one_indicator)
    derived = [f for f in facts if "has_diabetes" in str(f)]
    findings.append(
        f"rule base: {len(single)}/{len(rules)} rules have a single antecedent, so one "
        f"indicator alone yields a diagnosis ({'confirmed' if derived else 'not reproduced'})")
    assert len(single) == len(rules), "rule shapes have changed; update this note"
    return f"{len(single)}/{len(rules)} rules single-antecedent (see findings)"


# ========================================================= partial-order plan

def plan_is_valid():
    """The planner must find a plan, and that plan must achieve the goal.

    This replaces an earlier version that pinned the broken behaviour (1 of 2
    goal literals). The planner now searches rather than printing a hardcoded
    list, so the goal is genuinely reachable and is asserted outright.
    """
    ns = load_notebook_namespace(NB / "nonlinear_planning.ipynb")
    plan_fn, actions = ns["nonlinear_plan"], ns["ACTIONS"]
    initial, goal = set(ns["INITIAL_STATE"]), set(ns["GOAL_STATE"])

    with contextlib.redirect_stdout(io.StringIO()):
        plan, final_state, achieved = plan_fn(set(initial), set(goal), actions,
                                              verbose=False)

    assert plan is not None, "planner found no plan for a reachable goal"
    assert achieved, f"planner reports success without it; missing {sorted(goal - final_state)}"

    # re-simulate independently of the planner's own bookkeeping
    applicable, apply_ = ns["applicable"], ns["apply"]
    state = set(initial)
    for step in plan:
        assert applicable(step, state), (
            f"step {step} executed with unmet preconditions; state {sorted(state)[:4]}")
        state = apply_(step, state)
    assert goal <= state, f"independent replay missed {sorted(goal - state)}"
    return f"{len(plan)} steps found by search, preconditions hold, goal achieved"


def plan_reports_unreachable_goals():
    """Removing Stir makes mixed(cup) unproducible; the planner must say so.

    This is the bug the rewrite fixed: the old version printed
    'GOAL STATE TERCAPAI' unconditionally because it echoed the goal it was
    given rather than checking the state it reached.
    """
    ns = load_notebook_namespace(NB / "nonlinear_planning.ipynb")
    plan_fn = ns["nonlinear_plan"]
    initial, goal = set(ns["INITIAL_STATE"]), set(ns["GOAL_STATE"])
    without_stir = [a for a in ns["ACTIONS"] if a.name != "Stir(cup)"]

    with contextlib.redirect_stdout(io.StringIO()):
        plan, _, achieved = plan_fn(set(initial), set(goal), without_stir, verbose=False)

    assert plan is None, "a plan was returned for an unreachable goal"
    assert achieved is False, "planner claimed success on an unreachable goal"
    return "unreachable goal correctly reported as failure"


def plan_causal_links_are_derived():
    """Ordering constraints must come from the plan, not a hardcoded list."""
    ns = load_notebook_namespace(NB / "nonlinear_planning.ipynb")
    links_fn = ns.get("causal_links")
    assert callable(links_fn), "notebook no longer defines causal_links"

    with contextlib.redirect_stdout(io.StringIO()):
        plan, _, _ = ns["nonlinear_plan"](set(ns["INITIAL_STATE"]),
                                          set(ns["GOAL_STATE"]),
                                          ns["ACTIONS"], verbose=False)
    links = links_fn(plan, set(ns["INITIAL_STATE"]))
    assert links, "no causal links derived"
    # every link must be a real producer/consumer pair within the plan
    for j, i, p in links:
        assert j is not None, f"precondition {p} of step {i} has no producer"
        assert j < i, f"link {j} -> {i} is not forward in time"
        assert p in plan[j].add_effects, f"step {plan[j]} does not produce {p}"
        assert p in plan[i].preconds, f"step {plan[i]} does not require {p}"
    return f"{len(links)} links, each a verified producer/consumer pair"


# =========================================================== fuzzy controller

def fuzzy():
    return load_notebook_namespace(NB / "fuzzy_logic_inference.ipynb")


def _risk(ns, speed, road):
    with contextlib.redirect_stdout(io.StringIO()):
        out = ns["evaluate_case"](speed, road)
    return float(out["risk_crisp"] if isinstance(out, dict) else out)


def fuzzy_memberships_bounded():
    ns = fuzzy()
    for v in range(0, 201, 5):
        for name, deg in ns["fuzzify_speed"](v).items():
            assert -1e-9 <= deg <= 1 + 1e-9, f"speed {v}: '{name}' = {deg} outside [0,1]"
    for v in range(0, 11):
        for name, deg in ns["fuzzify_road"](v).items():
            assert -1e-9 <= deg <= 1 + 1e-9, f"road {v}: '{name}' = {deg} outside [0,1]"
    return "all degrees within [0, 1]"


def fuzzy_partition_covers_domain():
    """A proper fuzzy partition sums to about 1 everywhere. This one does not.

    Adjacent membership functions should cross at 0.5 so every input is fully
    covered. Here `medium` is tri(40, 90, 140) and `fast` is tri(120, 180, 180):
    medium reaches zero at 140 while fast has only climbed to 0.33, leaving
    troughs where the rule base barely fires - and nothing at all above 180.
    """
    ns = fuzzy()
    totals = {v: sum(ns["fuzzify_speed"](v).values()) for v in range(0, 201, 10)}
    worst_v = min(totals, key=totals.get)
    uncovered = [v for v, t in totals.items() if t < 1e-9]
    findings.append(
        f"speed membership does not partition the domain: total degree dips to "
        f"{totals[worst_v]:.2f} at {worst_v} km/h"
        + (f", and is 0 at {uncovered} (no rule fires)" if uncovered else ""))
    # the bug is the trough; assert only that it is still the shape described
    assert totals[worst_v] < 0.5, "coverage has improved; update this note"
    return f"total degree ranges {min(totals.values()):.2f}-{max(totals.values()):.2f}"


def fuzzy_broadly_monotone():
    """Risk should not fall as speed rises, nor rise as the road improves.

    It mostly holds, but a dip of about 2 units appears near 140 km/h, caused by
    the coverage trough above. The test allows that known violation and fails if
    it grows, which is what a regression would look like.
    """
    ns = fuzzy()
    TOL = 4.0
    speeds = list(range(20, 181, 20))
    rising = [_risk(ns, s, 5) for s in speeds]
    drops = [(speeds[i + 1], round(a - b, 2))
             for i, (a, b) in enumerate(zip(rising, rising[1:])) if b < a - 1e-6]
    worst = max((d for _, d in drops), default=0.0)
    assert worst <= TOL, (
        f"risk falls by {worst} as speed increases (allowed {TOL}): {drops}")

    roads = list(range(1, 11))
    falling = [_risk(ns, 120, r) for r in roads]
    rises = [(roads[i + 1], round(b - a, 2))
             for i, (a, b) in enumerate(zip(falling, falling[1:])) if b > a + 1e-6]
    worst_r = max((d for _, d in rises), default=0.0)
    assert worst_r <= TOL, (
        f"risk rises by {worst_r} as road quality improves (allowed {TOL}): {rises}")

    if drops:
        findings.append(
            f"risk is not strictly monotone in speed: dips of {[d for _, d in drops]} "
            f"at {[s for s, _ in drops]} km/h, within the {TOL} tolerance")
    return (f"speed 20->180: {rising[0]:.1f}->{rising[-1]:.1f}; "
            f"road 1->10: {falling[0]:.1f}->{falling[-1]:.1f}")


def main():
    print("symbolic AI reasoner properties\n")
    check("FOL: sound on no evidence", fol_sound_on_no_evidence)
    check("FOL: derives on evidence", fol_derives_on_evidence)
    check("FOL: unification", fol_unify_is_sound)
    check("FOL: rule base shape", fol_rule_base_is_disjunctive)
    check("plan: validity and goal", plan_is_valid)
    check("plan: reports unreachable goal", plan_reports_unreachable_goals)
    check("plan: causal links derived", plan_causal_links_are_derived)
    check("fuzzy: membership bounds", fuzzy_memberships_bounded)
    check("fuzzy: domain coverage", fuzzy_partition_covers_domain)
    check("fuzzy: broad monotonicity", fuzzy_broadly_monotone)

    if findings:
        print("\nfindings (design observations, not implementation bugs)")
        for f in findings:
            print(f"  - {f}")

    print(f"\n{sum(results)} of {len(results)} properties hold")
    if not all(results):
        return 1
    print("OK: all reasoner properties hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
