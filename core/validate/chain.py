"""Ordered validator chain with one repair round."""

from __future__ import annotations

from core.validate.canned import build_canned_context
from core.validate.context import ValidationContext
from core.validate.models import ChainResult, CheckResult, FailAction
from core.validate.repair import apply_repairs
from core.validate.validators import VALIDATORS
from schemas.answer import ValidatorReport


def _run_all(ctx: ValidationContext) -> list[CheckResult]:
    return [fn(ctx) for fn in VALIDATORS]


def run_validation_chain(ctx: ValidationContext) -> tuple[ValidationContext, ChainResult]:
    checks = _run_all(ctx)
    hard = [c for c in checks if c.action == FailAction.HARD_FAIL and not c.passed]
    if hard:
        canned_ctx = build_canned_context(ctx, reason=hard[0].reason or "hard_fail")
        canned_checks = _run_all(canned_ctx)
        report = ChainResult(
            passed=all(c.passed for c in canned_checks),
            checks=checks + [CheckResult(validator="CannedFallback", passed=True, reason="applied")]
            + canned_checks,
            repairs_applied=0,
            used_canned=True,
            hard_fail_reason=hard[0].reason,
        )
        return canned_ctx, report

    repair_needed = [c for c in checks if c.action == FailAction.REPAIR and not c.passed]
    if repair_needed:
        repaired = apply_repairs(ctx, repair_needed)
        rechecks = _run_all(repaired)
        hard2 = [c for c in rechecks if c.action == FailAction.HARD_FAIL and not c.passed]
        if hard2:
            canned_ctx = build_canned_context(repaired, reason=hard2[0].reason or "hard_fail")
            canned_checks = _run_all(canned_ctx)
            report = ChainResult(
                passed=all(c.passed for c in canned_checks),
                checks=checks + rechecks
                + [CheckResult(validator="CannedFallback", passed=True, reason="applied")]
                + canned_checks,
                repairs_applied=1,
                used_canned=True,
                hard_fail_reason=hard2[0].reason,
            )
            return canned_ctx, report
        still_repair = [c for c in rechecks if c.action == FailAction.REPAIR and not c.passed]
        if still_repair:
            canned_ctx = build_canned_context(repaired, reason="repair_cap_exceeded")
            canned_checks = _run_all(canned_ctx)
            report = ChainResult(
                passed=all(c.passed for c in canned_checks),
                checks=checks + rechecks
                + [CheckResult(validator="CannedFallback", passed=True, reason="repair_cap")]
                + canned_checks,
                repairs_applied=1,
                used_canned=True,
                hard_fail_reason="repair_cap_exceeded",
            )
            return canned_ctx, report
        report = ChainResult(
            passed=all(c.passed for c in rechecks),
            checks=checks + rechecks,
            repairs_applied=1,
        )
        return repaired, report

    report = ChainResult(passed=all(c.passed for c in checks), checks=checks)
    return ctx, report


def to_validator_report(result: ChainResult) -> ValidatorReport:
    checks_dict = {
        c.validator: {"passed": c.passed, "reason": c.reason, "details": c.details}
        for c in result.checks
    }
    return ValidatorReport(
        passed=result.passed,
        checks=checks_dict,
        repairs=result.repairs_applied,
    )
