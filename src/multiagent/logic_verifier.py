"""
Sprint 4.1: Standalone Deterministic Propositional Logic Verification Engine

Provides deterministic, mathematical logical verification using SymPy:
1. normalize_logical_formula: Translates MMLU / textbook Unicode logical symbols into SymPy expressions.
2. verify_argument_validity: Determines deductive validity via satisfiability (SAT) checking.
3. verify_counterexample_candidate: Verifies whether a candidate truth assignment constitutes a genuine counterexample.

Constraints:
- Pure deterministic computation (Zero LLM reliance).
- Returns structured dictionaries, not print statements.
- Unsupported constructs (first-order logic, predicates, natural language) return NOT_APPLICABLE.
- Malformed inputs return PARSE_FAILURE without crashing.
"""

import re
import ast
from typing import Dict, Any, List, Optional, Sequence, Union, Tuple
from sympy import symbols, Not, And, Or, Implies, Equivalent, true, false
from sympy.logic.boolalg import Boolean
from sympy.logic.inference import satisfiable


class LogicParseError(Exception):
    """Raised when a formula has malformed syntax."""
    pass


class UnsupportedLogicError(Exception):
    """Raised when an expression involves first-order predicate logic or natural language."""
    pass


# First-order logic and natural language indicator patterns
UNSUPPORTED_PATTERNS = [
    r"[∀∃]",                          # Quantifiers: universal / existential
    r"\\forall|\\exists",             # LaTeX quantifiers
    r"\([∀∃]?[a-z]\)",                # Quantifier parenthetical: (x), (∀x), (∃x)
    r"[A-Za-z]+\s+[A-Za-z]+",         # Multi-word natural language sentences
]

PRED_RELATION_PATTERN = re.compile(r"^[A-Z][a-z0-9_]{1,4}$")
FUNCTIONAL_LOGIC_NAMES = {"true", "false", "implies", "and", "or", "not", "equivalent"}


def _is_unsupported(expr_str: str) -> bool:
    """Detects whether an expression involves first-order logic or natural language."""
    if not expr_str or not isinstance(expr_str, str):
        return True
    
    s = expr_str.strip()
    if not s:
        return True

    for pat in UNSUPPORTED_PATTERNS:
        if re.search(pat, s):
            return True

    # Check for relations like Txy, Tdc (starts with capital, followed by lower-case variables)
    tokens = re.findall(r"[A-Za-z0-9_]+", s)
    for tok in tokens:
        if tok.lower() in FUNCTIONAL_LOGIC_NAMES:
            continue
        if PRED_RELATION_PATTERN.match(tok):
            return True

    return False


