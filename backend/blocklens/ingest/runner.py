"""Run lifecycle: open an `ingest_run`, hand out a budget, close the books.

Every command wraps itself in `run_scope`, so three things are true of
every run without any command having to remember them:

* it exists in `ingest_run` with the git sha and config that produced it,
  before it does any work — a crashed run leaves a 'running' row, which is
  the evidence that it crashed;
* its budget starts from what the month has already spent, read from the
  ledger rather than from memory;
* whatever it spent is written to the ledger even when it fails, because a
  failed call still cost its allowance.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from sqlalchemy.orm import Session

from ..config import CONFIG, Config, git_sha
from ..store import write
from ..store.db import session_scope
from .budget import Budget, BudgetExhausted


@dataclass
class RunContext:
    session: Session
    budget: Budget
    run_id: int
    rows: int = 0
    notes: dict = field(default_factory=dict)

    def add_rows(self, n: int) -> None:
        self.rows += n


@contextmanager
def run_scope(*, source: str, scope: str | None = None, chain: str | None = None,
              max_calls: int | None = None, config: Config = CONFIG,
              budget_source: str = "alchemy") -> Iterator[RunContext]:
    """One run, bracketed. `budget_source` names the ledger the monthly CU
    ceiling is read from — the keyless sources spend no CU, so it only
    matters when the optional Alchemy path is switched on."""
    chain = chain or config.chain
    period = Budget.period()

    with session_scope() as session:
        _, cu_spent = write.read_budget(session, source=budget_source, period=period)
        budget = Budget(config=config, max_calls=max_calls, monthly_cu_used=cu_spent)
        run_id = write.start_run(
            session, source=source, chain=chain, scope=scope,
            config_json={
                "rpc_url": config.rpc_url, "rpc_log_span": config.rpc_log_span,
                "feature_window_hours": config.feature_window_hours,
                "max_calls": budget.max_calls, "alchemy": config.alchemy_enabled,
                "monthly_cu_used_at_start": cu_spent,
            },
            git_sha=git_sha(),
        )
        session.commit()

        ctx = RunContext(session=session, budget=budget, run_id=run_id)
        status, error = "completed", None
        try:
            yield ctx
        except BudgetExhausted as e:
            # Not a failure: the ceiling did its job. Recorded distinctly so
            # a partial dataset is never mistaken for a complete one.
            status, error = "stopped_budget", str(e)
        except KeyboardInterrupt:
            status, error = "failed", "interrupted by operator"
            raise
        except Exception as e:  # noqa: BLE001 - recorded, then re-raised
            status, error = "failed", f"{type(e).__name__}: {e}"
            raise
        finally:
            # The bookkeeping writes have to happen on a clean transaction.
            # On the error path the session may be poisoned by the very
            # failure being recorded, and PostgreSQL refuses every further
            # statement in an aborted transaction — which is how a failed
            # run first left no record of itself at all. Rolling back costs
            # nothing: the ingestors commit their own rows as they go.
            if status != "completed":
                session.rollback()
            for name, calls in budget.by_source.items():
                write.bump_budget(
                    session, source=name, period=period, requests=calls,
                    compute_units=budget.compute_units if name == budget_source else 0,
                )
            write.finish_run(
                session, run_id, status=status, requests_made=budget.requests,
                compute_units=budget.compute_units, rows_written=ctx.rows, error=error,
            )
            session.commit()
