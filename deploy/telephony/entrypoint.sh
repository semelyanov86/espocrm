#!/bin/sh
# Entry point of the test PBX containers (stage 07.1). Role pbx: renders the AMI users from the production example
# with the stand secrets (environment of the container, from the private stand directory), bridges the loopback AMI
# to the host socket, then runs Asterisk as the asterisk user like the production package does.
set -eu
umask 077

if [ "${ITVOLGA_ROLE:-}" = pbx ]; then
    : "${AMI_LISTENER_SECRET:?}" "${AMI_DIALER_SECRET:?}" "${ESPO_GID:?}"
    mkdir -p /etc/asterisk/manager.d
    # The sed script comes on stdin from the printf builtin: the secrets never appear in a process's arguments.
    printf 's/example_listener_secret/%s/\ns/example_dialer_secret/%s/\n' "$AMI_LISTENER_SECRET" "$AMI_DIALER_SECRET" \
        | sed -f - /opt/itvolga/manager.d-itvolga-espo.conf.example > /etc/asterisk/manager.d/itvolga-espo.conf
    chown root:asterisk /etc/asterisk/manager.d/itvolga-espo.conf
    chmod 640 /etc/asterisk/manager.d/itvolga-espo.conf
    socat "UNIX-LISTEN:/run/ami/ami.sock,fork,unlink-early,mode=660,user=root,group=${ESPO_GID}" TCP:127.0.0.1:5038 &
fi

exec asterisk -f -U asterisk -G asterisk
