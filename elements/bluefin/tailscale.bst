kind: manual

sources:
- kind: tar
  (?):
  - arch == "x86_64":
      url: tailscale_pkgs:tailscale_1.102.5_amd64.tgz
      ref: 65e6d7f19ad7e1c87d20c2a21e92f38a96795cb897af54b04536590e1c148d12
  - arch == "aarch64":
      url: tailscale_pkgs:tailscale_1.102.5_arm64.tgz
      ref: 60d60109e33d097318c66adc1f1b4e78e528fa1c0357e8bfe82af99f21a18b89

build-depends:
- core/sandbox-tools.bst
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- freedesktop-sdk.bst:components/sed.bst

variables:
  strip-binaries: ""

config:
  install-commands:
  - |
    install -Dm755 -t "%{install-root}%{bindir}" tailscale tailscaled
  - |
    sed -e 's|/usr/sbin/tailscaled|/usr/bin/tailscaled|g' \
        -e '/^EnvironmentFile=/d' \
        systemd/tailscaled.service > tailscaled.service.patched
    sed -i '/^\[Service\]/a Environment=FLAGS=' tailscaled.service.patched
    sed -i '/^\[Service\]/a Environment=PORT=41641' tailscaled.service.patched
    install -Dm644 -t "%{install-root}%{indep-libdir}/systemd/system" tailscaled.service.patched
    mv "%{install-root}%{indep-libdir}/systemd/system/tailscaled.service.patched" \
       "%{install-root}%{indep-libdir}/systemd/system/tailscaled.service"
  - |
    install -Dm644 /dev/null "%{install-root}%{indep-libdir}/systemd/system-preset/80-tailscale.preset"
    cat > "%{install-root}%{indep-libdir}/systemd/system-preset/80-tailscale.preset" <<'PRESET'
    enable tailscaled.service
    PRESET
  - |
    %{install-extra}
