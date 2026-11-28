# Evidence correlation
Run log analyzer and system-tree audit first, then:
python3 tools/evidence_correlator.py port-log-analysis.json system-audit.json --output correlated-evidence.json

This read-only stage links log tokens to ELF SONAME/path, init service inventory, property inventory, and APEX paths. Its review ranking is not root-cause certainty or a compatibility verdict. It does not resolve linker namespaces, symbol versions, runtime permissions, or service dependencies. A library absent from an inventory is not a recommendation to copy it; validate ABI, symbol/version, namespace, partition visibility and donor provenance first.