class PropositionalLogicParser:
    """
    Deterministic Pratt parser for propositional logic formulas.
    Converts Unicode symbols (⊃, •, ∨, ¬, ∧, →, ↔, ≡, ~) into SymPy Boolean expressions.
    """

    def __init__(self, expr_str: str):
        self.raw_str = expr_str
        self.tokens = self._tokenize(expr_str)
        self.pos = 0

    def _tokenize(self, s: str) -> List[Tuple[str, str]]:
        # Normalize Unicode symbols
        s = s.replace("\u2022", "&").replace("\u2219", "&").replace("\u22c5", "&")
        s = s.replace("•", "&").replace("∧", "&").replace("^", "&")
        s = s.replace("∨", "|")
        s = s.replace("¬", "~").replace("!", "~")
        s = s.replace("⊃", ">>").replace("→", ">>").replace("->", ">>")
        s = s.replace("↔", "<->").replace("≡", "<->").replace("<=>", "<->")

        token_spec = [
            ("EQUIV", r"<->"),
            ("IMPLIES", r">>"),
            ("AND", r"&"),
            ("OR", r"\|"),
            ("NOT", r"~"),
            ("LPAREN", r"\("),
            ("RPAREN", r"\)"),
            ("COMMA", r","),
            ("VAR", r"[A-Za-z][A-Za-z0-9_]*"),
            ("SKIP", r"\s+"),
            ("MISMATCH", r"."),
        ]
        tok_regex = "|".join(f"(?P<{pair[0]}>{pair[1]})" for pair in token_spec)
        tokens = []
        for mo in re.finditer(tok_regex, s):
            kind = mo.lastgroup
            val = mo.group()
            if kind == "SKIP":
                continue
            elif kind == "MISMATCH":
                raise LogicParseError(f"Unexpected character in formula: {val!r}")
            tokens.append((kind, val))
        return tokens

    def _current_token(self) -> Tuple[Optional[str], Optional[str]]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def _consume(self, expected_kind: Optional[str] = None) -> Tuple[str, str]:
        tok = self._current_token()
        if tok[0] is None:
            raise LogicParseError("Unexpected end of formula")
        if expected_kind and tok[0] != expected_kind:
            raise LogicParseError(f"Expected token {expected_kind}, got {tok[0]} ({tok[1]})")
        self.pos += 1
        return tok

    def parse(self) -> Boolean:
        if not self.tokens:
            raise LogicParseError("Empty formula string")
        res = self._parse_expr(0)
        if self.pos < len(self.tokens):
            extra_tok = self.tokens[self.pos]
            raise LogicParseError(f"Unexpected token at end of formula: {extra_tok[1]}")
        return res

    def _parse_expr(self, min_prec: int) -> Boolean:
        tok_kind, tok_val = self._current_token()

        if tok_kind == "NOT":
            self._consume("NOT")
            left = Not(self._parse_expr(5))
        elif tok_kind == "LPAREN":
            self._consume("LPAREN")
            left = self._parse_expr(0)
            self._consume("RPAREN")
        elif tok_kind == "VAR":
            self._consume("VAR")
            # Functional notation support: Implies(A, B), And(A, B), Or(A, B), Not(A), Equivalent(A, B)
            next_kind, _ = self._current_token()
            if next_kind == "LPAREN" and tok_val in ("Implies", "And", "Or", "Not", "Equivalent"):
                self._consume("LPAREN")
                args = []
                while True:
                    args.append(self._parse_expr(0))
                    curr_k, _ = self._current_token()
                    if curr_k == "COMMA":
                        self._consume("COMMA")
                    elif curr_k == "RPAREN":
                        self._consume("RPAREN")
                        break
                    else:
                        raise LogicParseError("Expected ',' or ')' in function call")
                if tok_val == "Implies":
                    if len(args) != 2:
                        raise LogicParseError("Implies requires exactly 2 arguments")
                    left = Implies(args[0], args[1])
                elif tok_val == "Not":
                    if len(args) != 1:
                        raise LogicParseError("Not requires exactly 1 argument")
                    left = Not(args[0])
                elif tok_val == "And":
                    left = And(*args)
                elif tok_val == "Or":
                    left = Or(*args)
                elif tok_val == "Equivalent":
                    left = Equivalent(*args)
            elif tok_val.lower() == "true":
                left = true
            elif tok_val.lower() == "false":
                left = false
            else:
                if PRED_RELATION_PATTERN.match(tok_val):
                    raise UnsupportedLogicError(f"Predicate logic relation '{tok_val}' is not supported.")
                left = symbols(tok_val)
        else:
            raise LogicParseError(f"Expected variable or prefix operator, got {tok_kind} ({tok_val})")

        # Operator Precedences (Standard formal logic rules):
        # 1: Equivalence (<->) non-assoc
        # 2: Implication (>>) right-assoc
        # 3: Disjunction (|) left-assoc
        # 4: Conjunction (&) left-assoc
        precedences = {
            "EQUIV": (1, False),
            "IMPLIES": (2, True),
            "OR": (3, False),
            "AND": (4, False),
        }

        while True:
            k, _ = self._current_token()
            if k not in precedences:
                break
            prec, right_assoc = precedences[k]
            if prec < min_prec:
                break
            self._consume(k)
            next_prec = prec if right_assoc else prec + 1
            right = self._parse_expr(next_prec)

            if k == "EQUIV":
                left = Equivalent(left, right)
            elif k == "IMPLIES":
                left = Implies(left, right)
            elif k == "OR":
                left = Or(left, right)
            elif k == "AND":
                left = And(left, right)

        return left


def parse_to_sympy(expr: str) -> Boolean:
    """
    Parses a propositional formula string into a SymPy Boolean expression.
    Raises:
    - UnsupportedLogicError if formula contains predicate logic or natural language.
    - LogicParseError if formula has invalid syntax.
    """
    if not isinstance(expr, str):
        raise LogicParseError(f"Formula must be a string, got {type(expr)}")
    
    clean_expr = expr.strip()
    if not clean_expr:
        raise LogicParseError("Formula is empty")

    if _is_unsupported(clean_expr):
        raise UnsupportedLogicError(f"Expression contains unsupported logic: {clean_expr!r}")

    parser = PropositionalLogicParser(clean_expr)
    return parser.parse()


