#!/data/data/com.termux/files/usr/bin/bash
# Free Python/pip cache
pip cache purge 2>/dev/null && echo "  ✓ pip cache cleared"
# Free npm cache
npm cache clean --force 2>/dev/null && echo "  ✓ npm cache cleared"
# Free cargo cache registry (keep builds)
rm -rf "$HOME/.cargo/registry/cache" 2>/dev/null && echo "  ✓ cargo cache cleared"
# Free Go cache
go clean -cache 2>/dev/null && echo "  ✓ go cache cleared"
# Clear Python bytecode
find "$HOME/charlie2" -name "*.pyc" -delete 2>/dev/null
find "$HOME/charlie2" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
echo "  ✓ Python bytecode cleared"
# Drop page cache (needs root — attempt anyway)
sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null \
  && echo "  ✓ Page cache dropped" \
  || echo "  [!] Page cache drop needs root"
