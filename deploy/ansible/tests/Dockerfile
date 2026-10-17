# Disposable test target of the role espocrm (stage 09, deploy/ansible/tests): Ubuntu 26.04 — the release of the
# production server — with systemd as PID 1, so the server roles (php, apache, mysql, fail2ban, backup) and the role
# espocrm run unchanged over the Docker connection. Synthetic data only; removed by `task ansible:test-down`.
FROM ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
ENV container=docker DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends systemd systemd-sysv dbus python3 python3-apt sudo \
        ca-certificates curl gnupg cron iproute2 openssl procps tzdata less \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/systemd/system/*.wants/*getty* /lib/systemd/system/multi-user.target.wants/*getty* \
    && systemctl mask systemd-logind.service console-getty.service 'getty@.service'
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
