# Isolated test PBX of the local stand (stage 07.1, D-172): the Ubuntu 26.04 Asterisk package of the production
# server (checked read-only 2026-10-13: 1:22.5.2~dfsg+~cs6.15.60671435-1). One image for the three containers: the
# PBX under test, the simulated desk phones and the simulated providers. socat bridges the PBX's loopback AMI to a
# Unix socket for the host (the AMI users permit 127.0.0.1 only, exactly as in production).
FROM ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
ARG ASTERISK_VERSION=1:22.5.2~dfsg+~cs6.15.60671435-1
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        "asterisk=${ASTERISK_VERSION}" "asterisk-modules=${ASTERISK_VERSION}" socat \
    && rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /usr/local/bin/itvolga-entrypoint
RUN chmod 755 /usr/local/bin/itvolga-entrypoint
ENTRYPOINT ["/usr/local/bin/itvolga-entrypoint"]
