# Use a lightweight base image
FROM ubuntu:20.04

# Set environment variables to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    build-essential \
    bzip2 \
    ca-certificates \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Detect architecture and install the correct Miniconda version
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh; \
    else \
        wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O /tmp/miniconda.sh; \
    fi && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda && \
    rm /tmp/miniconda.sh

# Add Miniconda to PATH
ENV PATH="/opt/miniconda/bin:$PATH"

# Update conda and create a new environment
RUN conda update -n base -c defaults conda && \
    conda create -y -n neuro python=3.9

# Activate environment and install Python packages
RUN /opt/miniconda/bin/conda run -n neuro conda install -y -c conda-forge \
        pandas=1.4 \
        matplotlib=3.5 \
        scikit-learn=1.0 \
        seaborn=0.11 \
        ipython=7.31 \
        tensorflow=2.9 \
        tensorflow-probability=0.17 \
        nilearn=0.9 \
        pyyaml=6.0 \
        tqdm=4.62 \
        numpy=1.23.5 \
        && conda clean --all -y

# Install additional Python packages via pip
RUN /opt/miniconda/bin/conda run -n neuro pip install git+https://github.com/Gilles86/braincoder.git@edf1c5d3ab921121ee7642adc95fb40898d00620

# Copy necessary files
COPY entrypoint.sh /entrypoint.sh
COPY run.py /run.py
COPY version /version

# Ensure entrypoint script is executable
RUN chmod +x /entrypoint.sh

# Set the working directory
WORKDIR /workspace

# Set the entrypoint to the script
ENTRYPOINT ["/entrypoint.sh"]

# Default command to keep the container running
CMD ["bash"]