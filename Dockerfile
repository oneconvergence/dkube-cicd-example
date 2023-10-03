FROM ubuntu:18.04

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get -y install git python-pip curl

RUN apt-get install -y python3.7 python3-distutils libpython3.7


#conda
ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN apt-get update

RUN apt-get install -y wget && rm -rf /var/lib/apt/lists/*

RUN wget \
     https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
     && mkdir /root/.conda \
     && bash Miniconda3-latest-Linux-x86_64.sh -b \
     && rm -f Miniconda3-latest-Linux-x86_64.sh

ADD conda_env.yaml .
RUN conda env create -f conda_env.yaml && \
     conda clean -afy && conda init bash && \
     echo "conda activate dkube-env" >> ~/.bashrc

RUN cp /root/miniconda3/envs/dkube-env/bin/dcc /usr/local/bin/dcc
RUN cp /root/miniconda3/envs/dkube-env/bin/dsl-compile /usr/local/bin/dsl-compile
RUN ln -s /usr/lib/x86_64-linux-musl/libc.so /lib/libc.musl-x86_64.so.1

#kubectl
RUN curl -LO https://dl.k8s.io/release/v1.20.0/bin/linux/amd64/kubectl
RUN mv kubectl /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl


RUN touch /built_using_dockerfile
ENV PATH=/opt/conda/envs/dkube-env/bin:$PATH

ENV TINI_VERSION v0.16.1
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /usr/bin/tini
RUN chmod +x /usr/bin/tini

ENTRYPOINT [ "/usr/bin/tini", "--" ]
