import pydantic
import datetime

from enum import Enum

class Workload(Enum):
	kv_95pct_reads = "kv_95pct_reads"
	kv_50pct_reads = "kv_50pct_reads"
	kv_60pct_reads = "kv_60pct_reads"
	kv_10pct_reads = "kv_10pct_reads"
	movr = "movr"

class Cockroachdb_Results(pydantic.BaseModel):
    Workload: Workload
    Concurrency: int = pydantic.Field(gt=0)
    Average: float = pydantic.Field(allow_inf_nan=False, ge=0)
    Deviation: float = pydantic.Field(allow_inf_nan=False, ge=0)
    Start_Date: datetime.datetime
    End_Date: datetime.datetime
