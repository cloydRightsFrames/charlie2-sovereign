#!/data/data/com.termux/files/usr/bin/bash
# ZRAM-equivalent: configure kernel memory compression
# On Android, zram is usually pre-configured by the kernel
# We optimize the swappiness and cache pressure instead

# Check current zram
if [ -d /sys/block/zram0 ]; then
  echo "  zram0 detected: $(cat /sys/block/zram0/disksize 2>/dev/null || echo 'size unknown')"
  echo "  ✓ Kernel zram active"
else
  echo "  No zram block device — using swappiness tuning"
fi

# Tune virtual memory for low-RAM mobile device
# swappiness=80: aggressive swap use to keep RAM free
# cache_pressure=150: reclaim cache aggressively
for setting in \
  "vm.swappiness=80" \
  "vm.vfs_cache_pressure=150" \
  "vm.dirty_ratio=10" \
  "vm.dirty_background_ratio=5" \
  "vm.overcommit_memory=1" \
  "vm.min_free_kbytes=8192"; do
  sysctl -w "$setting" 2>/dev/null && echo "  ✓ $setting" || echo "  [!] $setting (needs root)"
done
