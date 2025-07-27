# Base image
FROM ubuntu:20.04

# Disable interactive prompts during package installation
ARG DEBIAN_FRONTEND=noninteractive

# Set environment variables
ENV PATH="/root/OpenEFT/nbis/nfseg/bin:/root/OpenEFT/nbis/nfiq/bin:$PATH"

# Update and install required packages, including cmake, X11 development libraries, and openjpeg
RUN apt-get update && apt-get install -y \
    git \
    sudo \
    build-essential \
    cmake \
    libopenjp2-7-dev \
    libgl1-mesa-glx \
    libx11-dev \
    libxext-dev \
    python3 \
    python3-pip \
    bash

# Clone the OpenEFT repository
RUN git clone https://github.com/robbbbbbbbb/OpenEFT.git /root/OpenEFT && \
    cd /root/OpenEFT && git pull

# Set working directory to the cloned repo
WORKDIR /root/OpenEFT

# Clone and set up NBIS in the repo directory
RUN mkdir /root/build && \
    echo "Setting Up NBIS" && \
    git clone https://github.com/Robbbbbbbbb/nbis /root/OpenEFT/nbis && \
    cd /root/OpenEFT/nbis && \
    ./setup.sh /root/build --64 && \
    echo "Configuring NBIS" && \
    make config && \
    echo "Making NBIS" && \
    make it && \
    echo "Installing NBIS" && \
    make install LIBNBIS=no

# Add NBIS binaries to PATH
RUN echo 'export PATH="/root/OpenEFT/nbis/nfseg/bin:$PATH"' >> ~/.bashrc && \
    echo 'export PATH="/root/OpenEFT/nbis/nfiq/bin:$PATH"' >> ~/.bashrc && \
	echo 'export PATH="/root/OpenEFT/nbis/an2k/bin:$PATH"' >> ~/.bashrc

# Install Python dependencies from the requirements.txt in the OpenEFT repo
RUN pip3 install -r requirements.txt

# Run Django migrations
RUN python3 manage.py migrate

# Compile an2ktool during build
WORKDIR /root/OpenEFT/nbis/an2k
RUN make config && make it

# Set working directory back to OpenEFT since an2ktool is compiled in order
WORKDIR /root/OpenEFT

# Run the build_linux.sh script
RUN chmod +x build_docker.sh && ./build_docker.sh

# Expose Django port
EXPOSE 8080

# Start OpenEFT, fallback to tail if it crashes
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]