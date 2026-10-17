kind: manual

sources:
- kind: tar
  (?):
  - arch == "x86_64":
      url: github_files:ublue-os/uupd/releases/download/v1.5.0/uupd_Linux_x86_64.tar.gz
      ref: 1a24d3a87941a24a82a764b339163392516ee83b18c1c8cecf4efcde1dc9f38f
  - arch == "aarch64":
      url: github_files:ublue-os/uupd/releases/download/v1.5.0/uupd_Linux_arm64.tar.gz
      ref: bfdb71a2153c903da9c530f3aaf5d6cf398111266f79f608d02768cf895e3342
  base-dir: ""

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    install -Dm755 -t "%{install-root}%{bindir}" uupd
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/systemd/system/uupd.service"
    cat > "%{install-root}%{indep-libdir}/systemd/system/uupd.service" <<'SERVICE'
    [Unit]
    Description=Universal Blue Update Oneshot Service
    StartLimitBurst=3
    StartLimitIntervalSec=600

    [Service]
    Type=oneshot
    # DO NOT CHANGE ANYTHING BELOW UNLESS YOU KNOW WHAT YOU ARE DOING
    # --disable-module-distrobox matches production Bluefin (build_files/base/17-cleanup.sh)
    ExecStart=/usr/bin/uupd --disable-module-distrobox --log-level=debug --json
    # Restart on failure for edge cases like waking from suspend and wifi not connecting immediately
    Restart=on-failure
    RestartSec=60s
    # Set SELinux context unconfined because bootc requires some special perms for relabeling (install_t????)
    SELinuxContext=system_u:unconfined_r:unconfined_t:s0
    SERVICE
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/systemd/system/uupd.timer"
    cat > "%{install-root}%{indep-libdir}/systemd/system/uupd.timer" <<'TIMER'
    [Unit]
    Description=Auto Update System Timer For Universal Blue
    Wants=network-online.target

    [Timer]
    # Run daily at 4:00 AM
    OnCalendar=*-*-* 04:00:00

    # If the system was off/suspended at 4:00 AM, trigger immediately on resume/boot
    Persistent=true

    # Wait up to 15 minutes after triggering and Spreads the load on update servers (thundering herd protection).
    RandomizedDelaySec=15m

    [Install]
    WantedBy=timers.target
    TIMER
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/systemd/system/uupd-manual.service"
    cat > "%{install-root}%{indep-libdir}/systemd/system/uupd-manual.service" <<'MANUAL'
    [Unit]
    Description=Universal Blue Update Oneshot Service - Manual Activation
    StartLimitBurst=3
    StartLimitIntervalSec=600

    [Service]
    Type=oneshot
    # DO NOT CHANGE ANYTHING BELOW UNLESS YOU KNOW WHAT YOU ARE DOING
    ExecStart=/usr/bin/uupd --hw-check=false --json --log-level=debug
    # Restart on failure for edge cases like waking from suspend and wifi not connecting immediately
    Restart=on-failure
    RestartSec=60s
    # Set SELinux context unconfined because bootc requires some special perms for relabeling (install_t????)
    SELinuxContext=system_u:unconfined_r:unconfined_t:s0
    MANUAL
  - |
    install -Dm644 /dev/null "%{install-root}%{sysconfdir}/uupd/config.json"
    cat > "%{install-root}%{sysconfdir}/uupd/config.json" <<'CONFIG'
    {
        "checks": {
            "hardware": {
                "enable": true,
                "bat-min-percent": 20,
                "cpu-max-percent": 50,
                "mem-max-percent": 90,
                "net-max-bytes": 700000
            }
        },
        "modules": {
            "brew": {
                "disable": false
            },
            "distrobox": {
                "disable": false
            },
            "flatpak": {
                "disable": false
            },
            "system": {
                "disable": false
            }
        }
    }
    CONFIG
  - |
    install -Dm644 /dev/null "%{install-root}%{sysconfdir}/polkit-1/rules.d/uupd.rules"
    cat > "%{install-root}%{sysconfdir}/polkit-1/rules.d/uupd.rules" <<'RULES'
    polkit.addRule(function(action, subject) {
        if (action.id == "org.freedesktop.systemd1.manage-units") {
            switch(action.lookup("unit")) {
                case "uupd.service":
                    return polkit.Result.YES;
                case "uupd-manual.service":
                    return polkit.Result.YES;
            }
        }
    })
    RULES
  - |
    %{install-extra}