def normalize_logical_formula(expr: str) -> Optional[str]:
    """
    Normalizes a propositional logical formula into a SymPy-compatible string.

    Supports MMLU notation:
    - Implication: ⊃, →, ->, >>
    - Conjunction: •, ∧, &, ^
    - Disjunction: ∨, |
    - Negation: ¬, ~, !
    - Equivalence: ↔, ≡, <->, <=>

    Returns:
    - A normalized string representation parseable by SymPy.
    - None if the expression is malformed or unsupported (never crashes).
    """
    try:
        parsed = parse_to_sympy(expr)
        return str(parsed)
    except (LogicParseError, UnsupportedLogicError, Exception):
        return None


def verify_argument_validity(
    premises: Sequence[str],
    conclusion: str,
) -> Dict[str, Any]:
    """
    Determines whether a propositional argument is deductively valid.
    An argument is valid iff (Premises & ~Conclusion) is UNSATISFIABLE.

    Returns structured dictionary:
    {
        "status": "VALID" | "INVALID" | "NOT_APPLICABLE" | "PARSE_FAILURE",
        "is_valid": bool or None,
        "counterexample": Optional[Dict[str, bool]],
        "reason": str,
        "premises": List[str],
        "conclusion": str,
        "variables": List[str]
    }
    """
    res: Dict[str, Any] = {
        "status": "NOT_APPLICABLE",
        "is_valid": None,
        "counterexample": None,
        "reason": "",
        "premises": list(premises) if premises else [],
        "conclusion": str(conclusion) if conclusion else "",
        "variables": [],
    }

    if not premises:
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = "Premises list is empty; cannot evaluate validity."
        return res

    if conclusion is None or str(conclusion).strip() == "":
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = "Conclusion is empty; cannot evaluate validity."
        return res

    # 1. Check for unsupported first-order logic or natural language
    for p in premises:
        if _is_unsupported(p):
            res["status"] = "NOT_APPLICABLE"
            res["reason"] = f"Unsupported logic or natural language in premise: {p!r}"
            return res

    if _is_unsupported(conclusion):
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = f"Unsupported logic or natural language in conclusion: {conclusion!r}"
        return res

    # 2. Parse formulas into SymPy objects
    parsed_premises = []
    try:
        for p in premises:
            parsed_premises.append(parse_to_sympy(p))
        parsed_conclusion = parse_to_sympy(conclusion)
    except UnsupportedLogicError as e:
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = str(e)
        return res
    except LogicParseError as e:
        res["status"] = "PARSE_FAILURE"
        res["reason"] = f"Parse failure in argument formula: {e}"
        return res
    except Exception as e:
        res["status"] = "PARSE_FAILURE"
        res["reason"] = f"Unexpected parse failure: {e}"
        return res

    # 3. Extract all variables
    all_syms = set().union(*(p.free_symbols for p in parsed_premises))
    all_syms = all_syms.union(parsed_conclusion.free_symbols)
    res["variables"] = sorted(str(s) for s in all_syms)

    # 4. Formulate the falsification formula: Premises & ~Conclusion
    if len(parsed_premises) == 1:
        prem_conj = parsed_premises[0]
    else:
        prem_conj = And(*parsed_premises)

    falsification_expr = And(prem_conj, Not(parsed_conclusion))

    # 5. Check satisfiability via SymPy SAT solver
    try:
        sat_result = satisfiable(falsification_expr)
    except Exception as e:
        res["status"] = "PARSE_FAILURE"
        res["reason"] = f"SAT solver error: {e}"
        return res

    if sat_result is False:
        # UNSAT: No truth assignment can make premises true and conclusion false
        res["status"] = "VALID"
        res["is_valid"] = True
        res["counterexample"] = None
        res["reason"] = "Deductively valid: No truth assignment satisfies all premises while falsifying the conclusion."
    else:
        # SAT: Counterexample found
        res["status"] = "INVALID"
        res["is_valid"] = False
        counterexample_dict = {str(k): bool(v) for k, v in sat_result.items()}
        res["counterexample"] = counterexample_dict
        res["reason"] = f"Deductively invalid: Found counterexample assignment {counterexample_dict} where all premises are True and conclusion is False."

    return res


