# System-side compatibility evidence
Run target and donor audits, optionally evidence correlation, then:
python3 tools/compatibility_evidence.py target-audit.json donor-audit.json --correlated correlated-evidence.json --output compatibility-evidence.json

The report flags target ELF dependency inventory gaps, donor SONAME gaps, metadata ABI differences, duplicate SONAMEs, and init service name differences. These are findings to investigate—not a portability score, copy list, or bootability verdict. Runtime namespaces, symbols, VINTF, SELinux and HAL behavior are out of scope.
