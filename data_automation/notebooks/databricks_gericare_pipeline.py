# Databricks notebook source
# MAGIC %md
# MAGIC # GeriCare Data Automation
# MAGIC Pipeline Spark para tratar planilhas operacionais do GeriCare em camadas bronze,
# MAGIC silver e gold.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

INPUT_PATH = "dbfs:/FileStore/gericare/input"
OUTPUT_PATH = "dbfs:/FileStore/gericare/output"

# COMMAND ----------

residents_raw = spark.read.option("header", True).option("inferSchema", True).csv(f"{INPUT_PATH}/residents.csv")
vitals_raw = spark.read.option("header", True).option("inferSchema", True).csv(f"{INPUT_PATH}/vitals.csv")
medications_raw = spark.read.option("header", True).option("inferSchema", True).csv(f"{INPUT_PATH}/medications.csv")
tasks_raw = spark.read.option("header", True).option("inferSchema", True).csv(f"{INPUT_PATH}/tasks.csv")

# COMMAND ----------

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

# COMMAND ----------

latest_vitals = (
    vitals.withColumn(
        "row_number",
        F.row_number().over(Window.partitionBy("resident_id").orderBy(F.col("measured_at").desc())),
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

# COMMAND ----------

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

# COMMAND ----------

residents.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/silver/residents")
vitals.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/silver/vitals")
medications.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/silver/medications")
tasks.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/silver/tasks")
risk.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/gold/resident_risk_summary")
shift_board.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/gold/shift_board")
family_follow_up.write.mode("overwrite").format("delta").save(f"{OUTPUT_PATH}/gold/family_follow_up")

# COMMAND ----------

display(shift_board)
display(family_follow_up)

