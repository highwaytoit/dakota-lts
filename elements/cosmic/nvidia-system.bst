# Experimental COSMIC NVIDIA: reuse Dakota's R580 driver stack, not
# Razorfin's separate NVIDIA packaging or GNOME/Bluefin image identity.
# All dependencies share the existing freedesktop-sdk Linux 6.18 LTS kernel.
kind: stack

depends:
- cosmic/system.bst
- bluefin-nvidia/nvidia-drivers.bst
- bluefin-nvidia/nvidia-vaapi-driver.bst
- bluefin-nvidia/nvidia-kargs.bst
- bluefin-nvidia/nvidia-modprobe-config.bst
- bluefin-nvidia/nvidia-device-nodes.bst
- bluefin-nvidia/nvidia-container-toolkit.bst
- bluefin-nvidia/nvidia-container-toolkit-preset.bst

public:
  bst:
    integration-commands:
    # NVIDIA modules need depmod against the complete COSMIC sysroot.
    # Reject a second kernel rather than choosing the first one silently.
    - |
      KERNEL_DIRS=$(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d -print)
      set -- $KERNEL_DIRS
      if [ "$#" -ne 1 ]; then
          echo "FATAL: expected one Linux 6.18 kernel under /usr/lib/modules, found $#" >&2
          exit 1
      fi
      KVER=${1##*/}
      case "$KVER" in
          6.18.*) ;;
          *)
              echo "FATAL: COSMIC NVIDIA kernel escaped Linux 6.18 LTS: $KVER" >&2
              exit 1
              ;;
      esac
      if ! find "/usr/lib/modules/$KVER" -name 'nvidia.ko*' -print -quit | grep -q .; then
          echo "FATAL: NVIDIA kernel module not found for $KVER" >&2
          exit 1
      fi
      depmod -a "$KVER"
