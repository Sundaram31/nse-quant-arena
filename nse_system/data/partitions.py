"""
3-Stage Quantitative Walk-Forward Dataset Partitioning Engine.
Enforces strict separation between In-Sample Training, Model Validation, and Blind Out-Of-Sample Verification.
"""
from enum import Enum
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import pandas as pd

class DatasetStage(Enum):
    TRAIN_BACKTEST = "TRAIN_BACKTEST"             # 4 Years: Strategy Training & Initial Backtest (Aug 2021 - Jun 2025)
    VALIDATION_REFINE = "VALIDATION_REFINE"       # 1 Year: Model Tuning & Regime Refinement (Jul 2025 - Jun 2026)
    OUT_OF_SAMPLE_VERIFY = "OUT_OF_SAMPLE_VERIFY" # Last 2 Months: Strict Blind Verification (Jun 2026 - Aug 2026)
    FULL_SERIES = "FULL_SERIES"                   # Complete 5-Year Walk-Forward Series (Aug 2021 - Aug 2026)

class DatasetPartitionManager:
    """Manages date windows and DataFrame slicing for quantitative model validation."""

    OOS_DAYS = 60    # Last 2 months held out for final verification
    VAL_DAYS = 425   # ~1 year held out for model refinement

    @classmethod
    def get_stage_date_range(
        cls,
        df: pd.DataFrame,
        stage: DatasetStage
    ) -> Tuple[datetime, datetime]:
        """Calculates exact timestamp boundaries for a given dataset stage."""
        if df.empty:
            now = datetime.now()
            return now, now

        max_dt = df.index.max()
        min_dt = df.index.min()
        if isinstance(max_dt, pd.Timestamp):
            max_dt = max_dt.to_pydatetime()
        if isinstance(min_dt, pd.Timestamp):
            min_dt = min_dt.to_pydatetime()

        oos_start = max_dt - timedelta(days=cls.OOS_DAYS)
        val_start = max_dt - timedelta(days=cls.VAL_DAYS)

        if stage == DatasetStage.OUT_OF_SAMPLE_VERIFY:
            return oos_start, max_dt
        elif stage == DatasetStage.VALIDATION_REFINE:
            return val_start, oos_start
        elif stage == DatasetStage.TRAIN_BACKTEST:
            return min_dt, val_start
        else: # FULL_SERIES
            return min_dt, max_dt

    @classmethod
    def slice_dataframe_by_stage(
        cls,
        df: pd.DataFrame,
        stage: DatasetStage
    ) -> pd.DataFrame:
        """Slices historical DataFrame to the requested quantitative partition."""
        if df.empty:
            return df

        start_dt, end_dt = cls.get_stage_date_range(df, stage)
        sliced = df[(df.index >= pd.Timestamp(start_dt)) & (df.index <= pd.Timestamp(end_dt))]
        return sliced

    @classmethod
    def get_partition_summary(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Returns structured metadata summary of all 3 partitions for UI and logging."""
        if df.empty:
            return {}

        t_start, t_end = cls.get_stage_date_range(df, DatasetStage.TRAIN_BACKTEST)
        v_start, v_end = cls.get_stage_date_range(df, DatasetStage.VALIDATION_REFINE)
        o_start, o_end = cls.get_stage_date_range(df, DatasetStage.OUT_OF_SAMPLE_VERIFY)

        df_train = cls.slice_dataframe_by_stage(df, DatasetStage.TRAIN_BACKTEST)
        df_val = cls.slice_dataframe_by_stage(df, DatasetStage.VALIDATION_REFINE)
        df_oos = cls.slice_dataframe_by_stage(df, DatasetStage.OUT_OF_SAMPLE_VERIFY)

        return {
            "train": {
                "label": "🧪 Stage 1: Strategy Training & Backtest",
                "range": f"{t_start.strftime('%d-%b-%Y')} to {t_end.strftime('%d-%b-%Y')}",
                "bars": len(df_train),
                "purpose": "Initial parameter discovery & rule formulation"
            },
            "validation": {
                "label": "🔬 Stage 2: Model Refinement & Tuning",
                "range": f"{v_start.strftime('%d-%b-%Y')} to {v_end.strftime('%d-%b-%Y')}",
                "bars": len(df_val),
                "purpose": "Regime testing, indicator optimization & filter tuning"
            },
            "oos_verification": {
                "label": "🛡️ Stage 3: Out-of-Sample Final Verification (Last 2 Months)",
                "range": f"{o_start.strftime('%d-%b-%Y')} to {o_end.strftime('%d-%b-%Y')}",
                "bars": len(df_oos),
                "purpose": "Strict blind validation with zero lookahead bias"
            }
        }
