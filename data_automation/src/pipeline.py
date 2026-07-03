from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = BASE_DIR / "input"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


def create_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("gericare-data-automation")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def read_csv(spark: SparkSession, input_dir: Path, name: str) -> DataFrame:
    csv_path = input_dir / f"{name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(str(csv_path))
    )


def quality_report(residents: DataFrame, vitals: DataFrame, output_dir: Path) -> None:
    checks = [
        (
            "residents_missing_required_fields",
            residents.filter(
                F.col("resident_id").isNull()
                | F.col("name").isNull()
                | (F.length(F.trim("name")) == 0)
                | F.col("room").isNull()
            ).count(),
        ),
        (
            "residents_invalid_age",
            residents.filter((F.col("age") < 60) | (F.col("age") > 115)).count(),
        ),
        (
            "vitals_pressure_out_of_range",
            vitals.filter(
                (F.col("systolic") < 80)
                | (F.col("systolic") > 220)
                | (F.col("diastolic") < 40)
                | (F.col("diastolic") > 130)
            ).count(),
        ),
        (
            "vitals_invalid_pain_score",
            vitals.filter((F.col("pain_score") < 0) | (F.col("pain_score") > 10)).count(),
        ),
    ]
    spark = residents.sparkSession
    report = None
    for check_name, failed_rows in checks:
        row = spark.range(1).select(
            F.lit(check_name).alias("check_name"),
            F.lit(int(failed_rows)).alias("failed_rows"),
        )
        report = row if report is None else report.unionByName(row)

    if report is None:
        return

    report.coalesce(1).write.mode("overwrite").option("header", True).csv(
        str(output_dir / "quality" / "quality_report.csv")
    )


