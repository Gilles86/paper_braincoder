# Use official TensorFlow GPU image (preconfigured with CUDA/cuDNN)
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TF_FORCE_GPU_ALLOW_GROWTH=true \
    PATH="/opt/miniconda/bin:$PATH" \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH" \
    CUDA_HOME="/usr/local/cuda" \
    PYTHONPATH="/opt/miniconda/envs/neuro/lib/python3.10/site-packages:$PYTHONPATH" \
    TF_CPP_MIN_LOG_LEVEL=2

# Install essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget git build-essential \
    bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 \
    pciutils curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Miniconda & Mamba
RUN wget -qO /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda && \
    rm -f /tmp/miniconda.sh

# Install Mamba & zstandard
RUN /opt/miniconda/bin/conda install -n base -c conda-forge mamba zstandard

# Create Conda environment
RUN /opt/miniconda/bin/mamba create -y -n neuro -c conda-forge -c nvidia \
    python=3.10 \
    pandas=1.5 \
    matplotlib=3.7 \
    scikit-learn=1.3 \
    seaborn=0.12 \
    ipython=8.12 \
    nilearn=0.10 \
    pyyaml=6.0 \
    tqdm=4.66 \
    numpy=1.26

# Install TensorFlow Probability (since it's missing in the base image)
RUN /opt/miniconda/bin/conda run -n neuro pip install --no-cache-dir tensorflow[and-cuda] tensorflow-probability tf-keras

# Clean up Conda cache to reduce image size
RUN /opt/miniconda/bin/conda clean --all -y

# Install additional Python packages via pip
RUN /opt/miniconda/bin/conda run -n neuro pip install --no-cache-dir \
    git+https://github.com/Gilles86/braincoder.git@edf1c5d3ab921121ee7642adc95fb40898d00620

# Copy necessary scripts and set permissions
COPY entrypoint.sh /entrypoint.sh
COPY run.py /run.py
COPY version /version
RUN chmod +x /entrypoint.sh

# Set working directory
WORKDIR /workspace

# Define entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["bash"]