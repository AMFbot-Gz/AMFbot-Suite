"""
Tests unitaires — SafetyGuard

Couvre :
  - Blocage sur chemins système interdits
  - Blocage sur skill blacklist
  - Blocage sur risk_level=critical
  - Confirmation requise sur risk_level=high
  - Plan entièrement safe
  - Whitelist skill critique
  - Plan multi-étapes mixte
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.safety_guard import (
    ExecutionPlan,
    ExecutionStep,
    SafetyGuard,
    SafetyReport,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def guard() -> SafetyGuard:
    return SafetyGuard()


def make_step(
    skill_name: str,
    risk_level: str = "low",
    params: dict = None,
    description: str = "",
) -> ExecutionStep:
    return ExecutionStep(
        skill_name=skill_name,
        params=params or {},
        risk_level=risk_level,
        description=description,
    )


def make_plan(*steps: ExecutionStep, intent: str = "test") -> ExecutionPlan:
    plan = ExecutionPlan(intent=intent)
    for step in steps:
        plan.add_step(step)
    return plan


# ── Tests : chemins interdits ─────────────────────────────────────────────────

class TestForbiddenPaths:

    def test_system_path_blocked(self, guard):
        """Accès à /System doit être bloqué."""
        step = make_step("read_file", params={"path": "/System/Library/secrets.plist"})
        plan = make_plan(step, intent="lire un fichier système")
        report = guard.check(plan)

        assert not report.is_safe
        assert len(report.blocked_steps) == 1
        assert "/System" in report.blocked_steps[0].reason

    def test_usr_bin_blocked(self, guard):
        """Accès à /usr/bin doit être bloqué."""
        step = make_step("execute", params={"path": "/usr/bin/rm"})
        plan = make_plan(step)
        report = guard.check(plan)

        assert not report.is_safe

    def test_home_path_allowed(self, guard):
        """Accès à ~/Documents doit être autorisé."""
        step = make_step("read_file", risk_level="low",
                         params={"path": "/Users/wiaamhadara/Documents/notes.txt"})
        plan = make_plan(step)
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation

    def test_private_etc_blocked(self, guard):
        """Accès à /private/etc doit être bloqué."""
        step = make_step("edit_file", params={"path": "/private/etc/hosts"})
        plan = make_plan(step)
        report = guard.check(plan)

        assert not report.is_safe


# ── Tests : blacklist skills ──────────────────────────────────────────────────

class TestSkillBlacklist:

    def test_blacklisted_skill_blocked(self, guard):
        """format_disk est dans la blacklist → bloqué."""
        step = make_step("format_disk", risk_level="critical")
        plan = make_plan(step)
        report = guard.check(plan)

        assert not report.is_safe
        assert "format_disk" in report.blocked_steps[0].reason

    def test_delete_all_blocked(self, guard):
        step = make_step("delete_all")
        plan = make_plan(step)
        assert not guard.check(plan).is_safe

    def test_normal_skill_allowed(self, guard):
        step = make_step("open_app", risk_level="low", params={"app_name": "Chrome"})
        plan = make_plan(step)
        assert guard.check(plan).is_safe


# ── Tests : niveaux de risque ─────────────────────────────────────────────────

class TestRiskLevels:

    def test_critical_blocked_by_default(self, guard):
        """risk_level=critical doit être bloqué sauf whitelist."""
        step = make_step("dangerous_action", risk_level="critical")
        plan = make_plan(step)
        report = guard.check(plan)

        assert not report.is_safe
        assert not report.blocked_steps[0].requires_confirmation

    def test_critical_whitelisted_allowed(self, guard):
        """get_time est dans skill_whitelist → autorisé même si critical."""
        step = make_step("get_time", risk_level="critical")
        plan = make_plan(step)
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation

    def test_high_requires_confirmation(self, guard):
        """risk_level=high → autorisé MAIS confirmation requise."""
        step = make_step("send_email", risk_level="high")
        plan = make_plan(step)
        report = guard.check(plan)

        assert report.is_safe           # autorisé
        assert report.needs_confirmation  # mais avec confirmation
        assert len(report.confirm_steps) == 1

    def test_medium_allowed_without_confirmation(self, guard):
        step = make_step("resize_window", risk_level="medium")
        plan = make_plan(step)
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation

    def test_low_allowed_without_confirmation(self, guard):
        step = make_step("get_time", risk_level="low")
        plan = make_plan(step)
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation


# ── Tests : plans multi-étapes ────────────────────────────────────────────────

class TestMultiStepPlans:

    def test_mixed_plan_blocked_if_one_blocked(self, guard):
        """Un plan est unsafe dès qu'une étape est bloquée."""
        plan = make_plan(
            make_step("open_app",    risk_level="low"),
            make_step("format_disk", risk_level="critical"),  # blacklisté
            make_step("get_time",    risk_level="low"),
        )
        report = guard.check(plan)

        assert not report.is_safe
        assert len(report.blocked_steps) == 1
        assert len(report.verdicts) == 3

    def test_all_safe_plan(self, guard):
        """Plan avec uniquement des étapes low/medium → safe sans confirmation."""
        plan = make_plan(
            make_step("open_app",       risk_level="low",    params={"app_name": "Chrome"}),
            make_step("get_system_info", risk_level="low"),
            make_step("resize_window",  risk_level="medium"),
        )
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation
        assert len(report.blocked_steps) == 0

    def test_plan_with_confirmation_step(self, guard):
        """Plan mixte low + high → safe mais confirmation requise."""
        plan = make_plan(
            make_step("open_app",   risk_level="low"),
            make_step("send_email", risk_level="high"),
        )
        report = guard.check(plan)

        assert report.is_safe
        assert report.needs_confirmation
        assert len(report.confirm_steps) == 1

    def test_empty_plan(self, guard):
        """Plan vide → safe trivial."""
        plan = make_plan()
        report = guard.check(plan)

        assert report.is_safe
        assert not report.needs_confirmation
        assert len(report.verdicts) == 0


# ── Tests : rapport ───────────────────────────────────────────────────────────

class TestSafetyReport:

    def test_report_summary_contains_intent(self, guard):
        plan = make_plan(
            make_step("open_app", risk_level="low"),
            intent="ouvrir une application",
        )
        report = guard.check(plan)
        summary = report.summary()

        assert "ouvrir une application" in summary
        assert "open_app" in summary

    def test_blocked_steps_list(self, guard):
        plan = make_plan(
            make_step("open_app",    risk_level="low"),
            make_step("format_disk", risk_level="critical"),
        )
        report = guard.check(plan)

        assert len(report.blocked_steps) == 1
        assert report.blocked_steps[0].step.skill_name == "format_disk"