def normalize_assignment(assignment: Any) -> Dict[str, bool]:
    """Normalizes candidate truth assignments into a standard Dict[str, bool]."""
    if isinstance(assignment, str):
        assignment = ast.literal_eval(assignment)
    if not isinstance(assignment, dict):
        raise ValueError(f"Assignment must be a dictionary or dictionary string, got {type(assignment)}")

    normalized = {}
    for k, v in assignment.items():
        var_name = str(k).strip()
        if isinstance(v, bool):
            normalized[var_name] = v
        elif str(v).strip().lower() in ("true", "t", "1"):
            normalized[var_name] = True
        elif str(v).strip().lower() in ("false", "f", "0"):
            normalized[var_name] = False
        else:
            raise ValueError(f"Invalid boolean value for variable {var_name!r}: {v!r}")
    return normalized


def verify_counterexample_candidate(
    premises: Sequence[str],
    conclusion: str,
    assignment: Union[Dict[str, Any], str],
) -> Dict[str, Any]:
    """
    Verifies whether a specific truth assignment serves as a genuine counterexample.
    A counterexample strictly requires:
    1. All premises are TRUE under the assignment.
    2. The conclusion is FALSE under the assignment.

    Returns structured dictionary:
    {
        "status": "VALID_COUNTEREXAMPLE" | "NOT_A_COUNTEREXAMPLE" | "NOT_APPLICABLE" | "PARSE_FAILURE",
        "is_counterexample": bool or None,
        "premises_evaluations": Dict[str, bool],
        "all_premises_true": bool or None,
        "conclusion_evaluation": bool or None,
        "conclusion_false": bool or None,
        "assignment": Dict[str, bool],
        "reason": str
    }
    """
    res: Dict[str, Any] = {
        "status": "NOT_APPLICABLE",
        "is_counterexample": None,
        "premises_evaluations": {},
        "all_premises_true": None,
        "conclusion_evaluation": None,
        "conclusion_false": None,
        "assignment": {},
        "reason": "",
    }

    if not premises or not conclusion:
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = "Premises and conclusion must be non-empty."
        return res

    # Check for unsupported logic
    for p in premises:
        if _is_unsupported(p):
            res["status"] = "NOT_APPLICABLE"
            res["reason"] = f"Unsupported logic or natural language in premise: {p!r}"
            return res

    if _is_unsupported(conclusion):
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = f"Unsupported logic or natural language in conclusion: {conclusion!r}"
        return res

    # Parse assignment
    try:
        norm_assign = normalize_assignment(assignment)
        res["assignment"] = norm_assign
    except Exception as e:
        res["status"] = "PARSE_FAILURE"
        res["reason"] = f"Invalid truth assignment format: {e}"
        return res

    # Parse formulas
    try:
        parsed_premises = [parse_to_sympy(p) for p in premises]
        parsed_conclusion = parse_to_sympy(conclusion)
    except UnsupportedLogicError as e:
        res["status"] = "NOT_APPLICABLE"
        res["reason"] = str(e)
        return res
    except (LogicParseError, Exception) as e:
        res["status"] = "PARSE_FAILURE"
        res["reason"] = f"Formula parse failure: {e}"
        return res

    # Evaluate premises under assignment
    var_dict = {symbols(k): v for k, v in norm_assign.items()}
    prem_evals = {}
    for raw_p, parsed_p in zip(premises, parsed_premises):
        val = bool(parsed_p.subs(var_dict))
        prem_evals[raw_p] = val

    res["premises_evaluations"] = prem_evals
    all_prem_true = all(prem_evals.values())
    res["all_premises_true"] = all_prem_true

    # Evaluate conclusion under assignment
    concl_val = bool(parsed_conclusion.subs(var_dict))
    res["conclusion_evaluation"] = concl_val
    res["conclusion_false"] = (not concl_val)

    # Counterexample criterion: All premises TRUE AND Conclusion FALSE
    if all_prem_true and not concl_val:
        res["status"] = "VALID_COUNTEREXAMPLE"
        res["is_counterexample"] = True
        res["reason"] = "Valid counterexample: The given assignment makes all premises True and the conclusion False."
    else:
        res["status"] = "NOT_A_COUNTEREXAMPLE"
        res["is_counterexample"] = False
        failures = []
        if not all_prem_true:
            false_prems = [p for p, v in prem_evals.items() if not v]
            failures.append(f"Premise(s) evaluated to False: {false_prems}")
        if concl_val:
            failures.append(f"Conclusion evaluated to True ({conclusion} = True); counterexamples strictly require conclusion to be False")
        res["reason"] = "Not a counterexample: " + "; ".join(failures) + "."

    return res
