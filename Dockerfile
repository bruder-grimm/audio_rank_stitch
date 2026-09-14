FROM condaforge/miniforge3:latest

WORKDIR /app

# Create the Python 3.12 Conda environment.
COPY environment.yml .
RUN conda env create -f environment.yml && \
    conda clean -afy

# Use the Conda environment by default.
ENV PATH=/opt/conda/envs/audio-rank-stitch/bin:$PATH

# Install project metadata first.
COPY pyproject.toml README.md ./

# Copy application source.
COPY src ./src

# Install the project in editable mode.
RUN pip install --no-cache-dir -e .

# Recording frontend and administrative playback frontend.
EXPOSE 1234 5678

# Start the application.
CMD ["audio-rank-stitch"]