def build_pipeline(input_dir: Path, output_dir: Path) -> None:
    spark = create_spark()

    residents_raw = read_csv(spark, input_dir, "residents")
    vitals_raw = read_csv(spark, input_dir, "vitals")
    medications_raw = read_csv(spark, input_dir, "medications")
    tasks_raw = read_csv(spark, input_dir, "tasks")

    residents = (
        residents_raw.select(
            F.col("resident_id").cast("int"),
            F.initcap(F.trim("name")).alias("name"),
            F.col("age").cast("int"),
            F.upper(F.trim("room")).alias("room"),
            F.lower(F.trim("condition")).alias("condition"),
            F.initcap(F.trim("primary_contact")).alias("primary_contact"),
            F.regexp_replace(F.col("contact_phone").cast("string"), "[^0-9]", "").alias("contact_phone"),
            F.lower(F.trim("mobility")).alias("mobility"),
            F.col("fall_risk").cast("int"),
            F.to_timestamp("updated_at").alias("updated_at"),
        )
        .dropDuplicates(["resident_id"])
        .filter(F.col("resident_id").isNotNull())
    )

    vitals = (
        vitals_raw.select(
            F.col("resident_id").cast("int"),
            F.to_timestamp("measured_at").alias("measured_at"),
            F.col("systolic").cast("int"),
            F.col("diastolic").cast("int"),
            F.col("glucose").cast("int"),
            F.col("pain_score").cast("int"),
            F.col("hydration_ml").cast("int"),
        )
        .filter(F.col("resident_id").isNotNull())
        .dropDuplicates(["resident_id", "measured_at"])
    )

    medications = medications_raw.select(
        F.col("resident_id").cast("int"),
        F.initcap(F.trim("medication")).alias("medication"),
        F.trim("dose").alias("dose"),
        F.to_timestamp("scheduled_at").alias("scheduled_at"),
        F.lower(F.trim("status")).alias("status"),
    )

    tasks = tasks_raw.select(
        F.col("resident_id").cast("int"),
        F.trim("task").alias("task"),
        F.lower(F.trim("category")).alias("category"),
        F.to_timestamp("scheduled_at").alias("scheduled_at"),
        F.lower(F.trim("priority")).alias("priority"),
        F.lower(F.trim("status")).alias("status"),
    )

    latest_vitals = (
        vitals.withColumn(
            "row_number",
            F.row_number().over(
                Window.partitionBy("resident_id").orderBy(F.col("measured_at").desc())
            ),
        )
        .filter(F.col("row_number") == 1)
        .drop("row_number")
    )

    pending_tasks = (
        tasks.filter(F.col("status") != "done")
        .groupBy("resident_id")
        .agg(
            F.count("*").alias("pending_tasks"),
            F.sum(F.when(F.col("priority") == "high", 1).otherwise(0)).alias("high_priority_tasks"),
        )
    )

    pending_meds = (
        medications.filter(F.col("status") != "given")
        .groupBy("resident_id")
        .agg(F.count("*").alias("pending_medications"))
    )

    risk = (
        residents.join(latest_vitals, "resident_id", "left")
        .join(pending_tasks, "resident_id", "left")
        .join(pending_meds, "resident_id", "left")
        .fillna({"pending_tasks": 0, "high_priority_tasks": 0, "pending_medications": 0})
        .withColumn(
            "risk_score",
            F.lit(0)
            + F.when(F.col("age") >= 90, 2).when(F.col("age") >= 80, 1).otherwise(0)
            + F.when(F.col("systolic") >= 160, 2).when(F.col("systolic") >= 145, 1).otherwise(0)
            + F.when(F.col("pain_score") >= 7, 2).when(F.col("pain_score") >= 4, 1).otherwise(0)
            + F.when(F.col("glucose") >= 180, 2).when(F.col("glucose") >= 140, 1).otherwise(0)
            + F.when(F.col("hydration_ml") < 1000, 2).when(F.col("hydration_ml") < 1300, 1).otherwise(0)
            + F.when(F.col("fall_risk") >= 7, 2).when(F.col("fall_risk") >= 5, 1).otherwise(0)
            + F.when(F.col("high_priority_tasks") > 0, 1).otherwise(0),
        )
        .withColumn(
            "risk_level",
            F.when(F.col("risk_score") >= 7, "critico")
            .when(F.col("risk_score") >= 4, "observacao")
            .otherwise("estavel"),
        )
    )

    shift_board = risk.select(
        "resident_id",
        "name",
        "room",
        "condition",
        "risk_score",
        "risk_level",
        "pending_tasks",
        "pending_medications",
        "systolic",
        "diastolic",
        "pain_score",
        "hydration_ml",
    ).orderBy(F.col("risk_score").desc(), "room")

    family_follow_up = risk.select(
        "resident_id",
        "name",
        "room",
        "primary_contact",
        "contact_phone",
        "risk_level",
        F.when(
            F.col("risk_level") == "critico",
            F.concat(F.lit("Atualizar familiar sobre prioridade clinica de "), F.col("name")),
        )
        .when(
            F.col("risk_level") == "observacao",
            F.concat(F.lit("Enviar resumo preventivo do plantao para "), F.col("primary_contact")),
        )
        .otherwise(F.lit("Sem contato proativo necessario")).alias("recommended_action"),
    )

    quality_report(residents, vitals, output_dir)

    residents.write.mode("overwrite").parquet(str(output_dir / "silver" / "residents"))
    vitals.write.mode("overwrite").parquet(str(output_dir / "silver" / "vitals"))
    medications.write.mode("overwrite").parquet(str(output_dir / "silver" / "medications"))
    tasks.write.mode("overwrite").parquet(str(output_dir / "silver" / "tasks"))
    risk.write.mode("overwrite").parquet(str(output_dir / "gold" / "resident_risk_summary"))
    shift_board.coalesce(1).write.mode("overwrite").option("header", True).csv(
        str(output_dir / "gold" / "shift_board")
    )
    family_follow_up.coalesce(1).write.mode("overwrite").option("header", True).csv(
        str(output_dir / "gold" / "family_follow_up")
    )

    print(f"Pipeline finished. Outputs written to {output_dir}")
    spark.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GeriCare spreadsheet automation pipeline")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_DIR),
        help="Input folder with CSV spreadsheets",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output folder for silver/gold datasets",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_pipeline(Path(args.input), Path(args.output))
