FROM bitnami/spark:3.5

USER root
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/input /app/output

CMD ["bash", "-lc", "python src/generate_sample_data.py && spark-submit src/pipeline.py --input input --output output && python src/validate_outputs.py --output output"]

