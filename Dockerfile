# Multi-stage build: the render stage needs pandas/statsmodels to turn
# already-scored data into static HTML, but NOTHING in the final image
# needs torch/transformers/FinBERT -- that model only ever runs offline,
# during data collection (see src/run_pipeline.py), never in this container.
# The result is a static-file server serving ~1MB of HTML+PNG, not a
# ~2GB PyTorch image.

FROM python:3.12-slim AS render
WORKDIR /build

COPY site/requirements.txt site/requirements.txt
RUN pip install --no-cache-dir -r site/requirements.txt

COPY src/ src/
COPY site/templates/ site/templates/
COPY data/processed/call_features.parquet data/processed/call_features.parquet

RUN python3 -m src.site.render

FROM nginx:1.27-alpine-slim
COPY --from=render /build/site/dist/index.html /usr/share/nginx/html/index.html
COPY docs/figures/*_segment_heatmap.png /usr/share/nginx/html/figures/

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q --spider http://localhost/ || exit 1
